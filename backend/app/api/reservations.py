"""Restaurant reservation API endpoints."""
from fastapi import APIRouter, Depends, HTTPException

from ..auth.cognito import CurrentUser, get_current_user
from ..services import reservation, restaurant_catalog, restaurant_search

router = APIRouter()


def _raise_api_error(status_code: int, code: str, message: str):
    raise HTTPException(status_code=status_code, detail={"success": False, "error": {"code": code, "message": message}})


@router.get("/api/restaurants")
def list_restaurants(user: CurrentUser = Depends(get_current_user)):
    return {"restaurants": restaurant_catalog.list_restaurants()}


@router.post("/api/restaurants/search")
def search_restaurants(payload: dict, user: CurrentUser = Depends(get_current_user)):
    address = str(payload.get("address") or "").strip()
    if not address:
        _raise_api_error(400, "INVALID_FORM_DATA", "請提供地址")
    preference = str(payload.get("preference") or "")
    return restaurant_search.search_restaurants(user.sub, address, preference)


@router.get("/api/restaurants/{restaurant_id}")
def get_restaurant(restaurant_id: str, user: CurrentUser = Depends(get_current_user)):
    restaurant = restaurant_catalog.get_restaurant(restaurant_id)
    if not restaurant:
        _raise_api_error(404, "RESTAURANT_NOT_FOUND", "找不到指定的餐廳。")
    return restaurant


@router.post("/api/reservations/submit")
def submit_reservation(payload: dict, user: CurrentUser = Depends(get_current_user)):
    result = reservation.create_reservation_order(user.sub, payload)
    if not result.get("success"):
        error = result.get("error", {})
        status_code = 409 if error.get("code") == "DUPLICATE_RESERVATION" else 400
        _raise_api_error(status_code, error.get("code", "RESERVATION_FAILED"), error.get("message", "訂位失敗"))
    return result


@router.get("/api/reservations/{request_id}")
def get_reservation(request_id: str, user: CurrentUser = Depends(get_current_user)):
    order = reservation.get_reservation_order(user.sub, request_id)
    if not order:
        _raise_api_error(404, "REQUEST_NOT_FOUND", "找不到對應的訂位。")
    return order


@router.post("/api/reservations/{request_id}/cancel")
def cancel_reservation(request_id: str, user: CurrentUser = Depends(get_current_user)):
    result = reservation.cancel_reservation_order(user.sub, request_id)
    if not result.get("success"):
        _raise_api_error(404, "REQUEST_NOT_FOUND", "找不到對應的訂位。")
    return result


@router.post("/api/webhooks/booking-callback")
def booking_callback(body: dict):
    actor_id = body.get("actor_id")
    request_id = body.get("request_id")
    if not actor_id or not request_id:
        _raise_api_error(400, "INVALID_FORM_DATA", "缺少 actor_id 或 request_id。")

    order = reservation.get_reservation_order(actor_id, request_id)
    if not order:
        _raise_api_error(404, "REQUEST_NOT_FOUND", "找不到對應的訂位。")

    from ..services.store import STORE, now_iso

    order["status"] = body.get("status", order["status"])
    order["order_status"] = reservation.TEXT_TO_ORDER_STATUS.get(order["status"], order.get("order_status"))
    order["vendor_data"] = {
        "booking_id": body.get("booking_id"),
        "share_reservation_url": body.get("share_reservation_url"),
        "confirmed_at": now_iso(),
    }
    order.setdefault("status_history", []).append({"status": order["order_status"], "at": now_iso()})
    STORE.save_request(actor_id, order)
    return {"success": True}
