"""Service booking agent with Bedrock-assisted extraction and reply generation."""
from __future__ import annotations

import re
from datetime import date

from ..services import catalog
from ..services.conversation_memory import MEMORY
from . import llm, nlu, tools

CONFIRM_WORDS = ("確認", "確定", "好", "可以", "沒問題", "ok", "OK", "yes", "Yes")
DENY_WORDS = ("不是", "不用", "先不要", "修改", "不對", "no", "No")

SERVICE_DISPLAY_NAMES = {
    "plumbing_repair": "水電修繕",
    "washing_machine_cleaning": "洗衣機清洗",
    "air_conditioner_cleaning": "冷氣清洗",
    "home_cleaning": "居家清潔",
}

FIELD_DISPLAY_NAMES = {
    "issue_description": "問題描述",
    "preferred_date": "希望日期",
    "preferred_time_slot": "希望時段",
    "address": "服務地址",
    "phone": "聯絡電話",
    "quantity": "數量",
    "hours": "服務時數",
    "machine_type": "洗衣機類型",
}

SELECT_ALIASES = {
    "MORNING": ("MORNING", "早上", "上午"),
    "AFTERNOON": ("AFTERNOON", "下午"),
    "EVENING": ("EVENING", "晚上", "傍晚"),
    "TOP_LOAD": ("TOP_LOAD", "直立式", "上掀式"),
    "FRONT_LOAD": ("FRONT_LOAD", "滾筒式", "前開式"),
}

SELECT_DISPLAY_NAMES = {
    "MORNING": "上午",
    "AFTERNOON": "下午",
    "EVENING": "晚上",
    "TOP_LOAD": "直立式",
    "FRONT_LOAD": "滾筒式",
}

SERVICE_ISSUE_HINT_RE = re.compile(r"馬桶|水管|漏水|堵塞|不通|電燈|插座|冷氣|洗衣機|清潔")
NUMERIC_HINT_RE = re.compile(r"\d|[一二兩三四五六七八九十]")
RULE_SERVICE_KEYWORDS = (
    ("plumbing_repair", ("水電", "修繕", "馬桶", "漏水", "水管", "堵塞", "不通", "燈具", "插座")),
    ("washing_machine_cleaning", ("洗衣機", "洗衣機清洗", "洗衣機清潔")),
    ("air_conditioner_cleaning", ("冷氣", "冷氣清洗", "冷氣清潔", "冷氣保養")),
    ("home_cleaning", ("居家清潔", "打掃", "清潔", "家事服務")),
)


def _is_yes(text: str) -> bool:
    normalized = text.strip()
    return any(normalized == word or normalized.startswith(word) for word in CONFIRM_WORDS) and not _is_no(normalized)


def _is_no(text: str) -> bool:
    normalized = text.strip()
    return any(normalized == word or normalized.startswith(word) for word in DENY_WORDS)


def _judge_reply(question: str, text: str) -> str:
    verdict = llm.interpret_yes_no(question, text)
    if verdict is not None:
        return verdict
    if _is_yes(text):
        return "yes"
    if _is_no(text):
        return "no"
    return "unclear"


def _display_service_name(service_id: str | None, fallback: str | None = None) -> str:
    if service_id and service_id in SERVICE_DISPLAY_NAMES:
        return SERVICE_DISPLAY_NAMES[service_id]
    return fallback or "服務"


def _display_field_label(field_id: str, fields: list[dict]) -> str:
    field = next((item for item in fields if item["id"] == field_id), None)
    return FIELD_DISPLAY_NAMES.get(field_id) or (field or {}).get("label") or field_id


def _display_value(field_id: str, value, fields: list[dict]) -> str:
    if isinstance(value, str):
        value = SELECT_DISPLAY_NAMES.get(value, catalog.SELECT_LABELS.get(value, value))
    label = _display_field_label(field_id, fields)
    unit = " 台" if field_id == "quantity" else " 小時" if field_id == "hours" else ""
    return f"{label}：{value}{unit}"


def _build_summary_text(state: dict) -> str:
    fields = state["service_schema"]["fields"]
    lines = ["請確認以下申請內容：", f"服務：{_display_service_name(state['service_id'], state['service_name'])}"]
    for field in fields:
        if field["id"] in state["collected_fields"]:
            lines.append(_display_value(field["id"], state["collected_fields"][field["id"]], fields))
    lines.append("")
    lines.append("內容正確請回覆「確認」，若要修改也可以直接告訴我要更改哪一項。")
    return "\n".join(lines)


