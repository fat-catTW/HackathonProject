"""Service booking agent with Bedrock-assisted extraction and reply generation."""
from __future__ import annotations

import re
from datetime import date

from ..config import get_settings
from ..services import catalog, clock
from ..services import delivery, delivery_catalog, quick_purchase, reservation, shipping
from ..services.conversation_memory import MEMORY
from . import form_autopilot, llm, nlu, tools
from .page_catalog import search_pages
from .page_help import (
    answer_page_question,
    build_page_tool_request,
    is_voice_filling_question,
    looks_like_page_question,
)
from .page_catalog import is_navigation_query

DECIMAL_NUMBER_RE = re.compile(r"\d+\.\d+")
SERVICE_TIME_MIN = "08:30"
SERVICE_TIME_MAX = "18:00"

CONFIRM_WORDS = ("確認", "確定", "好", "可以", "沒問題", "送出", "ok", "OK", "yes", "Yes")
DENY_WORDS = ("不要", "不用", "取消", "改一下", "先不要", "no", "No")
ORDER_HISTORY_MEMORY_HINTS = (
    "我的服務",
    "我的訂單",
    "訂單",
    "下訂",
    "已下訂",
    "已經下訂",
    "查訂單",
    "查看訂單",
    "服務列表",
    "訂單列表",
    "案件進度",
    "訂單進度",
)

