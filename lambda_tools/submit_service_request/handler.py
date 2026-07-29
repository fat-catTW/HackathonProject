"""Gateway tool handler for submitting service requests."""
from __future__ import annotations

import math
from datetime import date, datetime, timedelta, timezone

from shared_lambda.catalog import (
    convert_floats_to_decimal,
    dynamodb_table,
    get_delivery_store,
    get_restaurant,
    load_service,
    next_request_id,
    now_iso,
    query_requests_by_actor,
    validate_required_fields,
)

TZ = timezone(timedelta(hours=8))

# --- 餐廳訂位平台狀態碼（複製自 backend/app/services/reservation.py 的
#     TEXT_TO_ORDER_STATUS，兩邊分開部署各自維護一份） ---
RESERVATION_ORDER_STATUS = {
    "PENDING_PROVIDER": "02",
    "CONFIRMED": "03",
}

# --- 美食外送外送範圍（複製自 backend/app/services/delivery.py） ---
_DELIVERY_SERVICE_CENTER = (25.033, 121.565)
_DELIVERY_SERVICE_RADIUS_KM = 10.0

_LUNCH_TIMES = [f"{h:02d}:{m:02d}" for h in range(11, 14) for m in (0, 30)]
_DINNER_TIMES = [f"{h:02d}:{m:02d}" for h in range(17, 21) for m in (0, 30)]


def _context_value(context, key: str) -> str | None:
    client_context = getattr(context, "client_context", None)
    custom = getattr(client_context, "custom", None)
    if isinstance(custom, dict):
        value = custom.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _verified_actor_id(event: dict, context) -> str | None:
    request_context = event.get("requestContext") or {}
    identity = request_context.get("identity") or {}
    for value in (
        identity.get("actorId"),
        event.get("actor_id"),
        _context_value(context, "actorId"),
        _context_value(context, "principalId"),
    ):
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _is_future_or_today(raw_date: str) -> bool:
    try:
        return date.fromisoformat(raw_date) >= date.today()
    except ValueError:
        return False


def _validate_payload_shape(payload: dict) -> str | None:
    if not isinstance(payload, dict):
        return "payload must be an object."
    preferred_date = payload.get("preferred_date")
    if isinstance(preferred_date, str) and preferred_date and not _is_future_or_today(preferred_date):
        return "preferred_date must be today or a future date."
    return None


def _error(code: str, message: str) -> dict:
    return {
        "success": False,
        "error": {"code": code, "message": message},
    }


def _put_request_item(item: dict) -> None:
    dynamodb_table().put_item(Item=convert_floats_to_decimal(item))


# ---------------------------------------------------------------------------
# 美食外送（複製自 backend/app/services/delivery.py 的驗證與金額計算邏輯）
# ---------------------------------------------------------------------------

def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    return r * 2 * math.asin(math.sqrt(a))


def _validate_delivery_address(address) -> dict | None:
    if not isinstance(address, dict):
        return _error("INVALID_ADDRESS", "外送地址為必填。")
    lat = address.get("lat")
    lng = address.get("lng")
    if lat is None or lng is None:
        return _error("INVALID_ADDRESS", "請提供有效的外送地址（含經緯度）。")
    try:
        lat = float(lat)
        lng = float(lng)
    except (ValueError, TypeError):
        return _error("INVALID_ADDRESS", "經緯度格式無效。")
    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        return _error("INVALID_ADDRESS", "經緯度超出有效範圍。")
    dist = _haversine_km(_DELIVERY_SERVICE_CENTER[0], _DELIVERY_SERVICE_CENTER[1], lat, lng)
    if dist > _DELIVERY_SERVICE_RADIUS_KM:
        return _error("OUT_OF_RANGE", "該地址暫不提供外送服務，請確認外送範圍。")
    if not address.get("city") and not address.get("street"):
        return _error("INVALID_ADDRESS", "請填寫外送地址的市區或街道資訊。")
    if not address.get("contact_name"):
        return _error("INVALID_CONTACT", "請填寫收件人姓名。")
    return None


