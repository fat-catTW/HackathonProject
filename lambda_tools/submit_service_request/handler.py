"""Gateway tool handler for submitting service requests."""
from __future__ import annotations

import math
from datetime import date, datetime, timedelta, timezone

from shared_lambda.catalog import (
    convert_floats_to_decimal,
    dynamodb_table,
    field_is_visible,
    get_delivery_store,
    get_restaurant,
    get_shop_sku,
    load_service,
    next_request_id,
    now_iso,
    query_requests_by_actor,
    validate_required_fields,
)
import re
import secrets

TZ = timezone(timedelta(hours=8))

RESERVATION_ORDER_STATUS = {
    "PENDING_PROVIDER": "02",
    "CONFIRMED": "03",
}

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
    if isinstance(preferred_date, str) and preferred_date and not _is_future_or_today(
        preferred_date
    ):
        return "preferred_date must be today or a future date."
    return None


def _error(code: str, message: str) -> dict:
    return {
        "success": False,
        "error": {"code": code, "message": message},
    }


def _put_request_item(item: dict) -> None:
    dynamodb_table().put_item(Item=convert_floats_to_decimal(item))


def _missing_required_fields_message(
    fields: list[dict], missing: list[str], payload: dict
) -> str:
    field_labels = {
        field["id"]: field.get("label", field["id"])
        for field in fields
        if field_is_visible(field, payload)
    }
    labels = [field_labels.get(field_id, field_id) for field_id in missing]
    return f"缺少必填欄位：{'、'.join(labels)}。"


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    radius_km = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlng / 2) ** 2
    )
    return radius_km * 2 * math.asin(math.sqrt(a))


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
    distance = _haversine_km(
        _DELIVERY_SERVICE_CENTER[0], _DELIVERY_SERVICE_CENTER[1], lat, lng
    )
    if distance > _DELIVERY_SERVICE_RADIUS_KM:
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
    original_amount = sum(
        item.get("price", 0) * item.get("quantity", 1) for item in goods
    )
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


def _validate_reservation_date(selected_date: str) -> bool:
    try:
        selected = date.fromisoformat(selected_date)
    except ValueError:
        return False
    today = datetime.now(TZ).date()
    return today <= selected <= today + timedelta(days=60)


def _validate_reservation_people(people) -> bool:
    if isinstance(people, bool) or not isinstance(people, int):
        return False
    return 1 <= people <= 20


def _validate_reservation_phone(phone: str) -> bool:
    return (
        isinstance(phone, str)
        and len(phone) == 10
        and phone.startswith("09")
        and phone.isdigit()
    )


def _validate_reservation_contact_name(name: str) -> bool:
    return isinstance(name, str) and 1 <= len(name.strip()) <= 50


def _validate_reservation_specific_time(time_slot: str, specific_time: str) -> bool:
    if time_slot == "LUNCH":
        return specific_time in _LUNCH_TIMES
    if time_slot == "DINNER":
        return specific_time in _DINNER_TIMES
    return False


def _build_reservation_service_time(
    date_str: str, specific_time: str | None, time_slot: str
) -> str:
    if specific_time:
        return f"{date_str}T{specific_time}:00+08:00"
    default_time = "12:00" if time_slot == "LUNCH" else "18:00"
    return f"{date_str}T{default_time}:00+08:00"


def _reservation_duplicate_exists(
    actor_id: str, restaurant_id: str, reserved_date: str, time_slot: str
) -> bool:
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