SERVICE_DISPLAY_NAMES = {
    "plumbing_repair": "水電修繕",
    "washing_machine_cleaning": "洗衣機清洗",
    "air_conditioner_cleaning": "冷氣清洗",
    "home_cleaning": "居家清潔",
    "food_delivery": "美食外送",
    "quick_purchase": "快速下單",
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
    "天花板嵌入式": ("天花板嵌入式", "嵌入式", "天花板式", "天花板的", "吊隱式", "吊隱"),
    "四方吹業務型": ("四方吹業務型", "四方吹", "業務型", "四方吹的"),
    "地板清潔": ("地板清潔", "地板清理", "清地板"),
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
FREE_TEXT_FIELD_IDS = {"issue_description", "notes", "note", "issue_details", "query"}
# 比對「模型填的自由文字是不是使用者剛剛說的」時忽略的標點與空白。
_GROUNDING_NOISE_RE = re.compile(r"[\s，。、！？!?,.:：；;~～「」『』（）()]+")


def _reset_debug_trace(state: dict, message: str) -> None:
    state["debug_trace"] = {
        "message": message,
        "llm_available": llm.is_available(),
        "turn_router": None,
        "form_router": None,
        "field_sources": [],
        "fallbacks": [],
    }


def _trace_field_source(state: dict, field_id: str, source: str) -> None:
    trace = state.setdefault("debug_trace", {})
    trace.setdefault("field_sources", []).append({"field_id": field_id, "source": source})


def _trace_fallback(state: dict, reason: str) -> None:
    trace = state.setdefault("debug_trace", {})
    trace.setdefault("fallbacks", []).append(reason)


def _trace_llm_debug(state: dict, key: str) -> None:
    info = llm.consume_debug_info()
    if info:
        state.setdefault("debug_trace", {})[key] = info


def _is_yes(text: str) -> bool:
    normalized = text.strip()
    reuse_hints = (
        "沿用",
        "用上次的",
        "沿用上次的",
        "沿用上次",
        "就用上次的",
        "就用上次",
        "用上次",
        "照上次",
        "跟上次一樣",
    )
    return (
        any(normalized == word or normalized.startswith(word) for word in CONFIRM_WORDS)
        or any(hint in normalized for hint in reuse_hints)
    ) and not _is_no(normalized)


def _is_no(text: str) -> bool:
    normalized = text.strip()
    return any(normalized == word or normalized.startswith(word) for word in DENY_WORDS)


def _judge_reply(question: str, text: str) -> str:
    verdict = llm.interpret_yes_no(question, text)
    if verdict in {"yes", "no"}:
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
        "quick_purchase": "快速下單",
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


def _display_field_value(field_id: str, value, fields: list[dict]) -> str:
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
    if field_id == "issue_photo" and isinstance(value, str) and value.startswith("data:image/"):
        value = "已上傳照片"
    unit = " 台" if field_id == "quantity" else " 個" if field_id == "antibacterial_film_quantity" else ""
    return f"{value}{unit}"


def _display_value(field_id: str, value, fields: list[dict]) -> str:
    return f"{_display_field_label(field_id, fields)}：{_display_field_value(field_id, value, fields)}"


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


# 只有這三項可以沿用上次，而且沿用時一律標註來源（見 _autofill_from_preferences）
# 或先問過使用者（pending_pref_question）。
REUSABLE_PREFERENCE_LABELS = (
    ("last_address", "常用地址"),
    ("last_phone", "常用電話"),
    ("preferred_time_slot", "偏好時間"),
)


def _reusable_preference_context(actor_id: str) -> str:
    """抽欄位時只給模型「可以沿用的偏好」，不給上一張單的內容。

    完整的長期記憶帶著 `上次摘要`，裡面是上一次每一格填了什麼（問題描述、日期、
    數量…）。模型看到那行就會照抄，於是使用者只說「幫我填」，問題描述卻冒出上次的
    文字——那是使用者這次沒說過的話。其他地方（服務判斷、回覆生成、記憶問答）仍用
    完整記憶，只有寫入表單這條路徑要收斂。
    """
    prefs = _safe_preferences(actor_id)
    lines = [
        f"{label}: {prefs[key]}"
        for key, label in REUSABLE_PREFERENCE_LABELS
        if prefs.get(key)
    ]
    return "\n".join(lines) if lines else "None"


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
    if any(hint in text for hint in ORDER_HISTORY_MEMORY_HINTS):
        return False

    hints = (
        "記得",
        "記住",
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
        today = clock.today()
        # 使用者講的是「這禮拜三」「明天」這種相對日期時，一律以規則解析為準。
        # 「某個日期是星期幾」對模型來說是很容易算錯的推理，但這裡是決定性的計算；
        # 之前直接採信模型回的 YYYY-MM-DD，就會填出對不上使用者當下星期幾的日期。
        if nlu.has_relative_date(original_text):
            parsed_from_text = nlu.parse_date(original_text, today=today)
            if parsed_from_text:
                return parsed_from_text

        if isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            try:
                normalized_date = date.fromisoformat(value)
                if normalized_date >= today:
                    return value
            except ValueError:
                pass
        return nlu.parse_date(str(value), today=today) or nlu.parse_date(original_text, today=today)

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
    long_term_context = _reusable_preference_context(actor_id)
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
    _trace_llm_debug(state, "llm_extract_fields_debug")

    found.update(_normalize_candidate_fields(state, llm_fields, text, found, source="llm_extract_fields"))

    heuristic_fields = nlu.extract_fields(
        state["service_id"],
        fields,
        text,
        state["collected_fields"] | found,
    )
    found.update(_normalize_candidate_fields(state, heuristic_fields, text, found, source="rule_extract_fields"))

    free_text_field = _capture_active_free_text_field(state, text, found)
    if free_text_field:
        field_id, value = free_text_field
        found[field_id] = value
        _trace_field_source(state, field_id, "free_text_capture")

    return found


def _normalize_candidate_fields(
    state: dict,
    raw_fields: dict,
    original_text: str,
    found: dict | None = None,
    *,
    source: str,
) -> dict:
    if not isinstance(raw_fields, dict):
        return {}

    fields = state["service_schema"]["fields"]
    normalized_found = dict(found or {})
    additions: dict = {}
    for field in fields:
        field_id = field["id"]
        if field_id in _LLM_EXCLUDED_FIELDS:
            continue
        if field_id in normalized_found or field_id not in raw_fields:
            continue
        if not _field_is_visible(field, state["collected_fields"] | normalized_found | additions):
            continue
        normalized = _normalize_field_value(field, raw_fields[field_id], original_text)
        if normalized is None:
            continue
        if source == "llm_extract_fields" and not _free_text_is_grounded(field_id, normalized, original_text):
            _trace_fallback(state, f"ungrounded_free_text:{field_id}")
            continue
        additions[field_id] = normalized
        _trace_field_source(state, field_id, source)
    return additions


def _free_text_is_grounded(field_id: str, value, original_text: str) -> bool:
    """自由文字欄位只能寫使用者這次說出口的內容。

    模型手上有偏好記憶與畫面草稿，遇到「幫我填」這種本身沒有描述內容的訊息時，
    容易生出一段問題描述（多半是抄記憶或草稿）。描述類欄位寧可留空、讓管家再問一次，
    也不要填一句使用者沒說過的話——那會直接被送進案件給廠商看。
    """
    if field_id not in FREE_TEXT_FIELD_IDS or not isinstance(value, str):
        return True
    return _GROUNDING_NOISE_RE.sub("", value) in _GROUNDING_NOISE_RE.sub("", original_text)


def _capture_active_free_text_field(state: dict, text: str, found: dict) -> tuple[str, str] | None:
    active_field_id = current_active_field(state)
    if not active_field_id or active_field_id in found:
        return None
    if active_field_id not in FREE_TEXT_FIELD_IDS:
        return None
    field = next((item for item in state["service_schema"]["fields"] if item["id"] == active_field_id), None)
    if not field or field.get("type") != "textarea":
        return None

    normalized = text.strip()
    if form_autopilot.looks_like_autofill_request(normalized):
        # 「幫我填」是指令不是描述：只剩指令就別填，夾帶內容時只取內容那一段。
        normalized = form_autopilot.strip_autofill_hints(normalized)
    if len(normalized) < 3:
        return None
    if _is_yes(normalized) or _is_no(normalized):
        return None
    if _looks_like_restart_service_request(normalized):
        return None
    if _should_prioritize_page_help(normalized):
        return None
    if _looks_like_memory_question(normalized):
        return None
    return active_field_id, normalized


def _prepend_reply(result: dict, prefix: str | None) -> dict:
    if prefix:
        base_reply = result.get("reply", "")
        result["reply"] = f"{prefix}\n{base_reply}" if base_reply else prefix
    return result


def _apply_found_fields_and_continue(
    actor_id: str,
    state: dict,
    text: str,
    events: list[dict] | None,
    found: dict,
    *,
    reply_prefix: str | None = None,
) -> dict:
    prohibited_reply = _hold_prohibited_item(state, found)
    if prohibited_reply:
        state["collected_fields"].update(found)
        _recompute_missing(state)
        return _prepend_reply(_reply(state, prohibited_reply), reply_prefix)

    state["collected_fields"].update(found)
    _recompute_missing(state)
    result = _continue_collection(actor_id, state, latest_user_message=text, events=events)
    return _prepend_reply(result, reply_prefix)


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
        _trace_fallback(state, f"model_reply:{phase}:llm_unavailable")
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
    _trace_llm_debug(state, "llm_compose_reply_debug")
    if reply:
        trace = state.setdefault("debug_trace", {})
        trace["model_reply_phase"] = phase
        trace["model_reply_source"] = "llm_compose_reply"
        return reply
    _trace_fallback(state, f"model_reply:{phase}:empty_reply")
    return _fallback_reply(state, phase, **kwargs)


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
        # 代操表單模式：使用者說「幫我填」之後，這一段會記住正在代操哪一張表單，
        # 之後同一張表單的每一句話都會繼續同步前端欄位（見 _plan_form_autopilot）。
        "form_autopilot": None,
        "short_term_memory": [],
        # health_product_recommendation is a one-shot query-and-answer service
        # (see catalog.py), not a form-and-submit one. It never sets request_id;
        # instead the agent answers directly and resets service_id back to None
        # while keeping this list around so a same-session follow-up naming one
        # of the recommended products can be answered with its nutrition info.
        "health_last_recommendations": [],
        "debug_trace": {},
        "is_multi_task": False,
        "pending_tasks": [],
        "awaiting_task_selection": False,
        "completed_task_summaries": [],
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


def _looks_like_restart_service_request(text: str) -> bool:
    return bool(
        re.search(r"(我要|我想|想要|需要|幫我|請幫我)", text)
        and re.search(r"(服務|預約|申請|安排|清洗|清潔|維修|修繕|訂位|外送|叫修)", text)
    )


def _explicit_service_request_id(text: str, services: list[dict]) -> str | None:
    scores: list[tuple[int, str]] = []
    for service in services:
        score = 0
        keywords = list(service.get("keywords", []))
        full_service = catalog.get_service(service["id"]) or {}
        keywords.extend(full_service.get("keywords", []))
        name = str(service.get("name") or full_service.get("name") or "")
        description = str(service.get("description") or full_service.get("description") or "")
        keywords.extend(part for part in re.split(r"[、，。\s與和]+", description) if len(part) >= 2)

        for keyword in keywords:
            if keyword and keyword in text:
                score += len(keyword)
        if name and name in text:
            score += len(name) + 2
        if score:
            scores.append((score, service["id"]))
    scores.sort(reverse=True)
    return scores[0][1] if scores else None


def _looks_like_other_service_request(text: str, service_id: str) -> bool:
    """這句話聽起來是在講「另一種服務」嗎？

    代操表單時用來擋掉誤判：使用者站在冷氣表單頁卻說「我要預約居家清潔」，
    不該被當成冷氣表單的欄位內容。
    """
    if not _looks_like_new_service_request(text):
        return False
    keywords_by_service = dict(RULE_SERVICE_KEYWORDS)
    if any(keyword in text for keyword in keywords_by_service.get(service_id, ())):
        return False
    return any(
        any(keyword in text for keyword in keywords)
        for other_service_id, keywords in RULE_SERVICE_KEYWORDS
        if other_service_id != service_id
    )


_PAGE_ID_REDIRECT_ROUTES = {
    "service_form_shop_purchase": "/services/shop_purchase",
}


def _fallback_page_help_reply(
    text: str,
    current_page_id: str | None,
    auth_token: str | None,
) -> tuple[str | None, str | None]:
    if not looks_like_page_question(text, current_page_id=current_page_id):
        return None, None
    return _page_help_reply(text, current_page_id=current_page_id, auth_token=auth_token)


def _should_prioritize_page_help(text: str, current_page_id: str | None = None) -> bool:
    return looks_like_page_question(text, current_page_id=current_page_id) and (
        is_navigation_query(text) or "哪裡訂" in text or "去哪裡訂" in text
    )


def _page_help_reply(
    text: str, current_page_id: str | None, auth_token: str | None
) -> tuple[str | None, str | None]:
    """回覆頁面問答，並在問到「有專屬導頁路由」的頁面（目前只有商城購物）時
    一併回傳 redirect_path，讓聊天面板直接帶使用者過去，而不是只用文字說明。
    其他服務走一般表單填寫流程，沒有對應的專屬路由，所以維持原本純問答行為。
    """
    if is_voice_filling_question(text):
        return answer_page_question(text, current_page_id=current_page_id), None

    tool_request = build_page_tool_request(text, current_page_id=current_page_id)
    tool_payload: dict | None = None

    if tool_request:
        tool_name, params = tool_request
        result = tools.call(tool_name, params, auth_token=auth_token)
        if result.get("success"):
            tool_payload = result

    resolved_page_id: str | None = None
    if isinstance(tool_payload, dict):
        page = tool_payload.get("page")
        if isinstance(page, dict):
            resolved_page_id = page.get("page_id")
        else:
            matches = tool_payload.get("matches")
            if isinstance(matches, list) and matches and isinstance(matches[0], dict):
                resolved_page_id = matches[0].get("page_id")
    redirect_path = _PAGE_ID_REDIRECT_ROUTES.get(resolved_page_id or "")

    if tool_payload and llm.is_available():
        llm_reply = llm.compose_page_help_reply(
            latest_user_message=text,
            current_page_id=current_page_id or "",
            tool_payload=tool_payload,
        )
        if llm_reply:
            return llm_reply, redirect_path

    return answer_page_question(text, current_page_id=current_page_id, tool_payload=tool_payload), redirect_path


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


def _answer_price_compare(query: str, auth_token: str | None) -> tuple[str, str | None]:
    result = tools.call("compare_product_prices", {"query": query}, auth_token=auth_token)
    if not result.get("success"):
        message = result.get("error", {}).get("message", "查詢失敗")
        return f"抱歉，這次比價沒有成功，原因是：{message}。你可以換個商品名稱再試一次。", None

    offers = result.get("offers") or []
    lines = [f"「{result.get('product_name', '')}」目前各店家的點數兌換價格："]
    for index, offer in enumerate(offers, start=1):
        lines.append(f"{index}. {offer.get('store_name', '')}：{offer.get('unit_price', '')} 元")
    if offers:
        lines.append(f"目前最便宜的是 {offers[0].get('store_name', '')}。")
    lines.append("我幫你導到商城購物頁面，可以直接看到完整比價和下單。")
    reply = "\n".join(lines)
    redirect_path = f"/services/shop_purchase?compare={result['group_id']}"
    return reply, redirect_path


def _handle_one_shot_service(
    service_id: str, state: dict, text: str, auth_token: str | None
) -> dict | None:
    """一次性問答／導頁服務的共用邏輯。

    health_product_recommendation / shop_purchase / shop_price_compare 都沒有表單欄位收集
    流程：前兩者是直接回答的 query-and-answer 服務，shop_purchase 則是導頁到專屬頁面。
    這三種在單一服務流程與多任務佇列（_start_next_multi_task）都要套用同一套特例，
    避免多任務佇列把它們誤導進通用的欄位收集流程（進而可能呼叫通用的
    submit_service_request 建立一筆不該存在的案件）。

    呼叫前提：state["service_id"] / state["service_schema"] 已經是這個 service_id 的資料。
    若 service_id 屬於這三種特殊服務，回傳完整的回覆 dict 並清空 state 的服務欄位；
    否則回傳 None，讓呼叫端繼續走一般表單收集流程。
    """
    if service_id == "health_product_recommendation":
        # The message that triggered detection is itself the health/diet
        # query (single-field, no form to fill) — answer immediately
        # instead of falling through to the generic field-collection flow.
        reply = _answer_health_recommendation(state, text, auth_token)
        state["service_id"] = None
        state["service_name"] = None
        state["service_schema"] = None
        state["collected_fields"] = {}
        state["missing_fields"] = []
        return _reply(state, reply)

    if service_id == "shop_purchase":
        # shop_purchase is a dedicated multi-step flow (store -> product/spec
        # -> cart -> checkout/points) built for the ShopFlowPage UI, not
        # conversational field collection — redirect instead of collecting fields.
        state["service_id"] = None
        state["service_name"] = None
        state["service_schema"] = None
        state["collected_fields"] = {}
        state["missing_fields"] = []
        return _reply(
            state,
            "商城購物需要挑選商品類型、規格和購物車，這部分請到「商城購物」頁面操作會更方便，我幫你導過去囉！",
            redirect_path="/services/shop_purchase",
        )

    if service_id == "shop_price_compare":
        # One-shot query-and-answer service (like health_product_recommendation):
        # answer directly with a price summary instead of collecting form fields.
        reply, redirect_path = _answer_price_compare(text, auth_token)
        state["service_id"] = None
        state["service_name"] = None
        state["service_schema"] = None
        state["collected_fields"] = {}
        state["missing_fields"] = []
        return _reply(
            state,
            reply,
            redirect_path=redirect_path,
            redirect_requires_confirmation=redirect_path is not None,
        )

    return None


def _reset_conversation_state(state: dict) -> None:
    """清空這段對話收到的資料，只留下短期對話記憶。"""
    short_term_memory = state.get("short_term_memory") or []
    state.clear()
    state.update(new_state())
    state["short_term_memory"] = short_term_memory


def _reset_state_for_service(state: dict, service_id: str, schema: dict) -> None:
    """把 session 換成另一張表單，只留下短期對話記憶。"""
    _reset_conversation_state(state)
    state["service_id"] = service_id
    state["service_name"] = _display_service_name(service_id, schema.get("title"))
    state["service_schema"] = {"fields": schema["fields"]}


def _seed_from_form_values(state: dict, form_values: dict) -> None:
    """把前端表單目前的內容同步進 collected_fields，畫面是唯一真相。

    使用者可能手動先填了幾格、也可能在代操後又自己改過或清空，Agent 要以畫面上的值為準，
    才不會重複問已經填好的欄位、或把使用者清掉的值當成還在（那會讓 Agent 以為表單填完了，
    送出時卻缺欄位）。

    前端會把「這張表單認得的每一格」都放進 form_values（空的就送空字串），只有照片
    （data URL）和過長的值會被略過——那些 key 不會出現，代表「不要動這一格」。
    """
    fields = (state.get("service_schema") or {}).get("fields") or []
    for field in fields:
        field_id = field["id"]
        if field_id not in form_values:
            continue
        raw_value = form_values[field_id]
        if raw_value is None or not str(raw_value).strip():
            state["collected_fields"].pop(field_id, None)
            continue
        normalized = _normalize_field_value(field, raw_value, str(raw_value))
        if normalized is None:
            continue
        state["collected_fields"][field_id] = normalized


def _hold_prohibited_item(state: dict, found: dict) -> str | None:
    """寄件內容物疑似違禁品時扣住這個值，並回傳要先問使用者的話。

    代填與畫面同步都要經過這一關：`shipping._validate_payload` 需要
    `prohibited_item_ack`，少了這關就會出現「表單看起來填完了、送出卻永遠失敗」。
    """
    if state.get("service_id") != "package_shipping":
        return None
    if state.get("prohibited_item_acknowledged"):
        return None

    description = found.get("item_description") or (state.get("collected_fields") or {}).get(
        "item_description"
    )
    if not description:
        return None
    matched = shipping.contains_prohibited_keywords(description)
    if not matched:
        return None

    found.pop("item_description", None)
    state["collected_fields"].pop("item_description", None)
    if state.get("pending_prohibited_item"):
        # 已經問過、正在等回覆，不重複發問。
        return None

    state["pending_prohibited_item"] = description
    categories = "、".join(matched)
    return (
        f"你提到的內容物可能屬於「{categories}」類別，這類物品寄送有限制。"
        "請問已詳讀寄送規範，確認可以寄送嗎？如果不確定，也可以直接重新描述內容物。"
    )


def _time_option_values(field: dict) -> list[str]:
    """表單時間下拉選單真的有的選項（和前端 buildTimeOptions 同一套規則）。"""

    def minutes_of(value: str) -> int | None:
        try:
            hours, minutes = (int(part) for part in value.split(":"))
        except (ValueError, AttributeError):
            return None
        return hours * 60 + minutes

    start = minutes_of(field.get("minValue") or "00:00")
    end = minutes_of(field.get("maxValue") or "23:55")
    step = max(int(field.get("step") or 300) // 60, 1)
    if start is None or end is None or start > end:
        return []
    return [f"{value // 60:02d}:{value % 60:02d}" for value in range(start, end + 1, step)]


def _snap_values_to_form_options(state: dict) -> None:
    """把時間對齊表單下拉選單真的有的那一格。

    LLM 可能回 14:03，後端只檢查營業時間範圍所以會收下，但畫面上的時間是每 5 分鐘一格的
    下拉選單，沒有 14:03 這個選項——代填就會變成「說有填、其實那格還是空的」。這裡先對齊到
    選單有的時間（往前取），Agent 認知與畫面才會一致。
    """
    fields = (state.get("service_schema") or {}).get("fields") or []
    collected = state.get("collected_fields") or {}
    for field in fields:
        if field.get("type") != "time":
            continue
        value = collected.get(field["id"])
        if not isinstance(value, str) or not value:
            continue
        options = _time_option_values(field)
        if not options or value in options:
            continue
        earlier = [option for option in options if option <= value]
        if earlier:
            collected[field["id"]] = earlier[-1]
        else:
            collected.pop(field["id"], None)


def _autofill_from_preferences(actor_id: str, state: dict) -> dict:
    """代操模式直接沿用上次的地址／電話／時間，不像對話流程那樣一項一項先問。

    回傳 {field_id: 說明文字}，讓前端在該欄位旁標註資料來源。
    """
    prefs = _safe_preferences(actor_id)
    fields = (state.get("service_schema") or {}).get("fields") or []
    field_map = {field["id"]: field for field in fields}
    asked = state.setdefault("asked_pref_fields", [])
    notes: dict[str, str] = {}

    for field_id, pref_key in (
        ("address", "last_address"),
        ("phone", "last_phone"),
        ("preferred_time_slot", "preferred_time_slot"),
    ):
        if field_id not in state["missing_fields"]:
            continue
        raw_value = prefs.get(pref_key)
        field = field_map.get(field_id)
        if not raw_value or not field:
            continue
        if field_id == "preferred_time_slot":
            raw_value = _normalize_saved_time_value(str(raw_value))
        normalized = _normalize_field_value(field, raw_value, "")
        if normalized is None:
            continue
        state["collected_fields"][field_id] = normalized
        # 標記成「已經問過」，避免之後的對話流程又問一次「要沿用上次的嗎」。
        if field_id not in asked:
            asked.append(field_id)
        notes[field_id] = "沿用你上次填的資料"

    return notes


def _detect_autopilot_service(
    actor_id: str,
    state: dict,
    text: str,
    events: list[dict] | None,
    auth_token: str | None,
) -> str | None:
    """這句話指的是哪一張服務表單？

    先用頁面知識庫的別名比對（`search_pages` 認得「冷氣」「洗衣機」「包裹」這種說法，
    而且是加權比分，不會像 RULE_SERVICE_KEYWORDS 那樣被「清洗」這種共用字先搶走），
    比不到才退回一般的服務判斷。

    回傳的服務不保證能代填（可能是有專屬流程頁的服務），由呼叫端決定怎麼處理。
    """
    for match in search_pages(text):
        service_id = form_autopilot.page_service_id(match.get("page_id"))
        if service_id:
            return service_id

    services = _available_services(auth_token)
    if not services:
        return None
    return _detect_service(
        text,
        services,
        _short_term_context(state, events, text),
        _long_term_memory_context(actor_id, text),
    )


def _autofill_service_options(auth_token: str | None) -> list[str]:
    """可以代填的服務名稱，用在「你要填哪一種」的回問。"""
    services = _available_services(auth_token) or []
    return [
        service["name"]
        for service in services
        if form_autopilot.supports_autopilot(service.get("id"))
    ]


def _can_adopt_form_page(
    text: str,
    form_context: dict | None,
    current_page_id: str | None,
) -> bool:
    """使用者沒說「幫我填」，但這一句仍然應該當成在改這張表單嗎？

    對話 session 會在重新整理後重來一次，這時使用者常常直接接著說「時間改成下午三點」。
    畫面上表單已經有資料、這句話又不是在問問題時，就把這張表單接手過來繼續收單，
    避免掉回「我目前只支援這幾種服務」。接手不等於代填——是否主動幫忙補資料由
    `entering` 決定（見 `_plan_form_autopilot`）。

    問句一律不接手：「冷氣清洗多少錢？」是在問事情，不是在給欄位值。
    """
    values = (form_context or {}).get("values") or {}
    if not any(str(value).strip() for value in values.values()):
        return False
    if form_autopilot.looks_like_question(text):
        return False
    return not looks_like_page_question(text, current_page_id=current_page_id)


def _switch_target_service(
    actor_id: str,
    state: dict,
    text: str,
    current_service_id: str,
    events: list[dict] | None,
    auth_token: str | None,
) -> str | None:
    """這句話是不是在改口要「另一張表單」？是的話回傳新的 service_id。

    先用便宜的關鍵字預篩（避免每句話都跑一次服務判斷），真的像在講別的服務時才確認一次。
    只有確認到「不同且可代操」的服務才算數，否則維持目前這張表單——否則像包裹寄送頁回答
    「我需要到府收件」這種正常答案（「到府」剛好是居家清潔的關鍵字）就會被誤判成換服務。
    """
    if not _looks_like_other_service_request(text, current_service_id):
        return None
    detected = _detect_autopilot_service(actor_id, state, text, events, auth_token)
    return detected if detected and detected != current_service_id else None


def _plan_form_autopilot(
    actor_id: str,
    state: dict,
    text: str,
    current_page_id: str | None,
    form_context: dict | None,
    events: list[dict] | None,
    auth_token: str | None,
) -> dict | None:
    """決定這一輪要不要代操表單，並先把 Agent 狀態和畫面上的表單對齊。

    回傳 None 代表這一輪走原本的對話流程（頁面問答、一般收單…）。
    """
    if is_voice_filling_question(text) and form_autopilot.looks_like_question(text):
        # 「可以用語音幫我填嗎」問的是功能，交給頁面問答回答。
        # 但「我用說的，幫我填兩台壁掛式冷氣」是要現在填，不能因為提到語音就擋掉。
        return None

    wants_autofill = form_autopilot.looks_like_autofill_request(text)

    if state.get("request_id"):
        # 這段對話已經送出過案件。使用者明講「幫我填」代表要開新的一張單，
        # 就從乾淨的狀態重來——不然會掉回頁面問答，變成只告訴他「表單在哪裡」。
        if not wants_autofill:
            return None
        _reset_conversation_state(state)

    context_service_id = (form_context or {}).get("service_id") or None
    form_service_id = context_service_id or form_autopilot.page_service_id(current_page_id)
    if not form_autopilot.supports_autopilot(form_service_id):
        form_service_id = None

    active_service_id = (state.get("form_autopilot") or {}).get("service_id")

    if form_service_id:
        # 已經站在表單頁：明講「幫我填」才會主動代填；沒明講但畫面上已經有資料時，
        # 仍然把這張表單接手過來繼續收單（重新打開管家或重整後接得下去），只是不會
        # 主動幫忙補偏好資料。
        if not wants_autofill and active_service_id != form_service_id:
            if not _can_adopt_form_page(text, form_context, current_page_id):
                return None
        target_service_id = form_service_id
    elif wants_autofill:
        target_service_id = active_service_id or ""
    else:
        # 人已經不在那張表單頁上（換頁、回首頁…）：結束代操，之後的對話不再驅動畫面。
        # 已經收到的資料留著，使用者可以繼續用對話把案件講完。
        state["form_autopilot"] = None
        return None

    # 改口要別的服務（「算了，我要預約居家清潔」／站在 A 表單頁說「幫我填冷氣清洗」）：
    # 換成那張表單並導頁過去，而不是把新需求硬塞進眼前這張表單。
    switched_service_id = (
        _switch_target_service(actor_id, state, text, target_service_id, events, auth_token)
        if target_service_id
        else None
    )
    if not target_service_id or switched_service_id:
        target_service_id = switched_service_id or _detect_autopilot_service(
            actor_id, state, text, events, auth_token
        )
        if not target_service_id:
            # 聽得出要代填、但聽不出是哪一種服務：直接問他要哪一種，
            # 不要回一段「表單在那邊」的頁面說明打發他。
            options = _autofill_service_options(auth_token)
            if not options:
                return None
            return {
                "service_id": None,
                "redirect_path": None,
                "clarify_reply": (
                    f"好，我可以直接幫你把表單填好。目前可以代填的服務有：{'、'.join(options)}。"
                    "請問你要申請哪一種？也可以直接把需求說完，例如「幫我填冷氣清洗，兩台壁掛式，明天下午三點」。"
                ),
                "entering": False,
            }

    if not form_autopilot.supports_autopilot(target_service_id):
        # 餐廳訂位、美食外送、商城購物、健康推薦在前端是專屬流程頁（挑店家、購物車…），
        # 沒有可以逐格代填的欄位。帶他過去並用對話接手，一樣不要只丟一句頁面說明。
        service_name = _display_service_name(target_service_id)
        return {
            "service_id": target_service_id,
            "redirect_path": f"/services/{target_service_id}",
            "clarify_reply": (
                f"「{service_name}」需要挑選店家與品項，不是一張可以直接代填的表單，"
                "我先帶你到那一頁，接著用對話一步一步幫你完成。"
            ),
            "entering": False,
        }

    redirect_path = None if target_service_id == form_service_id else f"/services/{target_service_id}"

    if state.get("service_id") != target_service_id or not state.get("service_schema"):
        schema = _service_schema(target_service_id, auth_token)
        if not schema:
            return None
        _reset_state_for_service(state, target_service_id, schema)

    state["form_autopilot"] = {"service_id": target_service_id, "notes": {}}
    prohibited_reply = None
    if target_service_id == form_service_id:
        _seed_from_form_values(state, (form_context or {}).get("values") or {})
        # 畫面上打的內容物同樣要過違禁品這一關，不能因為是「同步進來的」就跳過。
        prohibited_reply = _hold_prohibited_item(state, {})
    _snap_values_to_form_options(state)
    _recompute_missing(state)

    return {
        "service_id": target_service_id,
        "redirect_path": redirect_path,
        "prohibited_reply": prohibited_reply,
        # 只有明講「幫我填」才跑代填流程（自動帶入偏好、逐格寫入）；其餘情況維持
        # 原本一次問一格的對話流程，只是欄位變動一樣會同步到畫面上。
        "entering": wants_autofill,
    }


def _run_form_autopilot(
    actor_id: str,
    state: dict,
    text: str,
    plan: dict,
    before: dict,
    events: list[dict] | None,
) -> dict:
    """「幫我填」這一輪：把訊息裡的資料和使用者偏好一次補進表單。"""
    fields = state["service_schema"]["fields"]

    found = _extract_fields(actor_id, state, text, events)
    held_reply = _hold_prohibited_item(state, found)
    state["collected_fields"].update(found)
    _snap_values_to_form_options(state)
    _recompute_missing(state)

    if held_reply:
        # 寄件內容物疑似違禁品：先確認過才繼續，不能默默代填送出。
        return _reply(state, held_reply, redirect_path=plan.get("redirect_path"))

    notes = _autofill_from_preferences(actor_id, state)
    _snap_values_to_form_options(state)
    _recompute_missing(state)
    state["form_autopilot"]["notes"] = notes

    missing_label = ""
    missing_question = ""
    if state["missing_fields"]:
        state["status"] = "COLLECTING_INFORMATION"
        state["awaiting_confirmation"] = False
        next_field = next(field for field in fields if field["id"] == state["missing_fields"][0])
        missing_label = _display_field_label(next_field["id"], fields)
        missing_question = _build_field_question(next_field)
    else:
        state["status"] = "AWAITING_USER_CONFIRMATION"
        state["awaiting_confirmation"] = True

    # 回覆文案要和畫面上正在跑的動作完全一致，所以用同一份 before/after 差異算動作清單。
    actions = _build_form_actions(state, before)
    reply = form_autopilot.compose_reply(
        service_title=_display_service_name(state["service_id"], state["service_name"]),
        actions=actions,
        missing_label=missing_label,
        missing_question=missing_question,
        redirecting=bool(plan.get("redirect_path")),
    )
    return _reply(state, reply, redirect_path=plan.get("redirect_path"))


def _build_form_actions(state: dict, before: dict) -> list[dict]:
    autopilot = state.get("form_autopilot") or {}
    schema = state.get("service_schema")
    if not autopilot or not schema or state.get("service_id") != autopilot.get("service_id"):
        return []

    fields = schema["fields"]
    collected = state.get("collected_fields") or {}
    return form_autopilot.build_actions(
        fields,
        before,
        collected,
        label_of=lambda field_id: _display_field_label(field_id, fields),
        display_of=lambda field_id, value: _display_field_value(field_id, value, fields),
        is_visible=lambda field: _field_is_visible(field, collected),
        notes=autopilot.get("notes") or {},
    )




def handle_message(
    actor_id: str,
    session_id: str,
    state: dict,
    message: str,
    events: list[dict] | None = None,
    current_page_id: str | None = None,
    auth_token: str | None = None,
    form_context: dict | None = None,
) -> dict:
    """對話入口。

    代操表單模式下，這一輪造成的 collected_fields 變動會一併轉成 form_actions，
    由前端逐格高亮填進畫面上的表單。
    """
    text = message.strip()
    plan = _plan_form_autopilot(actor_id, state, text, current_page_id, form_context, events, auth_token)

    # before 一定要在「同步前端表單值」之後才拍快照：使用者自己打的字已經在畫面上了，
    # 不該再被當成 AI 的動作回填一次。
    before = dict(state.get("collected_fields") or {})

    if plan and plan.get("clarify_reply"):
        result = _reply(state, plan["clarify_reply"], redirect_path=plan.get("redirect_path"))
    elif plan and plan.get("prohibited_reply"):
        result = _reply(state, plan["prohibited_reply"], redirect_path=plan.get("redirect_path"))
    elif plan and plan["entering"]:
        result = _run_form_autopilot(actor_id, state, text, plan, before, events)
    else:
        result = _dispatch_message(
            actor_id,
            session_id,
            state,
            message,
            events,
            current_page_id=current_page_id,
            auth_token=auth_token,
        )

    if plan and plan.get("redirect_path") and not result.get("redirect_path"):
        # 換到另一張表單時，不管這一輪是代填還是一般收單，都要把使用者帶過去。
        result["redirect_path"] = plan["redirect_path"]

    # 沒有 plan 代表這一輪不是在操作畫面上的表單（人已經離開表單頁、或這句話走的是頁面問答），
    # 這時就算 collected_fields 有變動也不該回動作，否則前端會莫名關掉面板等一張不存在的表單。
    result["form_actions"] = _build_form_actions(result["state"], before) if plan else []
    return result



def _dispatch_message(
    actor_id: str,
    session_id: str,
    state: dict,
    message: str,
    events: list[dict] | None = None,
    current_page_id: str | None = None,
    auth_token: str | None = None,
) -> dict:
    text = message.strip()
    _reset_debug_trace(state, text)

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
                page_reply, page_redirect_path = _fallback_page_help_reply(
                    text,
                    current_page_id=current_page_id,
                    auth_token=auth_token,
                )
                if page_reply:
                    return _reply(state, page_reply, redirect_path=page_redirect_path)
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
            page_reply, page_redirect_path = _fallback_page_help_reply(
                text,
                current_page_id=current_page_id,
                auth_token=auth_token,
            )
            if page_reply:
                return _reply(state, page_reply, redirect_path=page_redirect_path)
            return _reply(state, _model_reply(actor_id, state, "completed", latest_user_message=text))

    if (
        state.get("service_id")
        and not state.get("is_multi_task")
        and _looks_like_restart_service_request(text)
    ):
        # During a multi-task queue the active task always has service_id set, so this
        # trigger must not fire there — it would silently wipe pending_tasks and
        # completed_task_summaries with zero acknowledgement to the user. Let the
        # message fall through to normal field extraction for the active task instead.
        services = _available_services(auth_token)
        if services is not None:
            restarted_service_id = _explicit_service_request_id(text, services)
            if restarted_service_id:
                state = new_state()

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
            found = _extract_fields(actor_id, state, text, events)
            if verdict == "unclear" and not found:
                return _reply(state, question)
            state["collected_fields"].update(found)
        state["pending_pref_field"] = None
        state["pending_pref_value"] = None
        state["pending_pref_question"] = None
        _recompute_missing(state)
        return _continue_collection(actor_id, state, latest_user_message=text, events=events)

    if state.get("awaiting_task_selection"):
        return _handle_task_selection_reply(actor_id, state, text, auth_token)

    if state["awaiting_confirmation"]:
        _recompute_missing(state)
        if state["missing_fields"]:
            state["awaiting_confirmation"] = False
            state["status"] = "COLLECTING_INFORMATION"
            return _continue_collection(actor_id, state, latest_user_message=text, events=events)

        verdict = _judge_reply("請確認以上內容是否正確，若正確請回覆確認送出。", text)
        if verdict == "yes":
            return _submit_and_continue_multi_task(actor_id, session_id, state, text, auth_token)

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
        if state.get("health_last_recommendations"):
            health_followup_reply = _handle_health_followup(state, text, auth_token)
            if health_followup_reply:
                return _reply(state, health_followup_reply)

        short_term_context = _short_term_context(state, events, text)
        long_term_context = _long_term_memory_context(actor_id, text)
        services = _available_services(auth_token) or []
        planned_service_id: str | None = None

        if llm.is_available():
            turn_plan = llm.plan_turn(
                message=text,
                services=services,
                current_page_id=current_page_id or "",
                short_term_memory=short_term_context,
                long_term_memory=long_term_context,
            )
            _trace_llm_debug(state, "turn_router_debug")
            if turn_plan:
                state["debug_trace"]["turn_router"] = turn_plan
                if turn_plan["mode"] == "chat" and turn_plan.get("reply"):
                    return _reply(state, turn_plan["reply"])
                if turn_plan["mode"] == "memory_query":
                    memory_reply = _reply_from_memory(actor_id)
                    if memory_reply:
                        return _reply(state, memory_reply)
                    if turn_plan.get("reply"):
                        return _reply(state, turn_plan["reply"])
                if turn_plan["mode"] == "page_help":
                    page_reply, page_redirect_path = _fallback_page_help_reply(
                        text,
                        current_page_id=current_page_id,
                        auth_token=auth_token,
                    )
                    if page_reply:
                        return _reply(state, page_reply, redirect_path=page_redirect_path)
                    if turn_plan.get("reply"):
                        return _reply(state, turn_plan["reply"])
                if turn_plan["mode"] == "service_request":
                    planned_service_id = turn_plan.get("service_id")
                if turn_plan["mode"] == "multi_task":
                    tasks = llm.plan_multi_task(
                        message=text,
                        services=services,
                        short_term_memory=short_term_context,
                        long_term_memory=long_term_context,
                    )
                    if len(tasks) >= 2:
                        state["is_multi_task"] = True
                        state["pending_tasks"] = list(tasks)
                        state["awaiting_task_selection"] = True
                        # Reset so a second multi-task run in the same session doesn't
                        # append onto a previous run's already-completed summaries.
                        state["completed_task_summaries"] = []
                        name_by_id = {service["id"]: service.get("name") for service in services}
                        names = "、".join(
                            _display_service_name(t["service_id"], name_by_id.get(t["service_id"]))
                            for t in tasks
                        )
                        reply = f"收到！我幫您整理了 {len(tasks)} 個任務：{names}。請問要全部進行，還是先從哪幾項開始呢？"
                        return _reply(state, reply, task_cards=_task_cards(tasks, services))
                    # Fewer than 2 real tasks resolved — fall through to normal single-service handling below.
            else:
                _trace_fallback(state, "turn_router:no_plan")

        if _should_prioritize_page_help(text, current_page_id=current_page_id):
            page_reply, page_redirect_path = _fallback_page_help_reply(
                text,
                current_page_id=current_page_id,
                auth_token=auth_token,
            )
            if page_reply:
                return _reply(state, page_reply, redirect_path=page_redirect_path)

        if not planned_service_id and _looks_like_memory_question(text):
            memory_reply = _reply_from_memory(actor_id)
            if memory_reply:
                state["debug_trace"]["turn_router"] = {"mode": "memory_query", "source": "rule_memory_question"}
                return _reply(state, memory_reply)

        if not services:
            return _reply(state, _model_reply(actor_id, state, "service_catalog_error", latest_user_message=text))

        service_id = planned_service_id or _detect_service(text, services, short_term_context, long_term_context)
        if not service_id:
            _trace_fallback(state, "service_detection:unresolved")
            page_reply, page_redirect_path = _fallback_page_help_reply(
                text,
                current_page_id=current_page_id,
                auth_token=auth_token,
            )
            if page_reply:
                return _reply(state, page_reply, redirect_path=page_redirect_path)
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

        one_shot_result = _handle_one_shot_service(service_id, state, text, auth_token)
        if one_shot_result is not None:
            return one_shot_result

    if llm.is_available():
        active_field = current_active_field(state) or ""
        form_plan = llm.plan_form_turn(
            message=text,
            service_name=_display_service_name(state["service_id"], state["service_name"]),
            fields=state["service_schema"]["fields"],
            collected_fields=state["collected_fields"],
            form_schema=build_form_schema(state),
            form_draft=build_form_draft(state),
            active_field=active_field,
            short_term_memory=_short_term_context(state, events, text),
            long_term_memory=_long_term_memory_context(actor_id, text),
        )
        _trace_llm_debug(state, "form_router_debug")
        if form_plan:
            state["debug_trace"]["form_router"] = form_plan
            planned_found = _normalize_candidate_fields(
                state,
                form_plan.get("fields", {}),
                text,
                source="llm_form_turn",
            )
            if planned_found:
                return _apply_found_fields_and_continue(
                    actor_id,
                    state,
                    text,
                    events,
                    planned_found,
                    reply_prefix=form_plan.get("reply"),
                )
            if form_plan.get("mode") == "reply" and form_plan.get("reply"):
                return _reply(state, form_plan["reply"])
        else:
            _trace_fallback(state, "form_router:no_plan")

    found = _extract_fields(actor_id, state, text, events)
    if not found:
        _trace_fallback(state, "field_extraction:empty")
    return _apply_found_fields_and_continue(actor_id, state, text, events, found)


def _continue_collection(actor_id: str, state: dict, latest_user_message: str = "", events: list[dict] | None = None) -> dict:
    if state.get("service_id") == "food_delivery":
        return _continue_delivery_collection(actor_id, state, latest_user_message, events)
    return _continue_generic_collection(actor_id, state, latest_user_message, events)


def _task_cards(tasks: list[dict], services: list[dict]) -> list[dict]:
    name_by_id = {service["id"]: service.get("name") for service in services}
    return [
        {
            "service_id": task["service_id"],
            "service_name": _display_service_name(task["service_id"], name_by_id.get(task["service_id"])),
        }
        for task in tasks
    ]


_CN_ORDINAL_DIGITS = {"一": 1, "二": 2, "兩": 2, "三": 3, "四": 4, "五": 5,
                      "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
_ORDINAL_COUNT_RE = re.compile(r"(?:前|第)\s*([一二三四五六七八九十兩\d]+)\s*(?:個|項)?")


def _parse_ordinal_count(text: str) -> int | None:
    """解析「前兩個」「前二」「先做第一個」這類序數式回覆，回傳要選取的任務數量。
    只支援 1-10 的常見中文數字，不做完整 NLP（見設計備註）。"""
    match = _ORDINAL_COUNT_RE.search(text)
    if not match:
        return None
    token = match.group(1)
    if token.isdigit():
        value = int(token)
    else:
        value = _CN_ORDINAL_DIGITS.get(token)
    return value if value and value > 0 else None


def _select_multi_tasks(text: str, pending_tasks: list[dict], services: list[dict]) -> dict:
    """回傳 {"action": "run", "tasks": [...]} | {"action": "cancel"} | {"action": "unclear"}。

    先前的版本在完全無法辨識回覆時一律 fallback 成「全部執行」，導致「不要」「算了」
    這類明確的取消回覆、或是「先做前兩個」這類序數式回覆都被誤判成全選。這裡改成：
    明確拒絕 → cancel；序數式回覆 → 依數量取前 N 個；其餘無法辨識 → unclear（讓呼叫端
    重新詢問一次，而不是用猜的）。
    """
    if _is_no(text) or "算了" in text:
        return {"action": "cancel"}

    if _is_yes(text) or any(word in text for word in ("全部", "都要", "都做", "全都要")):
        return {"action": "run", "tasks": list(pending_tasks)}

    name_by_id = {service["id"]: service.get("name", "") for service in services}
    selected = [
        task
        for task in pending_tasks
        if name_by_id.get(task["service_id"]) and name_by_id[task["service_id"]] in text
    ]
    if selected:
        return {"action": "run", "tasks": selected}

    count = _parse_ordinal_count(text)
    if count is not None:
        return {"action": "run", "tasks": list(pending_tasks[:count])}

    return {"action": "unclear"}


def _start_next_multi_task(
    actor_id: str,
    state: dict,
    auth_token: str | None,
    transition_prefix: str | None = None,
) -> dict:
    if not state["pending_tasks"]:
        summary = "\n".join(state["completed_task_summaries"])
        state["is_multi_task"] = False
        reply = f"任務都完成了！\n{summary}" if summary else "目前沒有任務可以彙總。"
        result = _reply(state, reply, share_text=summary or None)
        return _prepend_reply(result, transition_prefix) if transition_prefix else result

    task = state["pending_tasks"].pop(0)
    schema_result = _service_schema(task["service_id"], auth_token)
    if not schema_result:
        # Broken/unavailable service schema — skip this task and try the next one.
        return _start_next_multi_task(actor_id, state, auth_token, transition_prefix)

    services = _available_services(auth_token) or []
    service = next((item for item in services if item["id"] == task["service_id"]), None)
    state["service_id"] = task["service_id"]
    state["service_name"] = _display_service_name(
        task["service_id"], (service or {}).get("name") or schema_result.get("title")
    )
    state["service_schema"] = {"fields": schema_result["fields"]}
    state["collected_fields"] = {}
    _recompute_missing(state)

    hint_fields = task.get("hint_fields") or {}
    if hint_fields:
        normalized_hints = _normalize_candidate_fields(state, hint_fields, "", source="multi_task_hint")
        state["collected_fields"].update(normalized_hints)
        _recompute_missing(state)

    # health_product_recommendation / shop_purchase / shop_price_compare are one-shot
    # query-and-answer or redirect services with no form to fill — reuse the same
    # special-casing the single-service path applies right after schema load, so the
    # queue never drives them through generic field collection (which could otherwise
    # create a bogus request via the generic submit_service_request tool call).
    one_shot_query = str(state["collected_fields"].get("query") or hint_fields.get("query") or "")
    one_shot_result = _handle_one_shot_service(task["service_id"], state, one_shot_query, auth_token)
    if one_shot_result is not None:
        completed_name = _display_service_name(task["service_id"], (service or {}).get("name"))
        state["completed_task_summaries"].append(f"{completed_name}：{one_shot_result['reply']}")
        combined_prefix = (
            f"{transition_prefix}\n{one_shot_result['reply']}" if transition_prefix else one_shot_result["reply"]
        )
        return _start_next_multi_task(actor_id, state, auth_token, transition_prefix=combined_prefix)

    result = _continue_collection(actor_id, state, latest_user_message="")
    return _prepend_reply(result, transition_prefix)


def _submit_and_continue_multi_task(
    actor_id: str,
    session_id: str,
    state: dict,
    text: str,
    auth_token: str | None,
) -> dict:
    result = _submit(actor_id, session_id, state, latest_user_message=text, auth_token=auth_token)
    if not state.get("is_multi_task"):
        # Single-service (non-multi-task) path keeps today's retry-in-place behavior:
        # on failure, awaiting_confirmation/state is left exactly as _submit set it so
        # the user can retry or correct the active task without losing their place.
        return result

    completed_name = _display_service_name(state["service_id"], state["service_name"])
    if state.get("request_id"):
        state["completed_task_summaries"].append(f"{completed_name}：{result['reply']}")
    else:
        # A failed task must not block the rest of the queue (design spec): mark it
        # 待重試 (pending retry) with the failure reason and move on, instead of
        # leaving the user stuck retrying a task that may be deterministically doomed
        # (e.g. quick_purchase BUNDLE_NOT_FOUND can never succeed for the same query,
        # and there's no way to correct it once awaiting_confirmation is true).
        state["completed_task_summaries"].append(f"{completed_name}：待重試（{result['reply']}）")

    state["service_id"] = None
    state["service_name"] = None
    state["service_schema"] = None
    state["collected_fields"] = {}
    state["missing_fields"] = []
    state["request_id"] = None
    state["status"] = "COLLECTING_INFORMATION"
    state["awaiting_confirmation"] = False
    return _start_next_multi_task(actor_id, state, auth_token, transition_prefix=result["reply"])


def _handle_task_selection_reply(actor_id: str, state: dict, text: str, auth_token: str | None) -> dict:
    services = _available_services(auth_token) or []
    selection = _select_multi_tasks(text, state["pending_tasks"], services)

    if selection["action"] == "cancel":
        state["pending_tasks"] = []
        state["is_multi_task"] = False
        state["awaiting_task_selection"] = False
        return _reply(state, "好的，這次先不進行任何任務，如果之後有需要我再幫你安排。")

    if selection["action"] == "unclear":
        # Prefer re-asking once over guessing "run everything" for an ambiguous reply.
        return _reply(
            state,
            "不好意思，我不太確定你想怎麼安排這些任務，可以直接說「全部」，"
            "或告訴我想先做哪幾項（例如「先做前兩個」或直接說任務名稱）嗎？",
        )

    state["pending_tasks"] = selection["tasks"]
    state["awaiting_task_selection"] = False
    return _start_next_multi_task(actor_id, state, auth_token)


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

    if state["service_id"] == "quick_purchase":
        return _submit_quick_purchase(actor_id, state, latest_user_message)

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


def _submit_quick_purchase(actor_id: str, state: dict, latest_user_message: str) -> dict:
    collected = state["collected_fields"]
    result = quick_purchase.create_quick_purchase_order(
        actor_id,
        collected.get("query", ""),
        contact_name="住戶",
        phone=collected.get("phone", ""),
        address=collected.get("address", ""),
    )

    if not result.get("success"):
        message = result.get("error", {}).get("message", "下單失敗")
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
    return _reply(state, f"{reply}\n已幫您選購「{result.get('bundle_name', '')}」。")


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


def _format_health_recommendation_reply(result: dict) -> str:
    recommendations = result.get("recommendations") or []
    if not recommendations:
        return "很抱歉，目前沒有找到符合這個需求的商品，要不要換個方式描述你的需求？"
    lines = ["這是我幫你找到的推薦商品："]
    for index, rec in enumerate(recommendations, start=1):
        lines.append(f"{index}. {rec.get('name', '')}：{rec.get('reason', '')}")
    if result.get("fallback_used"):
        lines.append("（這次是用關鍵字比對挑選的，僅供參考）")
    lines.append("如果想知道某項商品的詳細營養資訊，可以直接告訴我商品名稱。")
    return "\n".join(lines)


def _answer_health_recommendation(state: dict, query: str, auth_token: str | None) -> str:
    result = tools.call("recommend_products_by_health_need", {"query": query}, auth_token=auth_token)
    if not result.get("success"):
        message = result.get("error", {}).get("message", "查詢失敗")
        return f"抱歉，這次查詢沒有成功，原因是：{message}。你可以稍後再試一次。"
    state["health_last_recommendations"] = result.get("recommendations") or []
    return _format_health_recommendation_reply(result)


def _answer_price_compare(query: str, auth_token: str | None) -> tuple[str, str | None]:
    result = tools.call("compare_product_prices", {"query": query}, auth_token=auth_token)
    if not result.get("success"):
        return f"抱歉，沒有找到「{query}」的比價資訊，要不要換個商品名稱再試一次？", None
    offers = result["offers"]
    lines = [f"「{result['product_name']}」目前有 {len(offers)} 家店販售："]
    for index, offer in enumerate(offers):
        tag = "（最便宜）" if index == 0 else ""
        lines.append(f"　{offer['store_name']} NT${offer['unit_price']}{tag}")
    lines.append("我幫你打開比價頁面，可以直接選店家下單。")
    return "\n".join(lines), f"/services/shop_purchase?compare={result['group_id']}"


def _format_health_nutrition_reply(product: dict) -> str:
    lines = [
        f"{product.get('name', '')} 的營養資訊：",
        f"熱量：{product.get('calories')} kcal",
        f"蛋白質：{product.get('protein_g')} g",
        f"碳水：{product.get('carbs_g')} g",
        f"脂肪：{product.get('fat_g')} g",
        f"鈉：{product.get('sodium_mg')} mg",
    ]
    allergens = product.get("allergens") or []
    if allergens:
        lines.append(f"過敏原：{'、'.join(allergens)}")
    return "\n".join(lines)


def _handle_health_followup(state: dict, text: str, auth_token: str | None) -> str | None:
    """若使用者接著問剛才推薦清單裡某項商品，直接查營養資訊回答；否則回 None 讓一般流程繼續判斷。"""
    recommendations = state.get("health_last_recommendations") or []
    matched = next(
        (rec for rec in recommendations if rec.get("name") and rec["name"] in text),
        None,
    )
    if not matched:
        return None
    result = tools.call("get_product_nutrition", {"product_id": matched["product_id"]}, auth_token=auth_token)
    if not result.get("success"):
        return None
    return _format_health_nutrition_reply(result)


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


def _reply(
    state: dict,
    reply: str,
    redirect_path: str | None = None,
    redirect_requires_confirmation: bool = False,
    task_cards: list[dict] | None = None,
    share_text: str | None = None,
) -> dict:
    return {
        "reply": reply,
        "state": state,
        "redirect_path": redirect_path,
        "redirect_requires_confirmation": redirect_requires_confirmation,
        "debug_trace": state.get("debug_trace", {}),
        "task_cards": task_cards,
        "share_text": share_text,
    }