def _build_field_question(field: dict) -> str:
    label = FIELD_DISPLAY_NAMES.get(field["id"]) or field.get("label") or field["id"]
    if field["id"] == "issue_description":
        return "想先幫你整理需求，請描述一下目前遇到的狀況。"
    if field["id"] == "preferred_date":
        return "你希望安排哪一天呢？"
    if field["id"] == "preferred_time_slot":
        return "你比較方便的時段是上午、下午，還是晚上呢？"
    if field["id"] == "address":
        return "請提供服務地址，我好幫你送出預約。"
    if field["id"] == "phone":
        return "請留一支方便聯絡的電話。"
    if field["id"] == "quantity":
        return "這次需要處理幾台呢？"
    if field["id"] == "hours":
        return "你預計需要幾小時的服務呢？"
    if field["id"] == "machine_type":
        return "洗衣機是直立式還是滾筒式呢？"
    return field.get("question") or f"請提供{label}。"


def _recompute_missing(state: dict) -> None:
    fields = state["service_schema"]["fields"]
    state["missing_fields"] = [
        field["id"]
        for field in fields
        if field.get("required") and field["id"] not in state["collected_fields"]
    ]


def _compress_recent_events(events: list[dict] | None, latest_user_message: str | None = None) -> list[dict]:
    recent = list(events or [])[-6:]
    compact = [
        {"role": event.get("role", ""), "content": str(event.get("content", ""))[:200]}
        for event in recent
    ]
    if latest_user_message:
        compact.append({"role": "USER", "content": latest_user_message[:200]})
    return compact[-6:]


def _short_term_context(state: dict, events: list[dict] | None, latest_user_message: str | None = None) -> str:
    recent = _compress_recent_events(events, latest_user_message)
    state["short_term_memory"] = recent
    if not recent:
        return "None"
    return "\n".join(f"{item['role']}: {item['content']}" for item in recent)


def _short_term_context_from_state(state: dict) -> str:
    recent = state.get("short_term_memory") or []
    if not recent:
        return "None"
    return "\n".join(f"{item['role']}: {item['content']}" for item in recent)


def _long_term_memory_context(actor_id: str, query: str) -> str:
    return MEMORY.get_long_term_context(actor_id, query)


def _looks_like_memory_question(text: str) -> bool:
    hints = (
        "記得",
        "記憶",
        "上次",
        "之前",
        "我申請什麼",
        "我預約什麼",
        "我的地址",
        "我的電話",
        "我的手機",
        "常用地址",
        "常用電話",
    )
    return any(hint in text for hint in hints)


def _reply_from_memory(actor_id: str) -> str | None:
    snapshot = MEMORY.get_memory_snapshot(actor_id)
    prefs = snapshot.get("preferences") or {}
    memory = snapshot.get("long_term_memory") or {}
    lines: list[str] = []

    if memory.get("last_service_name"):
        lines.append(f"我記得你上次申請的是「{memory['last_service_name']}」。")
    if prefs.get("last_address"):
        lines.append(f"常用地址是：{prefs['last_address']}")
    if prefs.get("last_phone"):
        lines.append(f"常用電話是：{prefs['last_phone']}")
    if prefs.get("preferred_time_slot"):
        slot = SELECT_DISPLAY_NAMES.get(prefs["preferred_time_slot"], prefs["preferred_time_slot"])
        lines.append(f"偏好時段是：{slot}")
    if memory.get("last_request_summary"):
        lines.append(f"上次摘要：{memory['last_request_summary']}")

    if not lines:
        return None

    lines.append("如果這次要沿用，我可以直接幫你接著填；如果要改，也可以直接告訴我要換哪一項。")
    return "\n".join(lines)


def current_active_field(state: dict) -> str | None:
    if state.get("pending_pref_field"):
        return state["pending_pref_field"]
    missing_fields = state.get("missing_fields") or []
    return missing_fields[0] if missing_fields else None


def build_form_schema(state: dict) -> dict | None:
    service_schema = state.get("service_schema")
    if not service_schema:
        return None
    return {
        "service_id": state.get("service_id"),
        "service_name": state.get("service_name"),
        "fields": [
            {
                "id": field["id"],
                "label": _display_field_label(field["id"], service_schema["fields"]),
                "type": field.get("type", "text"),
                "required": bool(field.get("required")),
                "options": list(field.get("options", [])),
            }
            for field in service_schema["fields"]
        ],
    }


