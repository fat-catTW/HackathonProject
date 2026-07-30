"""Service booking agent with Bedrock-assisted extraction and reply generation."""
from __future__ import annotations

import re
from datetime import date

from ..config import get_settings
from ..services import catalog
from ..services import delivery, delivery_catalog, reservation, shipping
from ..services.conversation_memory import MEMORY
from . import llm, nlu, tools
from .page_help import (
    answer_page_question,
    build_page_tool_request,
    is_voice_filling_question,
    looks_like_page_question,
)

DECIMAL_NUMBER_RE = re.compile(r"\d+\.\d+")
SERVICE_TIME_MIN = "08:30"
SERVICE_TIME_MAX = "18:00"

CONFIRM_WORDS = ("確認", "確定", "好", "可以", "沒問題", "送出", "ok", "OK", "yes", "Yes")
DENY_WORDS = ("不要", "不用", "取消", "改一下", "先不要", "no", "No")

SERVICE_DISPLAY_NAMES = {
    "plumbing_repair": "水電修繕",
    "washing_machine_cleaning": "洗衣機清洗",
    "air_conditioner_cleaning": "冷氣清洗",
    "home_cleaning": "居家清潔",
    "food_delivery": "美食外送",
}

FIELD_DISPLAY_NAMES = {
    "issue_description": "問題描述",
    "issue_photo": "現場照片",
    "preferred_date": "服務日期",
    "preferred_time_slot": "服務時間",
    "address": "服務地址",
    "phone": "聯絡電話",
    "quantity": "數量",
    "machine_type": "洗衣機類型",
    "restaurant_id": "餐廳選擇",
    "reserved_date": "用餐日期",
    "time_slot": "用餐時段",
    "people": "用餐人數",
    "contact_name": "聯絡人姓名",
    "store_id": "店家",
    "goods": "餐點",
    "note": "備註需求",
    "air_conditioner_type": "冷氣機種",
    "antibacterial_film_addon": "是否加購日本抗菌膜",
    "antibacterial_film_quantity": "日本抗菌膜數量",
    "repair_item": "叫修工項",
    "cleaning_service_option": "服務選項",
    "notes": "備註",
}

SELECT_ALIASES = {
    "MORNING": ("MORNING", "上午", "早上"),
    "AFTERNOON": ("AFTERNOON", "下午"),
    "EVENING": ("EVENING", "晚上", "夜間"),
    "TOP_LOAD": ("TOP_LOAD", "直立式"),
    "FRONT_LOAD": ("FRONT_LOAD", "滾筒式"),
    "LUNCH": ("LUNCH", "午餐", "中午"),
    "DINNER": ("DINNER", "晚餐", "晚飯"),
    "STANDARD": ("STANDARD", "一般"),
    "PREMIUM": ("PREMIUM", "高級", "指定"),
    "YES": ("YES", "要", "需要", "加購"),
    "NO": ("NO", "不要", "不需要", "不用"),
    "壁掛式": ("壁掛式", "壁掛", "掛壁"),
    "天花板嵌入式": ("天花板嵌入式", "嵌入式", "天花板式"),
    "四方吹業務型": ("四方吹業務型", "四方吹", "業務型"),
    "地板清潔": ("地板清潔",),
    "石材地板研磨 晶化 拋光": ("石材地板研磨 晶化 拋光", "石材地板研磨", "晶化", "拋光"),
    "地毯清潔": ("地毯清潔",),
    "玻璃清潔": ("玻璃清潔",),
    "天花板除塵": ("天花板除塵", "除塵"),
    "廁所清潔": ("廁所清潔", "浴室清潔"),
    "HOME_PICKUP": ("HOME_PICKUP", "到府收件", "到府", "宅配到府"),
    "STORE_TO_STORE": ("STORE_TO_STORE", "店到店", "超商", "7-11", "7-ELEVEN"),
}

SELECT_DISPLAY_NAMES = {
    "MORNING": "上午",
    "AFTERNOON": "下午",
    "EVENING": "晚上",
    "TOP_LOAD": "直立式",
    "FRONT_LOAD": "滾筒式",
    "LUNCH": "午餐",
    "DINNER": "晚餐",
    "STANDARD": "一般訂位",
    "PREMIUM": "高級訂位",
    "YES": "需要",
    "NO": "不需要",
    "HOME_PICKUP": "到府收件",
    "STORE_TO_STORE": "7-11 店到店",
}

