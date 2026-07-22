"""Bedrock-backed helpers for service booking."""
from __future__ import annotations

import json
import re
from datetime import date
from functools import lru_cache

from ..config import get_settings
from ..services.aws import get_aws_client, has_aws_credentials

_YES_NO_SYSTEM = (
    "You classify whether the user confirmed a booking summary. "
    "Return JSON only in the format {\"intent\":\"yes|no|unclear\"}."
)

_SERVICE_SYSTEM = (
    "You are an intent router for a Taiwanese home services assistant. "
    "Choose the best matching service_id from the provided list. "
    "If the user has not clearly chosen a service, return null. "
    "Return JSON only in the format {\"service_id\": string|null}."
)

_FIELD_SYSTEM = (
    "You update a JSON booking form for a Taiwanese home services assistant. "
    "Use only the provided field ids. "
    "Read the current form schema and current form draft before deciding updates. "
    "For select fields, return one of the exact option values when possible. "
    "For dates, prefer YYYY-MM-DD. "
    "If a value is not clearly present in the latest user message, omit it. "
    "Do not overwrite an existing value unless the user clearly changes it. "
    "Return JSON only in the format {\"fields\": { ... }}."
)

_REPLY_SYSTEM = (
    "You are a warm Taiwanese home services assistant speaking Traditional Chinese. "
    "Write natural chat replies, not robotic templates. "
    "Keep replies concise, helpful, and grounded only in the provided facts. "
    "If asking for information, ask for only one next thing at a time. "
    "Do not invent booking details, prices, or promises. "
    "Return JSON only in the format {\"reply\": string}."
)


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
        return None

    settings = get_settings()
    try:
        response = client.converse(
            modelId=settings.bedrock_model_id,
            system=[{"text": system}],
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={"maxTokens": max_tokens, "temperature": 0},
        )
        return _parse_json_text(_extract_text(response))
    except Exception:
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
        f"Today is {date.today().isoformat()}.\n"
        f"Short-term memory:\n{short_term_memory or 'None'}\n\n"
        f"Long-term memory:\n{long_term_memory or 'None'}\n\n"
        f"Available services:\n{json.dumps(services, ensure_ascii=False, indent=2)}\n\n"
        f"User message:\n{message}"
    )
    payload = _converse_json(_SERVICE_SYSTEM, prompt, max_tokens=192)
    if not payload:
        return None
    service_id = payload.get("service_id")
    valid_ids = {service["id"] for service in services}
    return service_id if service_id in valid_ids else None


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
        f"Today is {date.today().isoformat()}.\n"
        f"Service name: {service_name}\n"
        f"Form schema:\n{json.dumps(form_schema or {'fields': fields}, ensure_ascii=False, indent=2)}\n\n"
        f"Current form draft:\n{json.dumps(form_draft or {'fields': collected_fields}, ensure_ascii=False, indent=2)}\n\n"
        f"Already collected:\n{json.dumps(collected_fields, ensure_ascii=False, indent=2)}\n\n"
        f"Short-term memory:\n{short_term_memory or 'None'}\n\n"
        f"Long-term memory:\n{long_term_memory or 'None'}\n\n"
        f"Latest user message:\n{message}"
    )
    payload = _converse_json(_FIELD_SYSTEM, prompt, max_tokens=512)
    if not payload or not isinstance(payload.get("fields"), dict):
        return {}
    return payload["fields"]


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
        "today": date.today().isoformat(),
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
        json.dumps(prompt_payload, ensure_ascii=False, indent=2),
        max_tokens=320,
    )
    if not payload:
        return None
    reply = payload.get("reply")
    return reply.strip() if isinstance(reply, str) and reply.strip() else None