def build_form_draft(state: dict) -> dict | None:
    service_schema = state.get("service_schema")
    if not service_schema:
        return None

    fields = service_schema["fields"]
    values = {
        field["id"]: state.get("collected_fields", {}).get(field["id"])
        for field in fields
    }
    return {
        "service_id": state.get("service_id"),
        "service_name": state.get("service_name"),
        "status": state.get("status"),
        "request_id": state.get("request_id"),
        "fields": values,
        "missing_fields": list(state.get("missing_fields", [])),
        "active_field": current_active_field(state),
        "ready_for_confirmation": bool(not state.get("missing_fields")),
    }


def apply_form_patch(actor_id: str, state: dict, form_fields: dict) -> dict:
    service_schema = state.get("service_schema")
    if not service_schema:
        return _reply(state, "請先告訴我想申請哪一項服務，我才能開出對應表單。")

    fields = service_schema["fields"]
    field_map = {field["id"]: field for field in fields}
    invalid_labels: list[str] = []
    changed = False

    for field_id, raw_value in (form_fields or {}).items():
        field = field_map.get(field_id)
        if not field:
            continue

        if raw_value in (None, ""):
            if field_id in state["collected_fields"]:
                state["collected_fields"].pop(field_id, None)
                changed = True
            continue

        normalized = _normalize_field_value(field, raw_value, str(raw_value))
        if normalized is None:
            invalid_labels.append(_display_field_label(field_id, fields))
            continue

        if state["collected_fields"].get(field_id) != normalized:
            state["collected_fields"][field_id] = normalized
            changed = True

    state["awaiting_confirmation"] = False
    state["pending_pref_field"] = None
    state["pending_pref_value"] = None
    state["pending_pref_question"] = None
    _recompute_missing(state)

    result = _continue_collection(actor_id, state, latest_user_message="表單已更新")
    if invalid_labels:
        result["reply"] = f"以下欄位格式我還沒成功讀懂：{'、'.join(invalid_labels)}。\n{result['reply']}"
    elif changed:
        result["reply"] = f"表單已更新。\n{result['reply']}"
    else:
        result["reply"] = f"目前沒有新的變更。\n{result['reply']}"
    return result


def _normalize_select(raw_value: str, options: list[str]) -> str | None:
    if raw_value in options:
        return raw_value

    normalized = raw_value.strip().upper()
    for option, aliases in SELECT_ALIASES.items():
        if option in options and any(alias.upper() in normalized for alias in aliases):
            return option
    return None


def _has_field_evidence(field_id: str, text: str) -> bool:
    if field_id in {"quantity", "hours"}:
        return bool(NUMERIC_HINT_RE.search(text))
    if field_id == "preferred_date":
        return nlu.parse_date(text, today=date.today()) is not None
    if field_id == "preferred_time_slot":
        return nlu.parse_time_slot(text) is not None
    if field_id == "phone":
        return nlu.parse_phone(text) is not None
    if field_id == "address":
        return nlu.parse_address(text) is not None
    if field_id == "machine_type":
        return nlu.parse_machine_type(text) is not None
    if field_id == "issue_description":
        return len(text.strip()) >= 2
    return True


def _normalize_field_value(field: dict, value, original_text: str):
    field_id = field["id"]
    if value in (None, ""):
        return None

    if field["type"] == "number":
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        if field_id == "hours":
            return nlu.parse_hours(str(value)) or nlu.parse_hours(original_text)
        return (
            nlu.parse_quantity(str(value), unit_chars="台個支")
            or nlu.parse_number(str(value))
            or nlu.parse_quantity(original_text)
        )

    if field["type"] == "date":
        if isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            try:
                normalized_date = date.fromisoformat(value)
                if normalized_date >= date.today():
                    return value
            except ValueError:
                pass
        return nlu.parse_date(str(value), today=date.today()) or nlu.parse_date(original_text, today=date.today())

    if field["type"] == "select":
        if field_id == "preferred_time_slot":
            return (
                _normalize_select(str(value), field.get("options", []))
                or nlu.parse_time_slot(str(value))
                or nlu.parse_time_slot(original_text)
            )
        if field_id == "machine_type":
            return (
                _normalize_select(str(value), field.get("options", []))
                or nlu.parse_machine_type(str(value))
                or nlu.parse_machine_type(original_text)
            )
        return _normalize_select(str(value), field.get("options", []))

    if field_id == "phone":
        return nlu.parse_phone(str(value)) or nlu.parse_phone(original_text)

    if field_id == "address":
        return nlu.parse_address(str(value)) or nlu.parse_address(original_text) or str(value).strip()

    return str(value).strip()


