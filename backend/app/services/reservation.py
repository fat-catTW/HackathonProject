"""Core reservation order service."""
from __future__ import annotations

import asyncio
import sys

from . import reservation_validators as validators
from . import restaurant_catalog
from . import retry_service
from .booking_adapter import BookingStatus, get_booking_adapter
from .store import STORE, now_iso


def _run_async(coro):
    """Run an async coroutine in a safe way that works in threaded contexts (Python 3.10+)."""
    try:
        # Try to get the running event loop (if we're already in async context)
        loop = asyncio.get_running_loop()
        # We can't use run_until_complete on a running loop, so we'd need to wrap it
        # But for now, try the old approach first
    except RuntimeError:
        # No running loop, safe to use get_event_loop or create new one
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)

    # If we got here, we're in an async context. This shouldn't happen in normal sync code
    # but we need to handle it gracefully. Fall back to creating a new loop in a thread.
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor() as pool:
        return pool.submit(asyncio.run, coro).result()

TEXT_TO_ORDER_STATUS: dict[str, str] = {
    "PENDING_PROVIDER": "02",
    "CONFIRMED": "03",
    "IN_PROGRESS": "04",
    "COMPLETED": "70",
    "VERIFIED": "80",
    "CANCELLED": "90",
}

_REQUIRED_FIELDS = (
    "restaurant_id",
    "reserved_date",
    "time_slot",
    "people",
    "contact_name",
    "phone",
)


def _error(code: str, message: str) -> dict:
    return {"success": False, "error": {"code": code, "message": message}}


def _validate_payload(payload: dict) -> dict | None:
    for field_id in _REQUIRED_FIELDS:
        if payload.get(field_id) in (None, ""):
            return _error("INVALID_FORM_DATA", f"Missing required field: {field_id}")

    restaurant = restaurant_catalog.get_restaurant(payload["restaurant_id"])
    if not restaurant:
        return _error("RESTAURANT_NOT_FOUND", "找不到指定的餐廳。")

    if not validators.validate_date(payload["reserved_date"]):
        return _error("INVALID_DATE", "請選擇未來 60 天內的日期。")

    if not validators.validate_time_slot(payload["time_slot"]):
        return _error("INVALID_TIME_SLOT", "請選擇午餐或晚餐時段。")

    specific_time = payload.get("specific_time")
    if specific_time and not validators.validate_specific_time(payload["time_slot"], specific_time):
        return _error("INVALID_TIME_SLOT", "請選擇時段內的有效時間。")

    if not validators.validate_people(payload["people"]):
        return _error("INVALID_PEOPLE_COUNT", "用餐人數請填寫 1 至 20 人")

    if not validators.validate_contact_name(payload["contact_name"]):
        return _error("INVALID_CONTACT_NAME", "姓名請勿超過 50 個字，且不可為空白")

    if not validators.validate_phone(payload["phone"]):
        return _error("INVALID_PHONE", "請輸入正確的手機號碼格式（09 開頭，共 10 碼）")

    if not validators.validate_preference_note(payload.get("preference_note")):
        return _error("PREFERENCE_TOO_LONG", "偏好描述請勿超過 200 字")

    return None


def check_duplicate(actor_id: str, restaurant_id: str, reserved_date: str, time_slot: str) -> bool:
    existing = STORE.query_prefix(f"USER#{actor_id}", "REQUEST#")
    for item in existing:
        if item.get("service_id") != "restaurant_reservation":
            continue
        if item.get("status") == "CANCELLED":
            continue
        order_items = item.get("order_items") or {}
        if (
            order_items.get("restaurant_id") == restaurant_id
            and order_items.get("reserved_date") == reserved_date
            and order_items.get("time_slot") == time_slot
        ):
            return True
    return False


def create_reservation_order(actor_id: str, payload: dict) -> dict:
    validation_error = _validate_payload(payload)
    if validation_error:
        return validation_error

    restaurant = restaurant_catalog.get_restaurant(payload["restaurant_id"])

    if check_duplicate(actor_id, payload["restaurant_id"], payload["reserved_date"], payload["time_slot"]):
        return _error("DUPLICATE_RESERVATION", "這筆訂位已經成功送出囉，無需重複提交。")

    is_premium = bool(payload.get("is_premium", False))
    order_items = {
        "restaurant_id": restaurant["id"],
        "restaurant_name": restaurant["name"],
        "restaurant_phone": restaurant["phone"],
        "restaurant_address": restaurant["address"],
        "people": payload["people"],
        "is_premium": is_premium,
        "reserved_date": payload["reserved_date"],
        "time_slot": payload["time_slot"],
        "specific_time": payload.get("specific_time"),
        "contact_name": payload["contact_name"],
        "phone": payload["phone"],
        "preference_note": payload.get("preference_note"),
    }
    service_time = validators.build_service_time(
        payload["reserved_date"], payload.get("specific_time"), payload["time_slot"]
    )

    request_id = STORE.next_request_id()
    created_at = now_iso()
    order = {
        "request_id": request_id,
        "session_id": None,
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
            "specific_time": payload.get("specific_time"),
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
    }

    booking_url: str | None = None
    if is_premium or not restaurant["supports_booking_api"]:
        status = "PENDING_PROVIDER"
    else:
        result = _run_async(
            get_booking_adapter().create_booking(
                restaurant_id=restaurant["id"],
                date=payload["reserved_date"],
                time=payload.get("specific_time") or "",
                people=payload["people"],
                contact_name=payload["contact_name"],
                phone=payload["phone"],
            )
        )
        if result.status == BookingStatus.CONFIRMED:
            status = "CONFIRMED"
            order["vendor_data"] = {
                "booking_id": result.booking_id,
                "share_reservation_url": result.share_reservation_url,
                "confirmed_at": now_iso(),
            }
            booking_url = result.share_reservation_url
        else:
            status = "PENDING_PROVIDER"
            retry_service.mark_for_retry(order)

    order["status"] = status
    order["order_status"] = TEXT_TO_ORDER_STATUS[status]
    order["status_history"].append({"status": order["order_status"], "at": created_at})

    try:
        STORE.save_request(actor_id, order)
    except Exception as exc:
        return _error("ORDER_SAVE_FAILED", str(exc))

    return {
        "success": True,
        "request_id": request_id,
        "status": status,
        "order_status": order["order_status"],
        "booking_url": booking_url,
    }


def get_reservation_order(actor_id: str, request_id: str) -> dict | None:
    return STORE.get_request(actor_id, request_id)


def cancel_reservation_order(actor_id: str, request_id: str) -> dict:
    order = STORE.get_request(actor_id, request_id)
    if not order:
        return _error("REQUEST_NOT_FOUND", "找不到對應的訂位。")

    order["status"] = "CANCELLED"
    order["order_status"] = TEXT_TO_ORDER_STATUS["CANCELLED"]
    order.setdefault("status_history", []).append(
        {"status": order["order_status"], "at": now_iso()}
    )
    STORE.save_request(actor_id, order)
    return {"success": True, "request_id": request_id, "status": "CANCELLED"}