def _validate_delivery_goods(goods) -> dict | None:
    if not goods or not isinstance(goods, list):
        return _error("EMPTY_CART", "購物車不可為空，請至少選擇一項品項。")
    for idx, item in enumerate(goods):
        if not isinstance(item, dict) or not item.get("id"):
            return _error("INVALID_ITEM", f"品項 #{idx + 1} 缺少 id。")
        if not item.get("title"):
            return _error("INVALID_ITEM", f"品項 #{idx + 1} 缺少品名。")
        qty = item.get("quantity", 0)
        if not isinstance(qty, int) or qty < 1:
            return _error("INVALID_ITEM", f"品項 #{idx + 1} 數量需為正整數。")
        price = item.get("price", 0)
        if not isinstance(price, (int, float)) or price < 0:
            return _error("INVALID_ITEM", f"品項 #{idx + 1} 價格無效。")
    return None


def _submit_food_delivery(actor_id: str, session_id: str, payload: dict) -> dict:
    address = payload.get("address")
    address_error = _validate_delivery_address(address)
    if address_error:
        return address_error

    goods = payload.get("goods")
    goods_error = _validate_delivery_goods(goods)
    if goods_error:
        return goods_error

    store_id = payload.get("store_id")
    store = get_delivery_store(store_id)
    if not store:
        return _error("MISSING_STORE", "請選擇外送店家。")

    shipping_fee = int(payload.get("shipping_fee", 60))
    original_amount = sum(item.get("price", 0) * item.get("quantity", 1) for item in goods)
    total_amount = original_amount + shipping_fee

    request_id = next_request_id()
    created_at = now_iso()
    order_items = {
        "user": {"address": address},
        "goods": goods,
        "store": {
            "id": store["id"],
            "name": store["name"],
            "address": store["address"],
            "url": store.get("url", ""),
        },
        "note": payload.get("note", ""),
    }
    item = {
        "PK": f"USER#{actor_id}",
        "SK": f"REQUEST#{request_id}",
        "entity_type": "SERVICE_REQUEST",
        "request_id": request_id,
        "session_id": session_id,
        "service_id": "food_delivery",
        "service_name": "美食外送",
        "order_type": "06",
        "order_items": order_items,
        "original_amount": original_amount,
        "shipping_fee_amount": shipping_fee,
        "total_amount": total_amount,
        "status": "PENDING",
        "order_status": "01",
        "vendor_data": {"delivery": None, "order_status": None},
        "cancel_reason": None,
        "form_data": {
            "address": address,
            "goods": goods,
            "store_id": store["id"],
            "store_name": store["name"],
            "note": payload.get("note", ""),
        },
        "status_history": [{"status": "01", "at": created_at}],
        "created_at": created_at,
        "updated_at": created_at,
    }

    try:
        _put_request_item(item)
    except Exception as exc:
        return _error("ORDER_SAVE_FAILED", str(exc) or "Failed to save the delivery order.")

    return {
        "success": True,
        "request_id": request_id,
        "status": "SUBMITTED",
        "order_status": "01",
        "total_amount": total_amount,
        "message": "外送訂單已建立。",
    }


# ---------------------------------------------------------------------------
# 餐廳訂位（複製自 backend/app/services/reservation.py 的驗證與 Mock 訂位邏輯）
# ---------------------------------------------------------------------------

def _validate_reservation_date(selected_date: str) -> bool:
    try:
        d = date.fromisoformat(selected_date)
    except ValueError:
        return False
    today = datetime.now(TZ).date()
    return today <= d <= today + timedelta(days=60)


def _validate_reservation_people(people) -> bool:
    if isinstance(people, bool) or not isinstance(people, int):
        return False
    return 1 <= people <= 20


def _validate_reservation_phone(phone: str) -> bool:
    return isinstance(phone, str) and len(phone) == 10 and phone.startswith("09") and phone.isdigit()


def _validate_reservation_contact_name(name: str) -> bool:
    return isinstance(name, str) and 1 <= len(name.strip()) <= 50


def _validate_reservation_specific_time(time_slot: str, specific_time: str) -> bool:
    if time_slot == "LUNCH":
        return specific_time in _LUNCH_TIMES
    if time_slot == "DINNER":
        return specific_time in _DINNER_TIMES
    return False