def _detect_service(text: str, services: list[dict], short_term_context: str, long_term_context: str) -> str | None:
    valid_ids = {service["id"] for service in services}
    llm_choice = llm.choose_service(
        text,
        services,
        short_term_memory=short_term_context,
        long_term_memory=long_term_context,
    )
    if llm_choice in valid_ids:
        return llm_choice

    for service_id, keywords in RULE_SERVICE_KEYWORDS:
        if service_id in valid_ids and any(keyword in text for keyword in keywords):
            return service_id

    rule_choice, _ = nlu.detect_service(text)
    return rule_choice if rule_choice in valid_ids else None


def _extract_fields(actor_id: str, state: dict, text: str, events: list[dict] | None) -> dict:
    fields = state["service_schema"]["fields"]
    short_term_context = _short_term_context(state, events, text)
    long_term_context = _long_term_memory_context(actor_id, text)
    form_schema = build_form_schema(state)
    form_draft = build_form_draft(state)

    found = nlu.extract_fields(state["service_id"], fields, text, state["collected_fields"])
    llm_fields = llm.extract_fields(
        message=text,
        service_name=_display_service_name(state["service_id"], state["service_name"]),
        fields=fields,
        collected_fields=state["collected_fields"],
        form_schema=form_schema,
        form_draft=form_draft,
        short_term_memory=short_term_context,
        long_term_memory=long_term_context,
    )

    for field in fields:
        field_id = field["id"]
        if field_id in state["collected_fields"] or field_id not in llm_fields:
            continue
        if not _has_field_evidence(field_id, text):
            continue
        normalized = _normalize_field_value(field, llm_fields[field_id], text)
        if normalized is not None:
            found.setdefault(field_id, normalized)

    field_ids = {field["id"] for field in fields}
    if state["missing_fields"] and state["missing_fields"][0] == "issue_description":
        if "issue_description" not in found and len(text.strip()) >= 2:
            found["issue_description"] = text
    elif "issue_description" in field_ids and "issue_description" not in state["collected_fields"]:
        if SERVICE_ISSUE_HINT_RE.search(text):
            found.setdefault("issue_description", text)

    return found


def _fallback_reply(state: dict, phase: str, **kwargs) -> str:
    if phase == "completed":
        return "這張申請已經送出囉，你可以到服務列表查看最新進度。"
    if phase == "service_catalog_error":
        return "我現在暫時無法讀取服務清單，請稍後再試一次。"
    if phase == "service_not_understood":
        services = kwargs.get("service_options") or []
        service_text = "、".join(services) if services else "水電修繕、洗衣機清洗、冷氣清洗、居家清潔"
        return f"我先幫你處理預約。請告訴我你想申請哪一項服務，目前可協助：{service_text}。"
    if phase == "service_schema_error":
        return "我有辨識到你要的服務，但目前抓不到表單欄位，請稍後再試一次。"
    if phase == "reuse_preference":
        value = kwargs.get("preferred_value", "")
        label = kwargs.get("missing_field_label", "這個資料")
        return f"我這邊有你先前填過的{label}：{value}。要直接沿用嗎？"
    if phase == "collect_field":
        question = kwargs.get("missing_field_question")
        return question or "請再提供下一項資訊，我幫你繼續完成預約。"
    if phase == "confirm":
        return kwargs.get("summary") or _build_summary_text(state)
    if phase == "confirmation_retry":
        return "收到，我先不送出。你可以直接告訴我哪一項要修改，我會幫你更新。"
    if phase == "submit_error":
        error_message = kwargs.get("error_message") or "送出時發生問題"
        return f"剛剛送單沒有成功，原因是：{error_message}。你可以再試一次，我也可以幫你重新整理資料。"
    if phase == "submit_success":
        request_id = kwargs.get("request_id", "")
        return f"已幫你建立案件 {request_id}，目前狀態是「等待廠商確認」。你之後可以到首頁的服務列表查看進度。"
    return "我來幫你處理，請再告訴我一次你的需求。"


