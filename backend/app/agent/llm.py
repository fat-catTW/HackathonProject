"""Bedrock-backed helpers for service booking."""
from __future__ import annotations

import json
import re
import threading
from datetime import date
from decimal import Decimal
from functools import lru_cache

from ..config import get_settings
from ..services import clock
from ..services.aws import get_aws_client, has_aws_credentials

_DIALECT_GLOSSARY = (
    "The user may speak Taiwanese-Hokkien-influenced Mandarin (台語腔國語), transcribed by a "
    "Mandarin speech recognizer that may render it imperfectly. Recognize these common patterns: "
    "\"三牲\" (three-sacrifice ritual offering), \"透天厝\" (a multi-floor townhouse), "
    "\"逗陣\" (together/along), \"愛\" used to mean \"want/need\" (e.g. \"我愛買\" = \"我要買\"), "
    "\"甲意\" (like/prefer), \"呷飯\" (to eat a meal), \"歹勢\" (sorry/excuse me), "
    "and looser word order than standard Mandarin. Interpret the intended meaning, not the literal "
    "transcription."
)

_YES_NO_SYSTEM = (
    "You classify whether the user confirmed a booking summary. "
    "Return JSON only in the format {\"intent\":\"yes|no|unclear\"}."
)

_SERVICE_SYSTEM = (
    "You are an intent router for a Taiwanese home services assistant. "
    "Choose the best matching service_id from the provided list. "
    "If the user has not clearly chosen a service, return null. "
    "Return JSON only in the format {\"service_id\": string|null}."
    "\n\n" + _DIALECT_GLOSSARY
)

_TURN_SYSTEM = (
    "You are the first-turn router for a Taiwanese home services assistant speaking Traditional Chinese. "
    "Decide whether the latest user message should be handled as one of: "
    "\"chat\", \"service_request\", \"page_help\", \"memory_query\", \"multi_task\", or \"unknown\". "
    "Use \"chat\" for greetings, identity/capability questions, small talk, or short direct conversational replies. "
    "Use \"service_request\" when the user wants to book/apply/arrange exactly one supported service. "
    "Use \"multi_task\" only when the message clearly asks for two or more distinct, independent services in one "
    "sentence (for example: buying an item AND booking a restaurant AND booking a cleaning service). "
    "Use \"page_help\" when the user is asking where something is in the app, what the current page does, or how to navigate. "
    "Use \"memory_query\" when the user is asking about previously used address/phone/service/order details. "
    "If mode is \"chat\", include a natural direct reply in Traditional Chinese. "
    "If mode is \"service_request\" and a service is clear, include the best matching service_id from the provided list; otherwise use null. "
    "If mode is \"multi_task\", leave service_id null — the tasks themselves are resolved separately. "
    "Do not invent unsupported services. "
    "Return JSON only in the format "
    "{\"mode\":\"chat|service_request|page_help|memory_query|multi_task|unknown\",\"reply\":string|null,\"service_id\":string|null}."
    "\n\n" + _DIALECT_GLOSSARY
)

_MULTI_TASK_SYSTEM = (
    "You detect whether a Taiwanese home-services user message contains more than one distinct "
    "service request in a single sentence (e.g. buying an item, booking a restaurant, and booking "
    "a cleaning service all in one message). "
    "Only return tasks when there are genuinely two or more independent service requests; otherwise return an empty list. "
    "For each task, choose the best matching service_id from the provided list. "
    "Also extract any field values you can already tell from the message as hint_fields — use only field ids that "
    "make sense for that service (dates, quantities, addresses, etc.); if unsure, leave hint_fields empty. "
    "Do not invent unsupported services. "
    "Return JSON only in the format "
    "{\"tasks\": [{\"service_id\": string, \"hint_fields\": object}]}."
    "\n\n" + _DIALECT_GLOSSARY
)

_FIELD_SYSTEM = (
    "You fill a JSON booking form for a Taiwanese home services assistant. "
    "Use only the provided field ids from the current form schema. "
    "Read the current form schema and current form draft before deciding updates. "
    "Your job is to interpret the latest user message and write only the form fields the user is providing or correcting. "
    "Memory is background only: never copy a remembered value into a field unless the latest user message explicitly asks to reuse it. "
    "Never write a free-text field (descriptions, notes) from memory - those must come from what the user just said. "
    "For select fields, return one of the exact option values whenever possible. "
    "For dates, prefer YYYY-MM-DD. "
    "If the latest user message is not giving field values, return an empty object. "
    "Do not overwrite an existing value unless the user clearly changes it. "
    "Do not answer questions or explain anything outside the JSON. "
    "Return JSON only in the format {\"fields\": { ... }}."
    "\n\n" + _DIALECT_GLOSSARY
)

