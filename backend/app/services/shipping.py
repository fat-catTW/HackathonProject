"""Package shipping order service (統一速達／黑貓宅急便 + 7-11 店到店)."""
from __future__ import annotations

from . import catalog
from .store import STORE, now_iso

EXCLUDED_COUNTIES = {"金門縣", "連江縣", "澎湖縣"}

PROHIBITED_KEYWORDS: dict[str, tuple[str, ...]] = {
    "危險/易燃易爆物品": ("電池", "鋰電池", "瓦斯", "打火機", "油漆", "易燃", "易爆"),
    "易碎品": ("玻璃", "瓷器", "易碎"),
    "生鮮/冷藏冷凍食品": ("生鮮", "冷藏", "冷凍", "海鮮", "肉品"),
    "精密儀器/3C家電": ("筆電", "手機", "相機", "3C", "家電", "精密儀器"),
    "有價證券/證件": ("現金", "股票", "票券", "證件", "有價證券"),
}

# 需要進行數字運算（材積、超重、申報價值上限）的欄位；接受原始 API 呼叫時可能是字串，
# 必須先驗證型別才能做加總／比較，避免未經驗證的算術丟出未處理的例外。
_NUMERIC_FIELDS = ("weight_kg", "length_cm", "width_cm", "height_cm", "declared_value")


def contains_prohibited_keywords(text: str) -> list[str]:
    return [
        category
        for category, keywords in PROHIBITED_KEYWORDS.items()
        if any(keyword in text for keyword in keywords)
    ]


def _field_is_visible(field: dict, payload: dict) -> bool:
    visible_when = field.get("visibleWhen")
    if not isinstance(visible_when, dict):
        return True
    parent_field_id = visible_when.get("fieldId")
    expected_value = visible_when.get("value")
    if not isinstance(parent_field_id, str):
        return True
    return payload.get(parent_field_id) == expected_value


def _schema_fields() -> list[dict]:
    schema = catalog.get_service_schema("package_shipping") or {"fields": []}
    return schema["fields"]


def _missing_required_fields(payload: dict) -> list[str]:
    fields = _schema_fields()
    required = [
        field["id"]
        for field in fields
        if field.get("required") and _field_is_visible(field, payload)
    ]
    return [field_id for field_id in required if payload.get(field_id) in (None, "")]


def _missing_required_fields_message(missing: list[str]) -> str:
    field_labels = {field["id"]: field.get("label", field["id"]) for field in _schema_fields()}
    labels = [field_labels.get(field_id, field_id) for field_id in missing]
    return f"缺少必填欄位：{'、'.join(labels)}。"


def _is_valid_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def estimate_shipping_fee(
    pickup_method: str, weight_kg: float, length_cm: float, width_cm: float, height_cm: float
) -> tuple[int, int]:
    total_cm = length_cm + width_cm + height_cm
    if pickup_method == "HOME_PICKUP":
        if total_cm <= 60:
            return (110, 110)
        if total_cm <= 90:
            return (150, 150)
        return (190, 190)  # 91–120cm；超過 120cm 由 _validate_payload 擋下
    if total_cm <= 105:
        return (60, 60)
    return (125, 135)  # 106–120cm 大包裹；超過 120cm 由 _validate_payload 擋下


def _error(code: str, message: str) -> dict:
    return {"success": False, "error": {"code": code, "message": message}}


def _validate_payload(payload: dict) -> dict | None:
    missing = _missing_required_fields(payload)
    if missing:
        return {
            "success": False,
            "error": {
                "code": "INVALID_FORM_DATA",
                "message": _missing_required_fields_message(missing),
                "missing_fields": missing,
            },
        }

    pickup_method = payload["pickup_method"]
    if pickup_method not in ("HOME_PICKUP", "STORE_TO_STORE"):
        return _error("INVALID_FORM_DATA", "pickup_method 必須是 HOME_PICKUP 或 STORE_TO_STORE。")

    invalid_numeric = [field_id for field_id in _NUMERIC_FIELDS if not _is_valid_number(payload.get(field_id))]
    if invalid_numeric:
        return _error("INVALID_FORM_DATA", "包裹重量、長寬高與申報價值必須是數字。")

    if not payload.get("prohibited_item_ack"):
        matched = contains_prohibited_keywords(payload["item_description"])
        if matched:
            categories = "、".join(matched)
            return _error(
                "PROHIBITED_ITEM",
                f"你提到的內容物可能屬於「{categories}」類別，這類物品寄送有限制，請確認內容物是否可以寄送。",
            )

    total_cm = payload["length_cm"] + payload["width_cm"] + payload["height_cm"]
    weight_kg = payload["weight_kg"]

    if pickup_method == "HOME_PICKUP":
        if total_cm > 120 or weight_kg > 20:
            return _error(
                "PACKAGE_TOO_LARGE",
                "包裹尺寸或重量超過到府收件上限（三邊合計120公分、20公斤），請聯繫客服安排其他貨運。",
            )
        sender_address = payload.get("sender_address", "")
        if any(county in sender_address for county in EXCLUDED_COUNTIES):
            return _error("OUT_OF_SERVICE_AREA", "暫不提供此地區收件服務。")
    else:
        if total_cm > 120 or weight_kg > 5:
            return _error(
                "PACKAGE_TOO_LARGE",
                "包裹尺寸或重量超過店到店上限（三邊合計120公分、5公斤），請改選到府收件。",
            )
        if payload["declared_value"] > 5000:
            return _error("DECLARED_VALUE_TOO_HIGH", "申報價值超過店到店上限（5,000元），請改選到府收件。")

    return None


def create_shipping_order(actor_id: str, payload: dict) -> dict:
    validation_error = _validate_payload(payload)
    if validation_error:
        return validation_error

    fee_min, fee_max = estimate_shipping_fee(
        payload["pickup_method"],
        payload["weight_kg"],
        payload["length_cm"],
        payload["width_cm"],
        payload["height_cm"],
    )

    request_id = STORE.next_request_id()
    created_at = now_iso()
    order = {
        "request_id": request_id,
        "session_id": payload.get("session_id"),
        "service_id": "package_shipping",
        "service_name": "包裹寄送",
        "service_vendor_id": 2,
        "order_type": "20",
        "order_status": "01",
        "status": "AWAITING_QUOTE",
        "form_data": {k: v for k, v in payload.items() if k not in ("session_id", "prohibited_item_ack")},
        "estimated_fee_min": fee_min,
        "estimated_fee_max": fee_max,
        "created_at": created_at,
    }

    try:
        STORE.save_request(actor_id, order)
    except Exception as exc:
        return _error("ORDER_SAVE_FAILED", str(exc))

    return {
        "success": True,
        "request_id": request_id,
        "status": "AWAITING_QUOTE",
        "order_status": "01",
        "estimated_fee_min": fee_min,
        "estimated_fee_max": fee_max,
    }