def _model_reply(actor_id: str, state: dict, phase: str, latest_user_message: str = "", **kwargs) -> str:
    fields = (state.get("service_schema") or {}).get("fields", [])
    missing_fields = state.get("missing_fields") or []
    missing_field_id = missing_fields[0] if missing_fields else None
    missing_field_label = _display_field_label(missing_field_id, fields) if missing_field_id else ""
    missing_field_question = ""
    if missing_field_id:
        field = next((item for item in fields if item["id"] == missing_field_id), None)
        if field:
            missing_field_question = _build_field_question(field)

    short_term_memory = _short_term_context_from_state(state)
    long_term_query = latest_user_message or state.get("service_name") or state.get("service_id") or "服務預約"
    long_term_memory = _long_term_memory_context(actor_id, long_term_query)

    reply = llm.compose_reply(
        phase=phase,
        latest_user_message=latest_user_message,
        service_name=_display_service_name(state.get("service_id"), state.get("service_name")),
        collected_fields=state.get("collected_fields", {}),
        missing_field_label=kwargs.get("missing_field_label", missing_field_label),
        missing_field_question=kwargs.get("missing_field_question", missing_field_question),
        summary=kwargs.get("summary", ""),
        preferred_value=kwargs.get("preferred_value", ""),
        request_id=kwargs.get("request_id", ""),
        request_status=kwargs.get("request_status", ""),
        error_message=kwargs.get("error_message", ""),
        service_options=kwargs.get("service_options", []),
        short_term_memory=short_term_memory,
        long_term_memory=long_term_memory,
    )
    return reply or _fallback_reply(state, phase, **kwargs)


def new_state() -> dict:
    return {
        "service_id": None,
        "service_name": None,
        "service_schema": None,
        "collected_fields": {},
        "missing_fields": [],
        "awaiting_confirmation": False,
        "pending_pref_field": None,
        "pending_pref_value": None,
        "pending_pref_question": None,
        "asked_pref_fields": [],
        "request_id": None,
        "status": "COLLECTING_INFORMATION",
        "short_term_memory": [],
    }


def handle_message(
    actor_id: str,
    session_id: str,
    state: dict,
    message: str,
    events: list[dict] | None = None,
    auth_token: str | None = None,
) -> dict:
    text = message.strip()

    if state.get("request_id"):
        return _reply(state, _model_reply(actor_id, state, "completed", latest_user_message=text))

    if state.get("pending_pref_field"):
        field_id = state["pending_pref_field"]
        question = state.get("pending_pref_question") or ""
        verdict = _judge_reply(question, text)
        if verdict == "yes":
            state["collected_fields"][field_id] = state["pending_pref_value"]
        else:
            state["collected_fields"].update(_extract_fields(actor_id, state, text, events))
        state["pending_pref_field"] = None
        state["pending_pref_value"] = None
        state["pending_pref_question"] = None
        _recompute_missing(state)
        return _continue_collection(actor_id, state, latest_user_message=text, events=events)

    if state["awaiting_confirmation"]:
        verdict = _judge_reply("請確認以上申請內容是否正確。", text)
        if verdict == "yes":
            return _submit(actor_id, session_id, state, latest_user_message=text, auth_token=auth_token)

        override = _extract_fields(actor_id, state, text, events)
        if override:
            state["collected_fields"].update(override)
            state["awaiting_confirmation"] = False
            _recompute_missing(state)
            if not state["missing_fields"]:
                state["status"] = "AWAITING_USER_CONFIRMATION"
                summary = _build_summary_text(state)
                return _reply(state, _model_reply(actor_id, state, "confirm", latest_user_message=text, summary=summary))
            return _continue_collection(actor_id, state, latest_user_message=text, events=events)

        state["awaiting_confirmation"] = False
        state["status"] = "COLLECTING_INFORMATION"
        return _reply(state, _model_reply(actor_id, state, "confirmation_retry", latest_user_message=text))

    if not state["service_id"]:
        if _looks_like_memory_question(text):
            memory_reply = _reply_from_memory(actor_id)
            if memory_reply:
                return _reply(state, memory_reply)

        result = tools.call("list_services", {}, auth_token=auth_token)
        if not result.get("success", True):
            return _reply(state, _model_reply(actor_id, state, "service_catalog_error", latest_user_message=text))

        services = result["services"]
        short_term_context = _short_term_context(state, events, text)
        long_term_context = _long_term_memory_context(actor_id, text)
        service_id = _detect_service(text, services, short_term_context, long_term_context)
        if not service_id:
            return _reply(
                state,
                _model_reply(
                    actor_id,
                    state,
                    "service_not_understood",
                    latest_user_message=text,
                    service_options=[service["name"] for service in services],
                ),
            )

        schema_result = tools.call("get_service_schema", {"service_id": service_id}, auth_token=auth_token)
        if not schema_result.get("success", True):
            return _reply(state, _model_reply(actor_id, state, "service_schema_error", latest_user_message=text))

        service = next((item for item in services if item["id"] == service_id), None)
        state["service_id"] = service_id
        state["service_name"] = _display_service_name(service_id, (service or {}).get("name") or schema_result.get("title"))
        state["service_schema"] = {"fields": schema_result["fields"]}
        _recompute_missing(state)

    found = _extract_fields(actor_id, state, text, events)
    state["collected_fields"].update(found)
    _recompute_missing(state)
    return _continue_collection(actor_id, state, latest_user_message=text, events=events)