def _build_reservation_service_time(date_str: str, specific_time: str | None, time_slot: str) -> str:
    if specific_time:
        return f"{date_str}T{specific_time}:00+08:00"
    default_time = "12:00" if time_slot == "LUNCH" else "18:00"
    return f"{date_str}T{default_time}:00+08:00"


def _reservation_duplicate_exists(actor_id: str, restaurant_id: str, reserved_date: str, time_slot: str) -> bool:
    for existing in query_requests_by_actor(actor_id):
        if existing.get("service_id") != "restaurant_reservation":
            continue
        if existing.get("status") == "CANCELLED":
            continue
        order_items = existing.get("order_items") or {}
        if (
            order_items.get("restaurant_id") == restaurant_id
            and order_items.get("reserved_date") == reserved_date
            and order_items.get("time_slot") == time_slot
        ):
            return True
    return False


def _submit_restaurant_reservation(actor_id: str, session_id: str, payload: dict) -> dict:
    required = ("restaurant_id", "reserved_date", "time_slot", "people", "contact_name", "phone")
    for field_id in required:
        if payload.get(field_id) in (None, ""):
            return _error("INVALID_FORM_DATA", f"Missing required field: {field_id}")

    restaurant = get_restaurant(payload["restaurant_id"])
    if not restaurant:
        return _error("RESTAURANT_NOT_FOUND", "找不到指定的餐廳。")
    if not _validate_reservation_date(payload["reserved_date"]):
        return _error("INVALID_DATE", "請選擇未來 60 天內的日期。")
    if payload["time_slot"] not in ("LUNCH", "DINNER"):
        return _error("INVALID_TIME_SLOT", "請選擇午餐或晚餐時段。")
    specific_time = payload.get("specific_time")
    if specific_time and not _validate_reservation_specific_time(payload["time_slot"], specific_time):
        return _error("INVALID_TIME_SLOT", "請選擇時段內的有效時間。")
    if not _validate_reservation_people(payload["people"]):
        return _error("INVALID_PEOPLE_COUNT", "用餐人數請填寫 1 至 20 人")
    if not _validate_reservation_contact_name(payload["contact_name"]):
        return _error("INVALID_CONTACT_NAME", "姓名請勿超過 50 個字，且不可為空白")
    if not _validate_reservation_phone(payload["phone"]):
        return _error("INVALID_PHONE", "請輸入正確的手機號碼格式（09 開頭，共 10 碼）")

    if _reservation_duplicate_exists(actor_id, payload["restaurant_id"], payload["reserved_date"], payload["time_slot"]):
        return _error("DUPLICATE_RESERVATION", "這筆訂位已經成功送出囉，無需重複提交。")

    is_premium = bool(payload.get("is_premium") == "PREMIUM" or payload.get("is_premium") is True)
    order_items = {
        "restaurant_id": restaurant["id"],
        "restaurant_name": restaurant["name"],
        "restaurant_phone": restaurant["phone"],
        "restaurant_address": restaurant["address"],
        "people": payload["people"],
        "is_premium": is_premium,
        "reserved_date": payload["reserved_date"],
        "time_slot": payload["time_slot"],
        "specific_time": specific_time,
        "contact_name": payload["contact_name"],
        "phone": payload["phone"],
        "preference_note": payload.get("preference_note"),
    }
    service_time = _build_reservation_service_time(payload["reserved_date"], specific_time, payload["time_slot"])

    request_id = next_request_id()
    created_at = now_iso()
    item = {
        "PK": f"USER#{actor_id}",
        "SK": f"REQUEST#{request_id}",
        "entity_type": "SERVICE_REQUEST",
        "request_id": request_id,
        "session_id": session_id,
        "service_id": "restaurant_reservation",
        "service_name": "餐廳訂位",
        "order_type": "02",
        "order_items": order_items,
        "service_time": service_time,
        "form_data": {
            "restaurant_name": restaurant["name"],
            "restaurant_phone": restaurant["phone"],
            "restaurant_address": restaurant["address"],
            "reserved_date": payload["reserved_date"],
            "time_slot": payload["time_slot"],
            "specific_time": specific_time,
            "people": payload["people"],
            "contact_name": payload["contact_name"],
            "phone": payload["phone"],
            "preference_note": payload.get("preference_note"),
            "is_premium": is_premium,
        },
        "vendor_data": {},
        "retry_info": {"retry_count": 0, "max_retries": 3, "last_retry_at": None, "needs_manual": False},
        "status_history": [],
        "created_at": created_at,
        "updated_at": created_at,
    }

    booking_url: str | None = None
    if is_premium or not restaurant["supports_booking_api"]:
        status = "PENDING_PROVIDER"
    elif restaurant["verification_enabled"]:
        # Mock third-party booking confirmation — mirrors
        # backend/app/services/booking_adapter.py's MockEZTableAdapter,
        # which confirms immediately for verification_enabled restaurants.
        booking_id = f"EZ-MOCK-{request_id[-8:]}"
        status = "CONFIRMED"
        item["vendor_data"] = {
            "booking_id": booking_id,
            "share_reservation_url": f"https://eztable.example.com/booking/{booking_id}",
            "confirmed_at": created_at,
        }
        booking_url = item["vendor_data"]["share_reservation_url"]
    else:
        # Mock adapter failure — mirrors MockEZTableAdapter's ERROR path for
        # verification_enabled=False restaurants. The full retry queue
        # (backend/app/services/retry_service.py) isn't ported here: the
        # backend itself only keeps a stub for it (see the reservation
        # plan's Task 6, intentionally skipped), so there is nothing
        # meaningful to replicate — the order just stays PENDING_PROVIDER.
        status = "PENDING_PROVIDER"

    item["status"] = status
    item["order_status"] = RESERVATION_ORDER_STATUS[status]
    item["status_history"].append({"status": item["order_status"], "at": created_at})

    try:
        _put_request_item(item)
    except Exception as exc:
        return _error("ORDER_SAVE_FAILED", str(exc) or "Failed to save the reservation order.")

    return {
        "success": True,
        "request_id": request_id,
        "status": status,
        "order_status": item["order_status"],
        "booking_url": booking_url,
        "message": "訂位已建立。",
    }