def _submit_restaurant_reservation(
    actor_id: str, session_id: str, payload: dict
) -> dict:
    required = (
        "restaurant_id",
        "reserved_date",
        "time_slot",
        "people",
        "contact_name",
        "phone",
    )
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
    if specific_time and not _validate_reservation_specific_time(
        payload["time_slot"], specific_time
    ):
        return _error("INVALID_TIME_SLOT", "請選擇時段內的有效時間。")
    if not _validate_reservation_people(payload["people"]):
        return _error("INVALID_PEOPLE_COUNT", "用餐人數請填寫 1 至 20 人")
    if not _validate_reservation_contact_name(payload["contact_name"]):
        return _error("INVALID_CONTACT_NAME", "姓名請勿超過 50 個字，且不可為空白")
    if not _validate_reservation_phone(payload["phone"]):
        return _error(
            "INVALID_PHONE", "請輸入正確的手機號碼格式（09 開頭，共 10 碼）"
        )

    if _reservation_duplicate_exists(
        actor_id,
        payload["restaurant_id"],
        payload["reserved_date"],
        payload["time_slot"],
    ):
        return _error("DUPLICATE_RESERVATION", "這筆訂位已經成功送出囉，無需重複提交。")

    is_premium = bool(
        payload.get("is_premium") == "PREMIUM" or payload.get("is_premium") is True
    )
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
    service_time = _build_reservation_service_time(
        payload["reserved_date"], specific_time, payload["time_slot"]
    )

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
        "retry_info": {
            "retry_count": 0,
            "max_retries": 3,
            "last_retry_at": None,
            "needs_manual": False,
        },
        "status_history": [],
        "created_at": created_at,
        "updated_at": created_at,
    }

    booking_url: str | None = None
    if is_premium or not restaurant["supports_booking_api"]:
        status = "PENDING_PROVIDER"
    elif restaurant["verification_enabled"]:
        booking_id = f"EZ-MOCK-{request_id[-8:]}"
        status = "CONFIRMED"
        item["vendor_data"] = {
            "booking_id": booking_id,
            "share_reservation_url": f"https://eztable.example.com/booking/{booking_id}",
            "confirmed_at": created_at,
        }
        booking_url = item["vendor_data"]["share_reservation_url"]
    else:
        status = "PENDING_PROVIDER"

    item["status"] = status
    item["order_status"] = RESERVATION_ORDER_STATUS[status]
    item["status_history"].append({"status": item["order_status"], "at": created_at})

    try:
        _put_request_item(item)
    except Exception as exc:
        return _error(
            "ORDER_SAVE_FAILED", str(exc) or "Failed to save the reservation order."
        )

    return {
        "success": True,
        "request_id": request_id,
        "status": status,
        "order_status": item["order_status"],
        "booking_url": booking_url,
        "message": "訂位已建立。",
    }


_PHONE_RE = re.compile(r"^09\d{8}\Z")
POINTS_TO_NT_RATE = 1
PHYSICAL_SHIPPING_FEE = 60