def _continue_collection(actor_id: str, state: dict, latest_user_message: str = "", events: list[dict] | None = None) -> dict:
    prefs = MEMORY.get_preferences(actor_id)
    fields = state["service_schema"]["fields"]
    asked = state.setdefault("asked_pref_fields", [])

    for field_id, pref_key in (
        ("address", "last_address"),
        ("phone", "last_phone"),
        ("preferred_time_slot", "preferred_time_slot"),
    ):
        if (
            field_id in state["missing_fields"]
            and prefs.get(pref_key)
            and state["missing_fields"][0] == field_id
            and field_id not in asked
        ):
            value = SELECT_DISPLAY_NAMES.get(prefs[pref_key], prefs[pref_key])
            asked.append(field_id)
            state["pending_pref_field"] = field_id
            state["pending_pref_value"] = prefs[pref_key]
            question = _model_reply(
                actor_id,
                state,
                "reuse_preference",
                latest_user_message=latest_user_message,
                preferred_value=value,
                missing_field_label=_display_field_label(field_id, fields),
            )
            state["pending_pref_question"] = question
            return _reply(state, question)

    if state["missing_fields"]:
        state["status"] = "COLLECTING_INFORMATION"
        field = next(item for item in fields if item["id"] == state["missing_fields"][0])
        question = _build_field_question(field)
        return _reply(
            state,
            _model_reply(
                actor_id,
                state,
                "collect_field",
                latest_user_message=latest_user_message,
                missing_field_label=_display_field_label(field["id"], fields),
                missing_field_question=question,
            ),
        )

    state["awaiting_confirmation"] = True
    state["status"] = "AWAITING_USER_CONFIRMATION"
    summary = _build_summary_text(state)
    return _reply(state, _model_reply(actor_id, state, "confirm", latest_user_message=latest_user_message, summary=summary))


def _update_long_term_memory(actor_id: str, state: dict) -> None:
    fields = state["service_schema"]["fields"]
    summary_lines = [f"服務：{_display_service_name(state['service_id'], state['service_name'])}"]
    for field in fields:
        if field["id"] in state["collected_fields"]:
            summary_lines.append(_display_value(field["id"], state["collected_fields"][field["id"]], fields))
    MEMORY.save_long_term_summary(
        actor_id,
        {
            "last_service_id": state["service_id"],
            "last_service_name": _display_service_name(state["service_id"], state["service_name"]),
            "last_request_summary": "；".join(summary_lines),
        },
    )


def _submit(
    actor_id: str,
    session_id: str,
    state: dict,
    latest_user_message: str = "",
    auth_token: str | None = None,
) -> dict:
    result = tools.call(
        "submit_service_request",
        {
            "service_id": state["service_id"],
            "session_id": session_id,
            "actor_id": actor_id,
            "payload": dict(state["collected_fields"]),
        },
        auth_token=auth_token,
    )
    if not result.get("success"):
        message = result.get("error", {}).get("message", "送出時發生未知錯誤")
        return _reply(
            state,
            _model_reply(
                actor_id,
                state,
                "submit_error",
                latest_user_message=latest_user_message,
                error_message=message,
            ),
        )

    state["request_id"] = result["request_id"]
    state["status"] = result["status"]
    state["awaiting_confirmation"] = False

    collected = state["collected_fields"]
    prefs = {}
    if collected.get("address"):
        prefs["last_address"] = collected["address"]
    if collected.get("phone"):
        prefs["last_phone"] = collected["phone"]
    if collected.get("preferred_time_slot"):
        prefs["preferred_time_slot"] = collected["preferred_time_slot"]
    if prefs:
        MEMORY.save_preferences(actor_id, prefs)

    _update_long_term_memory(actor_id, state)
    return _reply(
        state,
        (
            f"已幫你建立案件 {result['request_id']}。\n"
            "案件已送出，接下來會由廠商確認；你可以到首頁的服務列表查看最新進度。"
        ),
    )


def _reply(state: dict, reply: str) -> dict:
    return {"reply": reply, "state": state}