_FORM_TURN_SYSTEM = (
    "You are the active-form orchestrator for a Taiwanese home services assistant speaking Traditional Chinese. "
    "The assistant is already collecting a booking form for one known service. "
    "Decide whether the latest user message should: "
    "\"reply\" (just answer conversationally), "
    "\"update_fields\" (update form fields), "
    "\"reply_and_update\" (do both), "
    "or \"unknown\". "
    "Use only provided field ids. For select fields, prefer exact option values. "
    "If the user is chatting, frustrated, asking what you can do, or saying something that should receive a direct answer without changing the form, use \"reply\". "
    "If the user provides or corrects form values, use \"update_fields\" or \"reply_and_update\". "
    "Do not invent unsupported fields or services. "
    "Return JSON only in the format "
    "{\"mode\":\"reply|update_fields|reply_and_update|unknown\",\"reply\":string|null,\"fields\":{...}}."
)

_REPLY_SYSTEM = (
    "You are a warm Taiwanese home services assistant speaking Traditional Chinese. "
    "Write natural chat replies, not robotic templates. "
    "Keep replies concise, helpful, and grounded only in the provided facts. "
    "If asking for information, ask for only one next thing at a time. "
    "Do not invent booking details, prices, or promises. "
    "Return JSON only in the format {\"reply\": string}."
)

_PAGE_HELP_SYSTEM = (
    "You are a warm Taiwanese app navigation assistant speaking Traditional Chinese. "
    "Answer only with facts provided in the tool payload. "
    "Choose the single best target page from the tool payload before writing the reply. "
    "If the user asks where to apply, book, fill, or manually submit a service request, prefer a service-specific form page over a generic home page whenever the payload supports it. "
    "If the current page is already the best page, say the user can continue there. "
    "If the target page is different, explain the shortest useful path in 1-3 steps. "
    "Mention the chosen page title explicitly. "
    "Do not invent UI elements, routes, or actions that are not in the payload. "
    "Do not mention internal relevance scores or backend logic. "
    "Return JSON only in the format {\"target_page_id\": string|null, \"reply\": string}."
)

_EXTERNAL_QUERY_SYSTEM = (
    "You turn a Taiwanese user's request into a short, effective search-engine query in Traditional "
    "Chinese, for finding real-world products or restaurants on the web. "
    "Keep it to a few keywords, no explanations. "
    "Return JSON only in the format {\"query\": string}."
)

_EXTERNAL_RANK_SYSTEM = (
    "You pick and rank the best matches for a user's request from a provided candidate list. "
    "You may ONLY choose ids that appear in the candidate list — never invent an id or describe an "
    "item that is not in the list. "
    "Pick at most the requested max_results items, best match first, and give each a short "
    "one-sentence reason in Traditional Chinese. "
    "Return JSON only in the format {\"picks\": [{\"id\": string, \"reason\": string}]}."
)

_DEBUG_STATE = threading.local()


def _set_debug_info(**kwargs) -> None:
    _DEBUG_STATE.info = kwargs


def consume_debug_info() -> dict:
    info = getattr(_DEBUG_STATE, "info", {}) or {}
    _DEBUG_STATE.info = {}
    return info


def _json_safe(value):
    """Recursively convert Decimal values (as returned by DynamoDB reads, see
    store.py's convert_floats_to_decimal for the write-side counterpart) into
    plain int/float so prompt payloads built from session state can always be
    JSON-serialized, regardless of whether state came from the mock store or
    real DynamoDB."""
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


def _dumps(value) -> str:
    return json.dumps(_json_safe(value), ensure_ascii=False, indent=2)