def _submit_shop_order(actor_id: str, session_id: str, payload: dict) -> dict:
    cart = payload.get("cart")
    if not isinstance(cart, list) or not cart:
        return _error("EMPTY_CART", "購物車不能是空的")

    resolved: list[tuple[dict, dict, int]] = []  # (product, sku, quantity)
    for line in cart:
        if not isinstance(line, dict) or not line.get("sku_id"):
            return _error("INVALID_ITEM", "購物車項目缺少 sku_id")
        quantity = line.get("quantity")
        if not isinstance(quantity, int) or quantity <= 0:
            return _error("INVALID_ITEM", f"品項 {line.get('sku_id')} 的數量必須是正整數")
        found = get_shop_sku(line["sku_id"])
        if not found:
            return _error("SKU_NOT_FOUND", f"找不到商品規格 {line['sku_id']}")
        product, sku = found
        resolved.append((product, sku, quantity))

    contact_name = payload.get("contact_name")
    if not contact_name or not str(contact_name).strip():
        return _error("INVALID_CONTACT", "請填寫聯絡人姓名")

    phone = payload.get("phone")
    if not phone or not _PHONE_RE.match(str(phone)):
        return _error("INVALID_PHONE", "請填寫正確的手機號碼（09 開頭 10 碼）")

    used_points = payload.get("used_points", 0)
    if not isinstance(used_points, int) or used_points < 0:
        return _error("INVALID_POINTS", "折抵點數必須是不小於 0 的整數")

    has_physical = any(product["product_type"] == "PHYSICAL" for product, _sku, _qty in resolved)
    if has_physical and not payload.get("address"):
        return _error("MISSING_ADDRESS", "購物車內含實體商品，請填寫收件地址")

    original_amount = sum(sku["unit_price"] * qty for _p, sku, qty in resolved)
    shipping_fee = PHYSICAL_SHIPPING_FEE if has_physical else 0
    payable_before_points = original_amount + shipping_fee
    points_discount = min(max(used_points, 0), payable_before_points) * POINTS_TO_NT_RATE
    points_discount = min(points_discount, payable_before_points)
    total_amount = payable_before_points - points_discount
    points_earned = sum(sku["unit_points"] * qty for _p, sku, qty in resolved)

    table = dynamodb_table()

    points_deducted = 0
    if points_discount > 0:
        points_to_deduct = points_discount // POINTS_TO_NT_RATE
        try:
            table.update_item(
                Key={"PK": f"USER#{actor_id}", "SK": "POINTS"},
                UpdateExpression="SET balance = balance - :amt, updated_at = :now",
                ConditionExpression="balance >= :amt",
                ExpressionAttributeValues={":amt": points_to_deduct, ":now": now_iso()},
            )
            points_deducted = points_to_deduct
        except Exception:
            return _error("INSUFFICIENT_POINTS", "點數餘額不足")

    decremented: list[tuple[str, int]] = []
    for _product, sku, qty in resolved:
        try:
            table.update_item(
                Key={"PK": f"SHOP_SKU#{sku['sku_id']}", "SK": "STOCK"},
                UpdateExpression="SET quantity = quantity - :qty, updated_at = :now",
                ConditionExpression="quantity >= :qty",
                ExpressionAttributeValues={":qty": qty, ":now": now_iso()},
            )
            decremented.append((sku["sku_id"], qty))
        except Exception:
            for sku_id, quantity in decremented:
                table.update_item(
                    Key={"PK": f"SHOP_SKU#{sku_id}", "SK": "STOCK"},
                    UpdateExpression="SET quantity = quantity + :qty, updated_at = :now",
                    ExpressionAttributeValues={":qty": quantity, ":now": now_iso()},
                )
            if points_deducted:
                table.update_item(
                    Key={"PK": f"USER#{actor_id}", "SK": "POINTS"},
                    UpdateExpression="SET balance = balance + :amt, updated_at = :now",
                    ExpressionAttributeValues={":amt": points_deducted, ":now": now_iso()},
                )
            return _error("OUT_OF_STOCK", f"商品規格「{sku['sku_id']}」庫存不足")

    table.update_item(
        Key={"PK": f"USER#{actor_id}", "SK": "POINTS"},
        UpdateExpression="SET balance = if_not_exists(balance, :zero) + :amt, updated_at = :now",
        ExpressionAttributeValues={":zero": 0, ":amt": points_earned, ":now": now_iso()},
    )

    redemption_codes: dict[str, list[str]] = {}
    for product, sku, qty in resolved:
        if product["product_type"] == "SERIAL_CODE":
            redemption_codes[sku["sku_id"]] = [secrets.token_hex(4).upper() for _ in range(qty)]

    request_id = next_request_id()
    order_status = "COMPLETED" if not has_physical else "SUBMITTED"
    order_type = "07" if not has_physical else "10"
    item = {
        "PK": f"USER#{actor_id}",
        "SK": f"REQUEST#{request_id}",
        "entity_type": "SERVICE_REQUEST",
        "request_id": request_id,
        "service_id": "shop_purchase",
        "service_name": "商城購物",
        "order_type": order_type,
        "status": order_status,
        "form_data": {
            "cart": cart,
            "contact_name": contact_name,
            "phone": phone,
            "address": payload.get("address"),
            "used_points": used_points,
        },
        "original_amount": original_amount,
        "shipping_fee_amount": shipping_fee,
        "points_discount": points_discount,
        "total_amount": total_amount,
        "points_earned": points_earned,
        "redemption_codes": redemption_codes,
        "status_history": [{"status": order_status, "at": now_iso()}],
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    _put_request_item(item)

    return {
        "success": True,
        "request_id": request_id,
        "status": order_status,
        "total_amount": total_amount,
        "points_earned": points_earned,
        "redemption_codes": redemption_codes,
    }


def _submit_generic(actor_id: str, session_id: str, service: dict, payload: dict) -> dict:
    missing_fields = validate_required_fields(service["schema"]["fields"], payload)
    if missing_fields:
        return {
            "success": False,
            "error": {
                "code": "INVALID_FORM_DATA",
                "message": _missing_required_fields_message(
                    service["schema"]["fields"], missing_fields, payload
                ),
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
        if service["id"] == "shop_purchase":
            return _submit_shop_order(actor_id, session_id, payload)
        return _submit_generic(actor_id, session_id, service, payload)
    except Exception as exc:
        return _error(
            "TOOL_INVOCATION_FAILED", str(exc) or "Failed to submit service request."
        )