# ---------------------------------------------------------------------------
# 一般服務（水電修繕／洗衣機清洗／冷氣清洗／居家清潔）——行為不變
# ---------------------------------------------------------------------------

def _submit_generic(actor_id: str, session_id: str, service: dict, payload: dict) -> dict:
    missing_fields = validate_required_fields(service["schema"]["fields"], payload)
    if missing_fields:
        return {
            "success": False,
            "error": {
                "code": "INVALID_FORM_DATA",
                "message": "Missing required fields.",
                "missing_fields": missing_fields,
            },
        }

    request_id = next_request_id()
    timestamp = now_iso()
    item = {
        "PK": f"USER#{actor_id}",
        "SK": f"REQUEST#{request_id}",
        "entity_type": "SERVICE_REQUEST",
        "request_id": request_id,
        "session_id": session_id,
        "service_id": service["id"],
        "service_name": service["name"],
        "status": "SUBMITTED",
        "form_data": payload,
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    _put_request_item(item)
    return {
        "success": True,
        "request_id": request_id,
        "status": "SUBMITTED",
        "message": "Service request submitted.",
    }


def lambda_handler(event, context):
    event = event or {}
    service_id = event.get("service_id")
    session_id = event.get("session_id")
    payload = event.get("payload") or {}
    actor_id = _verified_actor_id(event, context)

    if not service_id:
        return _error("INVALID_FORM_DATA", "service_id is required.")
    if not session_id:
        return _error("INVALID_FORM_DATA", "session_id is required.")
    if not actor_id:
        return _error("UNAUTHORIZED", "Unable to determine actor identity.")

    payload_error = _validate_payload_shape(payload)
    if payload_error:
        return _error("INVALID_FORM_DATA", payload_error)

    try:
        service = load_service(service_id)
        if not service:
            return _error("SERVICE_NOT_FOUND", f"Unknown service_id: {service_id}.")

        if service["id"] == "food_delivery":
            return _submit_food_delivery(actor_id, session_id, payload)
        if service["id"] == "restaurant_reservation":
            return _submit_restaurant_reservation(actor_id, session_id, payload)
        return _submit_generic(actor_id, session_id, service, payload)
    except Exception as exc:
        return _error("TOOL_INVOCATION_FAILED", str(exc) or "Failed to submit service request.")