def _strip_fences(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def _extract_text(response: dict) -> str:
    blocks = (((response.get("output") or {}).get("message") or {}).get("content") or [])
    return "\n".join(block.get("text", "") for block in blocks if isinstance(block, dict))


def _parse_json_text(text: str) -> dict | None:
    payload = _strip_fences(text)
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        start = payload.find("{")
        end = payload.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(payload[start : end + 1])
            except json.JSONDecodeError:
                return None
    return None


@lru_cache
def _get_client():
    if not has_aws_credentials():
        return None
    try:
        return get_aws_client("bedrock-runtime")
    except Exception:
        return None


def is_available() -> bool:
    return _get_client() is not None


def _converse_json(system: str, prompt: str, *, max_tokens: int = 512) -> dict | None:
    client = _get_client()
    if client is None:
        _set_debug_info(stage="client", status="unavailable")
        return None

    settings = get_settings()
    try:
        response = client.converse(
            modelId=settings.bedrock_model_id,
            system=[{"text": system}],
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={"maxTokens": max_tokens, "temperature": 0},
        )
        text = _extract_text(response)
        payload = _parse_json_text(text)
        if payload is None:
            _set_debug_info(stage="parse", status="invalid_json", raw_text=text[:800])
            return None
        _set_debug_info(stage="converse", status="ok")
        return payload
    except Exception as exc:
        _set_debug_info(stage="converse", status="exception", error_type=type(exc).__name__, error_message=str(exc))
        return None


def interpret_yes_no(question: str, reply: str) -> str | None:
    payload = _converse_json(
        _YES_NO_SYSTEM,
        f"Question:\n{question}\n\nReply:\n{reply}",
        max_tokens=128,
    )
    if not payload:
        return None
    intent = payload.get("intent")
    return intent if intent in {"yes", "no", "unclear"} else None


def choose_service(
    message: str,
    services: list[dict],
    *,
    short_term_memory: str = "",
    long_term_memory: str = "",
) -> str | None:
    prompt = (
        f"Today is {clock.today().isoformat()} ({clock.weekday_zh()}).\n"
        f"Short-term memory:\n{short_term_memory or 'None'}\n\n"
        f"Long-term memory:\n{long_term_memory or 'None'}\n\n"
        f"Available services:\n{_dumps(services)}\n\n"
        f"User message:\n{message}"
    )
    payload = _converse_json(_SERVICE_SYSTEM, prompt, max_tokens=192)
    if not payload:
        return None
    service_id = payload.get("service_id")
    valid_ids = {service["id"] for service in services}
    return service_id if service_id in valid_ids else None


def plan_turn(
    *,
    message: str,
    services: list[dict],
    current_page_id: str = "",
    short_term_memory: str = "",
    long_term_memory: str = "",
) -> dict | None:
    prompt = (
        f"Today is {date.today().isoformat()}.\n"
        f"Current page id: {current_page_id or 'None'}\n\n"
        f"Short-term memory:\n{short_term_memory or 'None'}\n\n"
        f"Long-term memory:\n{long_term_memory or 'None'}\n\n"
        f"Available services:\n{_dumps(services)}\n\n"
        f"Latest user message:\n{message}"
    )
    payload = _converse_json(_TURN_SYSTEM, prompt, max_tokens=320)
    if not payload:
        return None
    mode = payload.get("mode")
    if mode not in {"chat", "service_request", "page_help", "memory_query", "multi_task", "unknown"}:
        return None
    service_id = payload.get("service_id")
    valid_ids = {service["id"] for service in services}
    normalized_service_id = service_id if service_id in valid_ids else None
    reply = payload.get("reply")
    normalized_reply = reply.strip() if isinstance(reply, str) and reply.strip() else None
    return {
        "mode": mode,
        "reply": normalized_reply,
        "service_id": normalized_service_id,
    }


def plan_multi_task(
    *,
    message: str,
    services: list[dict],
    short_term_memory: str = "",
    long_term_memory: str = "",
) -> list[dict]:
    prompt = (
        f"Today is {date.today().isoformat()}.\n"
        f"Short-term memory:\n{short_term_memory or 'None'}\n\n"
        f"Long-term memory:\n{long_term_memory or 'None'}\n\n"
        f"Available services:\n{_dumps(services)}\n\n"
        f"User message:\n{message}"
    )
    payload = _converse_json(_MULTI_TASK_SYSTEM, prompt, max_tokens=512)
    if not payload or not isinstance(payload.get("tasks"), list):
        return []

    valid_ids = {service["id"] for service in services}
    tasks: list[dict] = []
    for task in payload["tasks"]:
        if not isinstance(task, dict):
            continue
        service_id = task.get("service_id")
        if service_id not in valid_ids:
            continue
        hint_fields = task.get("hint_fields")
        tasks.append({
            "service_id": service_id,
            "hint_fields": hint_fields if isinstance(hint_fields, dict) else {},
        })
    return tasks


def extract_fields(
    *,
    message: str,
    service_name: str,
    fields: list[dict],
    collected_fields: dict,
    form_schema: dict | None = None,
    form_draft: dict | None = None,
    short_term_memory: str = "",
    long_term_memory: str = "",
) -> dict:
    prompt = (
        f"Today is {clock.today().isoformat()} ({clock.weekday_zh()}).\n"
        f"Service name: {service_name}\n"
        f"Form schema:\n{_dumps(form_schema or {'fields': fields})}\n\n"
        f"Current form draft:\n{_dumps(form_draft or {'fields': collected_fields})}\n\n"
        f"Already collected:\n{_dumps(collected_fields)}\n\n"
        f"Short-term memory:\n{short_term_memory or 'None'}\n\n"
        f"Long-term memory:\n{long_term_memory or 'None'}\n\n"
        f"Latest user message:\n{message}"
    )
    payload = _converse_json(_FIELD_SYSTEM, prompt, max_tokens=512)
    if not payload or not isinstance(payload.get("fields"), dict):
        return {}
    return payload["fields"]


def plan_form_turn(
    *,
    message: str,
    service_name: str,
    fields: list[dict],
    collected_fields: dict,
    form_schema: dict | None = None,
    form_draft: dict | None = None,
    active_field: str = "",
    short_term_memory: str = "",
    long_term_memory: str = "",
) -> dict | None:
    prompt = (
        f"Today is {date.today().isoformat()}.\n"
        f"Service name: {service_name}\n"
        f"Active field: {active_field or 'None'}\n"
        f"Form schema:\n{_dumps(form_schema or {'fields': fields})}\n\n"
        f"Current form draft:\n{_dumps(form_draft or {'fields': collected_fields})}\n\n"
        f"Already collected:\n{_dumps(collected_fields)}\n\n"
        f"Short-term memory:\n{short_term_memory or 'None'}\n\n"
        f"Long-term memory:\n{long_term_memory or 'None'}\n\n"
        f"Latest user message:\n{message}"
    )
    payload = _converse_json(_FORM_TURN_SYSTEM, prompt, max_tokens=512)
    if not payload:
        return None
    mode = payload.get("mode")
    if mode not in {"reply", "update_fields", "reply_and_update", "unknown"}:
        return None
    reply = payload.get("reply")
    normalized_reply = reply.strip() if isinstance(reply, str) and reply.strip() else None
    raw_fields = payload.get("fields")
    normalized_fields = raw_fields if isinstance(raw_fields, dict) else {}
    return {
        "mode": mode,
        "reply": normalized_reply,
        "fields": normalized_fields,
    }


def compose_reply(
    *,
    phase: str,
    latest_user_message: str = "",
    service_name: str = "",
    collected_fields: dict | None = None,
    missing_field_label: str = "",
    missing_field_question: str = "",
    summary: str = "",
    preferred_value: str = "",
    request_id: str = "",
    request_status: str = "",
    error_message: str = "",
    service_options: list[str] | None = None,
    short_term_memory: str = "",
    long_term_memory: str = "",
) -> str | None:
    prompt_payload = {
        "today": f"{clock.today().isoformat()} ({clock.weekday_zh()})",
        "phase": phase,
        "latest_user_message": latest_user_message,
        "service_name": service_name,
        "collected_fields": collected_fields or {},
        "missing_field_label": missing_field_label,
        "missing_field_question": missing_field_question,
        "summary": summary,
        "preferred_value": preferred_value,
        "request_id": request_id,
        "request_status": request_status,
        "error_message": error_message,
        "service_options": service_options or [],
        "short_term_memory": short_term_memory or "None",
        "long_term_memory": long_term_memory or "None",
    }
    payload = _converse_json(
        _REPLY_SYSTEM,
        _dumps(prompt_payload),
        max_tokens=320,
    )
    if not payload:
        return None
    reply = payload.get("reply")
    return reply.strip() if isinstance(reply, str) and reply.strip() else None


def compose_page_help_reply(
    *,
    latest_user_message: str,
    current_page_id: str = "",
    tool_payload: dict | None = None,
) -> str | None:
    prompt_payload = {
        "today": f"{clock.today().isoformat()} ({clock.weekday_zh()})",
        "latest_user_message": latest_user_message,
        "current_page_id": current_page_id or "",
        "tool_payload": tool_payload or {},
    }
    payload = _converse_json(
        _PAGE_HELP_SYSTEM,
        _dumps(prompt_payload),
        max_tokens=320,
    )
    if not payload:
        return None
    reply = payload.get("reply")
    return reply.strip() if isinstance(reply, str) and reply.strip() else None


def plan_external_query(user_text: str, *, purpose: str) -> str | None:
    payload = _converse_json(
        _EXTERNAL_QUERY_SYSTEM,
        f"Purpose: {purpose}\nUser request:\n{user_text}",
        max_tokens=128,
    )
    if not payload:
        return None
    query = payload.get("query")
    return query.strip() if isinstance(query, str) and query.strip() else None


def rank_external_results(
    user_text: str, candidates: list[dict], *, id_key: str, max_results: int
) -> list[dict] | None:
    prompt = (
        f"User request:\n{user_text}\n\n"
        f"max_results: {max_results}\n\n"
        f"Candidates (id field is \"{id_key}\"):\n"
        + _dumps(candidates)
    )
    payload = _converse_json(_EXTERNAL_RANK_SYSTEM, prompt, max_tokens=768)
    if not payload or not isinstance(payload.get("picks"), list):
        return None

    by_id = {c[id_key]: c for c in candidates}
    picks: list[dict] = []
    for pick in payload["picks"]:
        if not isinstance(pick, dict):
            continue
        pick_id = pick.get("id")
        if pick_id not in by_id:
            continue
        reason = pick.get("reason")
        picks.append({
            **by_id[pick_id],
            "reason": reason.strip() if isinstance(reason, str) and reason.strip() else "",
        })
        if len(picks) >= max_results:
            break
    return picks or None