RULE_SERVICE_KEYWORDS = (
    ("plumbing_repair", ("水電", "修繕", "漏水", "插座", "燈具", "浴室", "維修")),
    ("washing_machine_cleaning", ("洗衣機", "清洗", "滾筒式", "直立式", "內槽")),
    ("air_conditioner_cleaning", ("冷氣", "清洗", "保養", "壁掛式", "室內機")),
    ("home_cleaning", ("清潔", "居家", "打掃", "整理", "到府")),
)

# goods/store_id 一律透過下方的購物車收集子流程取得，不透過 LLM 猜測
# （store_id 沒有靜態 options 所以本來就猜不中；goods 是清單型別，讓 LLM
#  猜測容易產生格式不符的字串，直接排除避免污染 collected_fields）。
_LLM_EXCLUDED_FIELDS = {"store_id", "goods"}


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
    names = {
        "plumbing_repair": "水電修繕",
        "washing_machine_cleaning": "洗衣機清洗",
        "air_conditioner_cleaning": "冷氣清洗",
        "home_cleaning": "居家清潔",
    }
    if service_id and service_id in names:
        return names[service_id]
    return fallback or "服務"


def _display_field_label(field_id: str, fields: list[dict]) -> str:
    field = next((item for item in fields if item["id"] == field_id), None)
    fallback_labels = {
        "issue_description": "問題描述",
        "issue_photo": "現場照片",
        "preferred_date": "服務日期",
        "preferred_time_slot": "服務時間",
        "address": "服務地址",
        "phone": "聯絡電話",
        "quantity": "數量",
        "machine_type": "洗衣機類型",
        "air_conditioner_type": "冷氣機種",
        "antibacterial_film_addon": "是否加購日本抗菌膜",
        "antibacterial_film_quantity": "日本抗菌膜數量",
        "repair_item": "叫修工項",
        "cleaning_service_option": "服務選項",
        "notes": "備註",
    }
    return (field or {}).get("label") or fallback_labels.get(field_id) or field_id


def _display_value(field_id: str, value, fields: list[dict]) -> str:
    if isinstance(value, str):
        display_names = {
            "TOP_LOAD": "直立式",
            "FRONT_LOAD": "滾筒式",
            "YES": "需要",
            "NO": "不需要",
            "MORNING": "上午",
            "AFTERNOON": "下午",
            "EVENING": "晚上",
        }
        value = display_names.get(value, catalog.SELECT_LABELS.get(value, value))
    label = _display_field_label(field_id, fields)
    if field_id == "issue_photo" and isinstance(value, str) and value.startswith("data:image/"):
        value = "已上傳照片"
    unit = " 台" if field_id == "quantity" else " 個" if field_id == "antibacterial_film_quantity" else ""
    return f"{label}：{value}{unit}"


def _build_summary_text(state: dict) -> str:
    fields = state["service_schema"]["fields"]
    lines = ["請確認以下申請內容：", f"服務：{_display_service_name(state['service_id'], state['service_name'])}"]
    for field in fields:
        field_id = field["id"]
        if field_id not in state["collected_fields"]:
            continue
        if state["service_id"] == "package_shipping" and not _field_is_visible(field, state["collected_fields"]):
            continue
        if field_id == "store_id":
            store = delivery_catalog.get_store(state["collected_fields"]["store_id"])
            lines.append(f"店家：{store['name'] if store else state['collected_fields']['store_id']}")
            continue
        if field_id == "goods":
            lines.append("餐點：")
            for item in state["collected_fields"]["goods"]:
                lines.append(f"　{item['title']} x{item['quantity']}")
            continue
        lines.append(_display_value(field_id, state["collected_fields"][field_id], fields))
    lines.append("")
    lines.append("如果資料正確請直接回覆「確認送出」，如果要修改請直接告訴我要改哪一項。")
    return "\n".join(lines)


