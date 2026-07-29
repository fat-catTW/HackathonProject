"""Delivery ordering service."""
from __future__ import annotations

import re

from .store import STORE, now_iso

# --- 第三方 vendor 狀態碼 → 本平台 order_status 映射表 ---
VENDOR_STATUS_MAP: dict[int, str] = {
    0: "01",   # 待接單
    1: "02",   # 商家已接單
    2: "03",   # 備餐中
    3: "04",   # 外送員已取餐
    4: "05",   # 配送中
    5: "70",   # 已送達
    9: "90",   # 已取消
}

# 本平台狀態碼 → 文字描述
ORDER_STATUS_LABEL: dict[str, str] = {
    "01": "待接單",
    "02": "商家已接單",
    "03": "備餐中",
    "04": "外送員已取餐",
    "05": "配送中",
    "70": "已送達",
    "90": "已取消",
}

_PHONE_RE = re.compile(r"^09\d{8}\Z")

# --- 簡易外送範圍判斷（圓心＋半徑） ---
_SERVICE_CENTER = (25.033, 121.565)  # 台北市中心示意
_SERVICE_RADIUS_KM = 10.0


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Simple haversine distance in km."""
    import math
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def _error(code: str, message: str) -> dict:
    return {"success": False, "error": {"code": code, "message": message}}


def _validate_address(address: dict) -> dict | None:
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
    # 檢查外送範圍
    dist = _haversine_km(_SERVICE_CENTER[0], _SERVICE_CENTER[1], lat, lng)
    if dist > _SERVICE_RADIUS_KM:
        return _error("OUT_OF_RANGE", "該地址暫不提供外送服務，請確認外送範圍。")
    if not address.get("city") and not address.get("street"):
        return _error("INVALID_ADDRESS", "請填寫外送地址的市區或街道資訊。")
    if not address.get("contact_name"):
        return _error("INVALID_CONTACT", "請填寫收件人姓名。")
    return None


def _validate_goods(goods: list) -> dict | None:
    if not goods or not isinstance(goods, list):
        return _error("EMPTY_CART", "購物車不可為空，請至少選擇一項品項。")
    for idx, item in enumerate(goods):
        if not item.get("id"):
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


def _validate_payload(payload: dict) -> dict | None:
    address = payload.get("address")
    if not address or not isinstance(address, dict):
        return _error("INVALID_ADDRESS", "外送地址為必填。")
    addr_err = _validate_address(address)
    if addr_err:
        return addr_err

    goods = payload.get("goods")
    goods_err = _validate_goods(goods)
    if goods_err:
        return goods_err

    if not payload.get("store_id"):
        return _error("MISSING_STORE", "請選擇外送店家。")

    phone = address.get("phone", "")
    if phone and not _PHONE_RE.match(phone):
        return _error("INVALID_PHONE", "請輸入正確的手機號碼格式（09 開頭，共 10 碼）。")

    return None


def calculate_order_amounts(goods: list, shipping_fee: float = 0) -> dict:
    """Calculate order totals."""
    original_amount = sum(item.get("price", 0) * item.get("quantity", 1) for item in goods)
    return {
        "original_amount": original_amount,
        "shipping_fee_amount": shipping_fee,
        "total_amount": original_amount + shipping_fee,
    }


def create_delivery_order(actor_id: str, payload: dict) -> dict:
    """Create a new delivery order (order_type=06)."""
    validation_error = _validate_payload(payload)
    if validation_error:
        return validation_error

    address = payload["address"]
    goods = payload["goods"]
    store_id = payload["store_id"]
    store_name = payload.get("store_name", "")
    store_address = payload.get("store_address", "")
    note = payload.get("note", "")
    store_url = payload.get("store_url", "")

    # 計算金額
    shipping_fee = float(payload.get("shipping_fee", 60))
    amounts = calculate_order_amounts(goods, shipping_fee)

    order_items = {
        "user": {"address": address},
        "goods": goods,
        "store": {
            "id": store_id,
            "name": store_name,
            "address": store_address,
            "url": store_url,
        },
        "note": note,
    }

    request_id = STORE.next_request_id()
    created_at = now_iso()

    order = {
        "request_id": request_id,
        "session_id": None,
        "service_id": "food_delivery",
        "service_name": "美食外送",
        "order_type": "06",
        "order_items": order_items,
        "original_amount": amounts["original_amount"],
        "shipping_fee_amount": amounts["shipping_fee_amount"],
        "total_amount": amounts["total_amount"],
        "status": "PENDING",
        "order_status": "01",
        "vendor_data": {"delivery": None, "order_status": None},
        "cancel_reason": None,
        "form_data": {
            "address": address,
            "goods": goods,
            "store_id": store_id,
            "store_name": store_name,
            "note": note,
        },
        "status_history": [{"status": "01", "at": created_at}],
        "created_at": created_at,
    }

    try:
        STORE.save_request(actor_id, order)
    except Exception as exc:
        return _error("ORDER_SAVE_FAILED", str(exc))

    return {
        "success": True,
        "request_id": request_id,
        "order_status": "01",
        "total_amount": amounts["total_amount"],
    }


def get_delivery_order(actor_id: str, request_id: str) -> dict | None:
    """Get delivery order by request_id."""
    return STORE.get_request(actor_id, request_id)


def cancel_delivery_order(actor_id: str, request_id: str, reason: str = "USER_CANCEL") -> dict:
    """Cancel a delivery order with reason classification."""
    order = STORE.get_request(actor_id, request_id)
    if not order:
        return _error("REQUEST_NOT_FOUND", "找不到對應的外送訂單。")

    current_status = order.get("order_status", "01")

    # 已出餐或已派單後不可由使用者取消
    if current_status in ("04", "05", "70"):
        return _error("CANCEL_NOT_ALLOWED", "外送員已取餐或配送中，無法取消訂單。請聯繫客服處理。")

    order["status"] = "CANCELLED"
    order["order_status"] = "90"
    order["cancel_reason"] = reason  # USER_CANCEL / STORE_CANCEL / SYSTEM_CANCEL
    order.setdefault("status_history", []).append({"status": "90", "at": now_iso()})
    STORE.save_request(actor_id, order)
    return {"success": True, "request_id": request_id, "status": "CANCELLED"}


def update_delivery_status_from_vendor(actor_id: str, request_id: str, vendor_status: int, delivery_info: dict | None = None) -> dict:
    """
    Webhook callback: update order from vendor status code.
    Maps vendor_data.order_status to platform order_status using VENDOR_STATUS_MAP.
    """
    order = STORE.get_request(actor_id, request_id)
    if not order:
        return _error("REQUEST_NOT_FOUND", "找不到對應的外送訂單。")

    platform_status = VENDOR_STATUS_MAP.get(vendor_status)
    if not platform_status:
        return _error("INVALID_VENDOR_STATUS", f"未知的第三方狀態碼: {vendor_status}")

    order["order_status"] = platform_status
    order["vendor_data"]["order_status"] = vendor_status

    if delivery_info:
        order["vendor_data"]["delivery"] = delivery_info

    if platform_status == "70":
        order["status"] = "COMPLETED"
    elif platform_status == "90":
        order["status"] = "CANCELLED"
        order["cancel_reason"] = "STORE_CANCEL"
    else:
        order["status"] = "IN_PROGRESS"

    order.setdefault("status_history", []).append({"status": platform_status, "at": now_iso()})
    STORE.save_request(actor_id, order)

    return {
        "success": True,
        "request_id": request_id,
        "order_status": platform_status,
        "order_status_label": ORDER_STATUS_LABEL.get(platform_status, ""),
    }