def _build_field_question(field: dict) -> str:
    field_id = field["id"]
    if field_id == "preferred_date":
        return "你希望安排哪一天服務呢？請提供日期。"
    if field_id == "preferred_time_slot":
        return "你希望安排什麼時間服務呢？請直接提供像 14:30 這樣的時間。"
    if field_id == "address":
        return "請提供服務地址。"
    if field_id == "phone":
        return "請提供聯絡電話。"
    if field_id == "repair_item":
        return "請問這次的叫修工項是什麼呢？"
    if field["id"] == "issue_description":
        return "請描述你要處理的問題，例如漏水位置、設備故障或想清洗的項目。"
    if field_id == "issue_photo":
        return "如果方便的話，也可以補一張現場照片。"
    if field["id"] == "preferred_date":
        return "你希望安排哪一天服務呢？"
    if field["id"] == "preferred_time_slot":
        return "你比較方便的服務時間是幾點呢？例如 09:30 或 14:00。"
    if field["id"] == "address":
        return "請提供完整的服務地址，方便安排人員前往。"
    if field["id"] == "phone":
        return "請提供方便聯絡的電話號碼。"
    if field["id"] == "quantity":
        return "這次需要處理幾台呢？"
    if field["id"] == "machine_type":
        return "請問是直立式還是滾筒式洗衣機呢？"
    if field_id == "air_conditioner_type":
        return "請問冷氣機種是壁掛式、天花板嵌入式，還是四方吹業務型呢？"
    if field_id == "antibacterial_film_addon":
        return "請問是否需要加購日本抗菌膜呢？"
    if field_id == "antibacterial_film_quantity":
        return "請問要加購幾個日本抗菌膜呢？"
    if field_id == "cleaning_service_option":
        return "請問這次需要哪一種居家清潔服務呢？"
    return field.get("question") or f"請提供{field.get('label') or field['id']}。"


def _field_is_visible(field: dict, collected: dict) -> bool:
    visible_when = field.get("visibleWhen")
    if not isinstance(visible_when, dict):
        return True
    parent_field_id = visible_when.get("fieldId")
    expected_value = visible_when.get("value")
    if not isinstance(parent_field_id, str):
        return True
    return collected.get(parent_field_id) == expected_value


def _recompute_missing(state: dict) -> None:
    fields = state["service_schema"]["fields"]
    collected = state["collected_fields"]
    state["missing_fields"] = [
        field["id"]
        for field in fields
        if field.get("required") and field["id"] not in collected and _field_is_visible(field, collected)
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
    try:
        return MEMORY.get_long_term_context(actor_id, query)
    except Exception:
        return "None"


def _safe_memory_snapshot(actor_id: str) -> dict:
    try:
        return MEMORY.get_memory_snapshot(actor_id)
    except Exception:
        return {"preferences": {}, "long_term_memory": {}}


def _safe_preferences(actor_id: str) -> dict:
    return _safe_memory_snapshot(actor_id).get("preferences") or {}


def _normalize_saved_time_value(value: str) -> str:
    legacy_map = {
        "MORNING": "09:00",
        "AFTERNOON": "14:00",
        "EVENING": "18:00",
    }
    if value in legacy_map:
        return legacy_map[value]
    parsed = nlu.parse_service_time(value)
    return parsed or value


def _is_supported_service_time(value: str) -> bool:
    return SERVICE_TIME_MIN <= value <= SERVICE_TIME_MAX


def _looks_like_memory_question(text: str) -> bool:
    hints = (
        "記得",
        "記住",
        "之前",
        "上次",
        "上一次",
        "上一個",
        "最近",
        "剛剛",
        "我的地址",
        "我的電話",
        "我的資料",
        "上次地址",
        "上次電話",
    )
    return any(hint in text for hint in hints)


def _reply_from_memory(actor_id: str) -> str | None:
    snapshot = _safe_memory_snapshot(actor_id)
    prefs = snapshot.get("preferences") or {}
    memory = snapshot.get("long_term_memory") or {}
    lines: list[str] = []

    if memory.get("last_service_name"):
        lines.append(f"你上次申請的服務是：{memory['last_service_name']}")
    if prefs.get("last_address"):
        lines.append(f"上次地址：{prefs['last_address']}")
    if prefs.get("last_phone"):
        lines.append(f"上次電話：{prefs['last_phone']}")
    if prefs.get("preferred_time_slot"):
        slot = _normalize_saved_time_value(str(prefs["preferred_time_slot"]))
        lines.append(f"常用時間：{slot}")
    if memory.get("last_request_summary"):
        lines.append(f"最近一次案件摘要：{memory['last_request_summary']}")

    if not lines:
        return None

    lines.append("如果你要沿用其中的資料，我也可以直接幫你帶入新的申請。")
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
                "minValue": field.get("minValue"),
                "maxValue": field.get("maxValue"),
                "step": field.get("step"),
                "visibleWhen": field.get("visibleWhen"),
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
        return _reply(state, "目前還沒有選定服務，請先告訴我你想申請哪一種服務。")

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

    result = _continue_collection(actor_id, state, latest_user_message="已更新表單資料")
    if invalid_labels:
        result["reply"] = f"有幾項資料格式不正確：{'、'.join(invalid_labels)}。\n{result['reply']}"
    elif changed:
        result["reply"] = f"表單資料已更新。\n{result['reply']}"
    else:
        result["reply"] = f"目前沒有需要變更的欄位。\n{result['reply']}"
    return result


def _normalize_select(raw_value: str, options: list[str]) -> str | None:
    if raw_value in options:
        return raw_value

    normalized_raw = raw_value.strip()
    for option in options:
        if option and (option in normalized_raw or normalized_raw in option):
            return option

    normalized = raw_value.strip().upper()
    for option, aliases in SELECT_ALIASES.items():
        if option in options and any(alias.upper() in normalized for alias in aliases):
            return option
    return None


def _normalize_field_value(field: dict, value, original_text: str):
    field_id = field["id"]
    if value in (None, ""):
        return None

    if field["type"] == "number":
        if DECIMAL_NUMBER_RE.search(str(value)) or DECIMAL_NUMBER_RE.search(original_text):
            return None
        if isinstance(value, int):
            return value if value > 0 else None
        if isinstance(value, float):
            return int(value) if value > 0 and float(value).is_integer() else None
        if field_id == "antibacterial_film_quantity":
            return (
                nlu.parse_quantity(str(value), unit_chars="個片張")
                or nlu.parse_number(str(value))
                or nlu.parse_quantity(original_text, unit_chars="個片張")
            )
        return (
            nlu.parse_quantity(str(value), unit_chars="台個")
            or nlu.parse_number(str(value))
            or nlu.parse_quantity(original_text, unit_chars="台個")
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

    if field["type"] == "time":
        if isinstance(value, str) and re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", value):
            return value if _is_supported_service_time(value) else None
        parsed_time = nlu.parse_service_time(str(value)) or nlu.parse_service_time(original_text)
        if parsed_time and _is_supported_service_time(parsed_time):
            return parsed_time
        return None

    if field["type"] == "select":
        if field_id == "pickup_method":
            return (
                _normalize_select(str(value), field.get("options", []))
                or nlu.parse_pickup_method(str(value))
                or nlu.parse_pickup_method(original_text)
            )
        if field_id == "machine_type":
            return (
                _normalize_select(str(value), field.get("options", []))
                or nlu.parse_machine_type(str(value))
                or nlu.parse_machine_type(original_text)
            )
        if field_id == "restaurant_id":
            # 餐廳代碼（r001~r006）對 LLM 不具語意，容易在合法代碼間猜錯；
            # 優先信任從原始文字比對餐廳名稱的規則解析（決定性、不會猜錯），
            # LLM 給的代碼只在規則解析找不到時才採用。
            return (
                nlu.parse_restaurant(original_text)
                or nlu.parse_restaurant(str(value))
                or _normalize_select(str(value), field.get("options", []))
            )
        if field_id == "time_slot":
            return (
                _normalize_select(str(value), field.get("options", []))
                or nlu.parse_meal_slot(str(value))
                or nlu.parse_meal_slot(original_text)
            )
        if field_id == "antibacterial_film_addon":
            return (
                _normalize_select(str(value), field.get("options", []))
                or nlu.parse_yes_no_option(str(value))
                or nlu.parse_yes_no_option(original_text)
            )
        if field_id in {"repair_item", "air_conditioner_type", "cleaning_service_option"}:
            return (
                _normalize_select(str(value), field.get("options", []))
                or nlu.parse_option(str(value), field.get("options", []))
                or nlu.parse_option(original_text, field.get("options", []))
            )
        return _normalize_select(str(value), field.get("options", []))

    if field_id == "phone":
        return nlu.parse_phone(str(value)) or nlu.parse_phone(original_text)

    if field["type"] == "address":
        return nlu.parse_address(str(value)) or nlu.parse_address(original_text) or str(value).strip()

    if field["type"] == "file":
        text = str(value).strip()
        return text if text.startswith("data:image/") else None

    text = str(value).strip()
    return text or None


def _message_matches_service(text: str, service_id: str, services: list[dict]) -> bool:
    service = next((item for item in services if item["id"] == service_id), None)
    if not service:
        return False

    keywords = list(service.get("keywords", []))
    if service.get("name"):
        keywords.append(service["name"])
    if service.get("description"):
        keywords.extend([part for part in re.split(r"[、，。\s]+", service["description"]) if len(part) >= 2])
    return any(keyword and keyword in text for keyword in keywords)


def _detect_service(text: str, services: list[dict], short_term_context: str, long_term_context: str) -> str | None:
    valid_ids = {service["id"] for service in services}
    llm_choice = llm.choose_service(
        text,
        services,
        short_term_memory=short_term_context,
        long_term_memory=long_term_context,
    )
    if llm_choice in valid_ids and _message_matches_service(text, llm_choice, services):
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

    found: dict = {}
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
        if field_id in _LLM_EXCLUDED_FIELDS:
            continue
        if field_id not in llm_fields:
            continue
        normalized = _normalize_field_value(field, llm_fields[field_id], text)
        if normalized is not None:
            found[field_id] = normalized

    return found


def _fallback_reply(state: dict, phase: str, **kwargs) -> str:
    if phase == "completed":
        service_name = _display_service_name(state.get("service_id"), state.get("service_name"))
        request_id = state.get("request_id") or "目前案件"
        return (
            f"你目前已經有一筆 {service_name} 案件，案件編號是 {request_id}。"
            "如果你想查看進度，我可以協助說明；如果你要新增別的服務，也可以直接告訴我你要預約哪一種。"
        )
    if phase == "service_catalog_error":
        return "我現在暫時無法讀取服務清單，請稍後再試。"
    if phase == "service_not_understood":
        services = kwargs.get("service_options") or []
        service_text = "、".join(services) if services else "水電修繕、洗衣機清洗、冷氣清洗、居家清潔"
        return f"我目前只支援這幾種服務：{service_text}。你可以直接告訴我想預約哪一種。"
    if phase == "service_schema_error":
        return "我現在暫時無法讀取這項服務的表單，請稍後再試。"
    if phase == "reuse_preference":
        value = kwargs.get("preferred_value", "")
        label = kwargs.get("missing_field_label", "資料")
        return f"我這邊有你上次使用的{label}：{value}。這次要沿用嗎？"
    if phase == "collect_field":
        question = kwargs.get("missing_field_question")
        return question or "請再補充下一項必填資料。"
    if phase == "confirm":
        return kwargs.get("summary") or _build_summary_text(state)
    if phase == "confirmation_retry":
        return "如果資料正確請回覆「確認送出」，如果要修改請直接告訴我哪一項要改。"
    if phase == "submit_error":
        error_message = kwargs.get("error_message") or "送出失敗"
        return f"抱歉，這次送出沒有成功，原因是：{error_message}。你可以稍後再試，或直接把要修改的資料告訴我。"
    if phase == "submit_success":
        request_id = kwargs.get("request_id", "")
        return f"已幫你建立案件 {request_id}。案件已送出，接下來可以到我的服務查看最新進度。"
    return "我先幫你整理需求，你也可以直接告訴我下一個要補的資訊。"


def _model_reply(actor_id: str, state: dict, phase: str, latest_user_message: str = "", **kwargs) -> str:
    if not llm.is_available():
        return _fallback_reply(state, phase, **kwargs)

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
        "pending_delivery_field": None,
        "pending_prohibited_item": None,
        "prohibited_item_acknowledged": False,
        "request_id": None,
        "status": "COLLECTING_INFORMATION",
        "short_term_memory": [],
    }


def _available_services(auth_token: str | None = None) -> list[dict] | None:
    result = tools.call("list_services", {}, auth_token=auth_token)
    if result.get("success", True) and isinstance(result.get("services"), list):
        return result["services"]
    if get_settings().use_mock:
        return catalog.list_services()
    return None


def _service_schema(service_id: str, auth_token: str | None = None) -> dict | None:
    result = tools.call("get_service_schema", {"service_id": service_id}, auth_token=auth_token)
    if result.get("success", True) and isinstance(result.get("fields"), list):
        return {
            "service_id": result.get("service_id", service_id),
            "title": result.get("title") or _display_service_name(service_id),
            "fields": result.get("fields", []),
        }
    if get_settings().use_mock:
        return catalog.get_service_schema(service_id)
    return None


def _looks_like_new_service_request(text: str) -> bool:
    hints = ("我要", "我想", "想要", "預約", "安排", "需要", "服務", "清洗", "清潔", "維修", "修繕", "打掃")
    return any(hint in text for hint in hints)


def _page_help_reply(text: str, current_page_id: str | None, auth_token: str | None) -> str | None:
    if is_voice_filling_question(text):
        return answer_page_question(text, current_page_id=current_page_id)

    tool_request = build_page_tool_request(text, current_page_id=current_page_id)
    tool_payload: dict | None = None

    if tool_request:
        tool_name, params = tool_request
        result = tools.call(tool_name, params, auth_token=auth_token)
        if result.get("success"):
            tool_payload = result

    if tool_payload and llm.is_available():
        llm_reply = llm.compose_page_help_reply(
            latest_user_message=text,
            current_page_id=current_page_id or "",
            tool_payload=tool_payload,
        )
        if llm_reply:
            return llm_reply

    return answer_page_question(text, current_page_id=current_page_id, tool_payload=tool_payload)


def _invalid_number_field_message(state: dict, latest_user_message: str) -> str | None:
    if not DECIMAL_NUMBER_RE.search(latest_user_message):
        return None
    missing_fields = state.get("missing_fields") or []
    if not missing_fields:
        return None
    field_id = missing_fields[0]
    if field_id == "quantity":
        return "數量需要填整數，例如 1 台或 2 台，不能填 0.1 台。"
    if field_id == "antibacterial_film_quantity":
        return "日本抗菌膜數量需要填整數，例如 1 個或 2 個，不能填 0.5 個。"
    return None


def handle_message(
    actor_id: str,
    session_id: str,
    state: dict,
    message: str,
    events: list[dict] | None = None,
    current_page_id: str | None = None,
    auth_token: str | None = None,
) -> dict:
    text = message.strip()

    page_reply = _page_help_reply(text, current_page_id=current_page_id, auth_token=auth_token) if looks_like_page_question(
        text,
        current_page_id=current_page_id,
    ) else None
    if page_reply:
        return _reply(state, page_reply)

    if state.get("request_id"):
        services = _available_services(auth_token)
        if services is None:
            return _reply(state, _model_reply(actor_id, state, "service_catalog_error", latest_user_message=text))
        short_term_context = _short_term_context(state, events, text)
        long_term_context = _long_term_memory_context(actor_id, text)
        if _looks_like_new_service_request(text):
            service_id = _detect_service(text, services, short_term_context, long_term_context)
            if service_id:
                state = new_state()
            else:
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
        else:
            return _reply(state, _model_reply(actor_id, state, "completed", latest_user_message=text))

    if state.get("pending_delivery_field"):
        return _handle_delivery_pending_reply(actor_id, state, text, events)

    if state.get("pending_prohibited_item"):
        return _handle_prohibited_item_reply(actor_id, state, text, events)

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
        _recompute_missing(state)
        if state["missing_fields"]:
            state["awaiting_confirmation"] = False
            state["status"] = "COLLECTING_INFORMATION"
            return _continue_collection(actor_id, state, latest_user_message=text, events=events)

        verdict = _judge_reply("請確認以上內容是否正確，若正確請回覆確認送出。", text)
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

        services = _available_services(auth_token)
        if services is None:
            return _reply(state, _model_reply(actor_id, state, "service_catalog_error", latest_user_message=text))
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

        schema_result = _service_schema(service_id, auth_token)
        if not schema_result:
            return _reply(state, _model_reply(actor_id, state, "service_schema_error", latest_user_message=text))

        service = next((item for item in services if item["id"] == service_id), None)
        state["service_id"] = service_id
        state["service_name"] = _display_service_name(service_id, (service or {}).get("name") or schema_result.get("title"))
        state["service_schema"] = {"fields": schema_result["fields"]}
        _recompute_missing(state)

    found = _extract_fields(actor_id, state, text, events)
    if state.get("service_id") == "package_shipping" and "item_description" in found:
        matched = shipping.contains_prohibited_keywords(found["item_description"])
        if matched:
            state["pending_prohibited_item"] = found.pop("item_description")
            state["collected_fields"].update(found)
            _recompute_missing(state)
            categories = "、".join(matched)
            return _reply(
                state,
                f"你提到的內容物可能屬於「{categories}」類別，這類物品寄送有限制。"
                "請問已詳讀寄送規範，確認可以寄送嗎？如果不確定，也可以直接重新描述內容物。",
            )
    state["collected_fields"].update(found)
    _recompute_missing(state)
    return _continue_collection(actor_id, state, latest_user_message=text, events=events)


def _continue_collection(actor_id: str, state: dict, latest_user_message: str = "", events: list[dict] | None = None) -> dict:
    if state.get("service_id") == "food_delivery":
        return _continue_delivery_collection(actor_id, state, latest_user_message, events)
    return _continue_generic_collection(actor_id, state, latest_user_message, events)


def _menu_text(store: dict) -> str:
    return "、".join(f"{item['title']}（${item['price']}）" for item in store["menu"])


def _continue_delivery_collection(actor_id: str, state: dict, latest_user_message: str = "", events: list[dict] | None = None) -> dict:
    collected = state["collected_fields"]

    if "store_id" not in collected:
        state["pending_delivery_field"] = "store"
        names = "、".join(s["name"] for s in delivery_catalog.list_stores())
        return _reply(state, f"請問想點哪一間店家？目前提供：{names}。")

    if not collected.get("goods"):
        state["pending_delivery_field"] = "item"
        store = delivery_catalog.get_store(collected["store_id"])
        menu_text = _menu_text(store)
        return _reply(state, f"這間店的餐點有：{menu_text}。想點哪一項？可以先說一項，要加點我再問。")

    _recompute_missing(state)
    return _continue_generic_collection(actor_id, state, latest_user_message, events)


def _handle_delivery_pending_reply(actor_id: str, state: dict, text: str, events: list[dict] | None) -> dict:
    pending = state["pending_delivery_field"]

    if pending == "store":
        store_id = nlu.parse_delivery_store(text)
        if not store_id:
            names = "、".join(s["name"] for s in delivery_catalog.list_stores())
            return _reply(state, f"不好意思，目前沒有找到這間店家，請問想點：{names} 哪一間呢？")
        state["collected_fields"]["store_id"] = store_id
        state["pending_delivery_field"] = None
        return _continue_delivery_collection(actor_id, state, text, events)

    if pending == "item":
        store = delivery_catalog.get_store(state["collected_fields"]["store_id"])
        item = nlu.parse_menu_item(text, state["collected_fields"]["store_id"])
        if not item:
            menu_text = _menu_text(store)
            return _reply(state, f"這個品項目前菜單上沒有找到，這間店的餐點有：{menu_text}。要不要換一個？")
        state["collected_fields"].setdefault("goods", []).append(item)
        state["pending_delivery_field"] = "more_items"
        return _reply(state, f"已加入 {item['title']} x{item['quantity']}。還要加點別的嗎？")

    if pending == "more_items":
        verdict = _judge_reply("還要加點別的嗎？", text)
        if verdict == "yes":
            state["pending_delivery_field"] = "item"
            store = delivery_catalog.get_store(state["collected_fields"]["store_id"])
            menu_text = _menu_text(store)
            return _reply(state, f"這間店的餐點有：{menu_text}。想點哪一項？")
        state["pending_delivery_field"] = None
        _recompute_missing(state)
        return _continue_delivery_collection(actor_id, state, text, events)

    state["pending_delivery_field"] = None
    return _continue_delivery_collection(actor_id, state, text, events)


def _handle_prohibited_item_reply(actor_id: str, state: dict, text: str, events: list[dict] | None) -> dict:
    pending_text = state["pending_prohibited_item"]
    verdict = _judge_reply("已詳讀寄送規範，確認可以寄送嗎？", text)
    state["pending_prohibited_item"] = None
    if verdict == "yes":
        state["collected_fields"]["item_description"] = pending_text
        state["prohibited_item_acknowledged"] = True
        _recompute_missing(state)
        return _continue_collection(actor_id, state, latest_user_message=text, events=events)
    return _reply(state, "好的，請重新描述包裹內容物，我們可以再確認一次是否能寄送。")


def _continue_generic_collection(actor_id: str, state: dict, latest_user_message: str = "", events: list[dict] | None = None) -> dict:
    prefs = _safe_preferences(actor_id)
    fields = state["service_schema"]["fields"]
    asked = state.setdefault("asked_pref_fields", [])

    for field_id, pref_key in (
        ("preferred_time_slot", "preferred_time_slot"),
        ("address", "last_address"),
        ("phone", "last_phone"),
    ):
        if (
            field_id in state["missing_fields"]
            and prefs.get(pref_key)
            and state["missing_fields"][0] == field_id
            and field_id not in asked
        ):
            if field_id == "preferred_time_slot":
                value = _normalize_saved_time_value(str(prefs[pref_key]))
                pending_value = value
            else:
                value = SELECT_DISPLAY_NAMES.get(prefs[pref_key], prefs[pref_key])
                pending_value = prefs[pref_key]
            asked.append(field_id)
            state["pending_pref_field"] = field_id
            state["pending_pref_value"] = pending_value
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
        invalid_message = _invalid_number_field_message(state, latest_user_message)
        if invalid_message:
            return _reply(state, f"{invalid_message}\n{question}")
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
    try:
        MEMORY.save_long_term_summary(
            actor_id,
            {
                "last_service_id": state["service_id"],
                "last_service_name": _display_service_name(state["service_id"], state["service_name"]),
                "last_request_summary": "；".join(summary_lines),
            },
        )
    except Exception:
        return None


def _submit(
    actor_id: str,
    session_id: str,
    state: dict,
    latest_user_message: str = "",
    auth_token: str | None = None,
) -> dict:
    _recompute_missing(state)
    if state.get("missing_fields"):
        state["awaiting_confirmation"] = False
        state["status"] = "COLLECTING_INFORMATION"
        return _continue_collection(actor_id, state, latest_user_message=latest_user_message)

    if state["service_id"] == "restaurant_reservation":
        return _submit_reservation(actor_id, state, latest_user_message)

    if state["service_id"] == "food_delivery":
        return _submit_delivery(actor_id, state, latest_user_message)

    if state["service_id"] == "package_shipping":
        return _submit_package_shipping(actor_id, state, latest_user_message)

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
        message = result.get("error", {}).get("message", "送出失敗")
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
        try:
            MEMORY.save_preferences(actor_id, prefs)
        except Exception:
            pass

    _update_long_term_memory(actor_id, state)
    return _reply(
        state,
        _model_reply(
            actor_id,
            state,
            "submit_success",
            latest_user_message=latest_user_message,
            request_id=result["request_id"],
        ),
    )


def _submit_reservation(actor_id: str, state: dict, latest_user_message: str) -> dict:
    collected = state["collected_fields"]
    payload = {
        "restaurant_id": collected.get("restaurant_id"),
        "reserved_date": collected.get("reserved_date"),
        "time_slot": collected.get("time_slot"),
        "people": collected.get("people"),
        "contact_name": collected.get("contact_name"),
        "phone": collected.get("phone"),
        "is_premium": collected.get("is_premium") == "PREMIUM",
    }
    result = reservation.create_reservation_order(actor_id, payload)

    if not result.get("success"):
        message = result.get("error", {}).get("message", "訂位失敗")
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
    return _reply(
        state,
        _model_reply(
            actor_id,
            state,
            "submit_success",
            latest_user_message=latest_user_message,
            request_id=result["request_id"],
        ),
    )


def _submit_delivery(actor_id: str, state: dict, latest_user_message: str) -> dict:
    collected = state["collected_fields"]
    store_id = collected.get("store_id")
    store = delivery_catalog.get_store(store_id) or {}
    payload = {
        "address": {
            "lat": 25.033,
            "lng": 121.565,
            "area": "",
            "city": "台北市",
            "street": collected.get("address", ""),
            "remark": "",
            "contact_name": collected.get("contact_name", ""),
        },
        "goods": collected.get("goods", []),
        "store_id": store_id,
        "store_name": store.get("name", ""),
        "store_address": store.get("address", ""),
        "note": collected.get("note", ""),
        "shipping_fee": 60,
    }
    result = delivery.create_delivery_order(actor_id, payload)

    if not result.get("success"):
        message = result.get("error", {}).get("message", "外送訂單建立失敗")
        state["awaiting_confirmation"] = False
        state["status"] = "COLLECTING_INFORMATION"
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
    state["status"] = "SUBMITTED"
    state["awaiting_confirmation"] = False
    return _reply(
        state,
        _model_reply(
            actor_id,
            state,
            "submit_success",
            latest_user_message=latest_user_message,
            request_id=result["request_id"],
        ),
    )


def _submit_package_shipping(actor_id: str, state: dict, latest_user_message: str) -> dict:
    fields = state["service_schema"]["fields"]
    collected = state["collected_fields"]
    payload = {
        field["id"]: collected[field["id"]]
        for field in fields
        if field["id"] in collected and _field_is_visible(field, collected)
    }
    payload["prohibited_item_ack"] = bool(state.get("prohibited_item_acknowledged"))
    result = shipping.create_shipping_order(actor_id, payload)

    if not result.get("success"):
        message = result.get("error", {}).get("message", "包裹寄送建立失敗")
        state["awaiting_confirmation"] = False
        state["status"] = "COLLECTING_INFORMATION"
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

    reply = _model_reply(
        actor_id,
        state,
        "submit_success",
        latest_user_message=latest_user_message,
        request_id=result["request_id"],
    )
    fee_min = result.get("estimated_fee_min")
    fee_max = result.get("estimated_fee_max")
    if fee_min is not None:
        reply = f"{reply}\n依重量與材積試算，預估運費約 NT${fee_min}–{fee_max}，正式報價將由客服於 30 分鐘內回覆確認。"
    return _reply(state, reply)


def _reply(state: dict, reply: str) -> dict:
    return {"reply": reply, "state": state}
