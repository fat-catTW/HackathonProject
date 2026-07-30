# backend/app/services/shop.py
"""Shop purchase order logic: cart validation, pricing, points, stock, fulfillment."""
from __future__ import annotations

import re
import secrets

from . import shop_catalog
from .store import STORE, now_iso

_PHONE_RE = re.compile(r"^09\d{8}\Z")

POINTS_TO_NT_RATE = 1  # 1 point = NT$1 discount
PHYSICAL_SHIPPING_FEE = 60

CANCELLABLE_STATUSES = ("SUBMITTED", "CONFIRMED")
STATUS_PROGRESSION = ("SUBMITTED", "CONFIRMED", "IN_PROGRESS", "COMPLETED")


def _error(code: str, message: str) -> dict:
    return {"success": False, "error": {"code": code, "message": message}}


def _validate_cart(cart) -> dict | None:
    if not isinstance(cart, list) or not cart:
        return _error("EMPTY_CART", "購物車不能是空的")
    for line in cart:
        if not isinstance(line, dict) or not line.get("sku_id"):
            return _error("INVALID_ITEM", "購物車項目缺少 sku_id")
        quantity = line.get("quantity")
        if not isinstance(quantity, int) or quantity <= 0:
            return _error("INVALID_ITEM", f"品項 {line.get('sku_id')} 的數量必須是正整數")
        if shop_catalog.get_sku(line["sku_id"]) is None:
            return _error("SKU_NOT_FOUND", f"找不到商品規格 {line['sku_id']}")
    return None


def _validate_payload(payload: dict) -> dict | None:
    cart_error = _validate_cart(payload.get("cart"))
    if cart_error:
        return cart_error
    cart = payload["cart"]

    contact_name = payload.get("contact_name")
    if not contact_name or not str(contact_name).strip():
        return _error("INVALID_CONTACT", "請填寫聯絡人姓名")

    phone = payload.get("phone")
    if not phone or not _PHONE_RE.match(str(phone)):
        return _error("INVALID_PHONE", "請填寫正確的手機號碼（09 開頭 10 碼）")

    used_points = payload.get("used_points", 0)
    if not isinstance(used_points, int) or used_points < 0:
        return _error("INVALID_POINTS", "折抵點數必須是不小於 0 的整數")

    has_physical = any(shop_catalog.get_sku(line["sku_id"])[0]["product_type"] == "PHYSICAL" for line in cart)
    if has_physical and not payload.get("address"):
        return _error("MISSING_ADDRESS", "購物車內含實體商品，請填寫收件地址")

    return None


def calculate_order_amounts(cart: list, used_points: int, shipping_fee: int = 0) -> dict:
    original_amount = 0
    for line in cart:
        _, sku = shop_catalog.get_sku(line["sku_id"])
        original_amount += sku["unit_price"] * line["quantity"]

    payable_before_points = original_amount + shipping_fee
    # Cap the discount so total_amount never goes negative.
    points_discount = min(max(used_points, 0), payable_before_points) * POINTS_TO_NT_RATE
    points_discount = min(points_discount, payable_before_points)
    total_amount = payable_before_points - points_discount

    return {
        "original_amount": original_amount,
        "shipping_fee_amount": shipping_fee,
        "points_discount": points_discount,
        "total_amount": total_amount,
    }


def calculate_points_earned(cart: list) -> int:
    total = 0
    for line in cart:
        _, sku = shop_catalog.get_sku(line["sku_id"])
        total += sku["unit_points"] * line["quantity"]
    return total


def create_shop_order(actor_id: str, payload: dict) -> dict:
    error = _validate_payload(payload)
    if error:
        return error

    cart = payload["cart"]
    used_points = payload.get("used_points", 0)
    has_physical = any(shop_catalog.get_sku(line["sku_id"])[0]["product_type"] == "PHYSICAL" for line in cart)
    shipping_fee = PHYSICAL_SHIPPING_FEE if has_physical else 0
    amounts = calculate_order_amounts(cart, used_points, shipping_fee)

    points_deducted = 0
    if amounts["points_discount"] > 0:
        # points_discount is expressed in NT$; at POINTS_TO_NT_RATE=1 the point cost equals it.
        points_to_deduct = amounts["points_discount"] // POINTS_TO_NT_RATE
        if not STORE.deduct_user_points(actor_id, points_to_deduct):
            return _error("INSUFFICIENT_POINTS", "點數餘額不足")
        points_deducted = points_to_deduct

    decremented: list[tuple[str, int]] = []
    for line in cart:
        if not STORE.decrement_sku_stock(line["sku_id"], line["quantity"]):
            for sku_id, quantity in decremented:
                STORE.restock_sku(sku_id, quantity)
            if points_deducted:
                STORE.refund_user_points(actor_id, points_deducted)
            return _error("OUT_OF_STOCK", f"商品規格「{line['sku_id']}」庫存不足")
        decremented.append((line["sku_id"], line["quantity"]))

    points_earned = calculate_points_earned(cart)
    STORE.refund_user_points(actor_id, points_earned)  # "refund" doubles as "credit new points"

    redemption_codes: dict[str, list[str]] = {}
    for line in cart:
        product, _sku = shop_catalog.get_sku(line["sku_id"])
        if product["product_type"] == "SERIAL_CODE":
            redemption_codes[line["sku_id"]] = [secrets.token_hex(4).upper() for _ in range(line["quantity"])]

    request_id = STORE.next_request_id()
    order_status = "COMPLETED" if not has_physical else "SUBMITTED"
    order_type = "07" if not has_physical else "10"

    order = {
        "request_id": request_id,
        "service_id": "shop_purchase",
        "service_name": "商城購物",
        "order_type": order_type,
        "status": order_status,
        "form_data": {
            "cart": cart,
            "contact_name": payload["contact_name"],
            "phone": payload["phone"],
            "address": payload.get("address"),
            "used_points": used_points,
        },
        "original_amount": amounts["original_amount"],
        "shipping_fee_amount": amounts["shipping_fee_amount"],
        "points_discount": amounts["points_discount"],
        "total_amount": amounts["total_amount"],
        "points_earned": points_earned,
        "redemption_codes": redemption_codes,
        "status_history": [{"status": order_status, "at": now_iso()}],
        "created_at": now_iso(),
    }

    try:
        STORE.save_request(actor_id, order)
    except Exception:
        for sku_id, quantity in decremented:
            STORE.restock_sku(sku_id, quantity)
        STORE.deduct_user_points(actor_id, points_earned)
        if points_deducted:
            STORE.refund_user_points(actor_id, points_deducted)
        return _error("ORDER_SAVE_FAILED", "訂單建立失敗，請稍後再試")

    return {
        "success": True,
        "request_id": request_id,
        "status": order_status,
        "total_amount": amounts["total_amount"],
        "points_earned": points_earned,
        "redemption_codes": redemption_codes,
    }


def get_shop_order(actor_id: str, request_id: str) -> dict | None:
    return STORE.get_request(actor_id, request_id)


def cancel_shop_order(actor_id: str, request_id: str, reason: str = "USER_CANCEL") -> dict:
    order = STORE.get_request(actor_id, request_id)
    if not order:
        return _error("REQUEST_NOT_FOUND", "找不到這筆訂單")
    if order.get("status") not in CANCELLABLE_STATUSES:
        return _error("CANCEL_NOT_ALLOWED", "目前狀態無法取消訂單")

    for line in order["form_data"]["cart"]:
        STORE.restock_sku(line["sku_id"], line["quantity"])

    points_discount = order.get("points_discount", 0)
    if points_discount:
        STORE.refund_user_points(actor_id, points_discount // POINTS_TO_NT_RATE)

    order["status"] = "CANCELLED"
    order["cancel_reason"] = reason
    order["status_history"].append({"status": "CANCELLED", "at": now_iso()})
    STORE.save_request(actor_id, order)
    return {"success": True, "status": "CANCELLED"}


def advance_shop_order_status(actor_id: str, request_id: str) -> dict:
    """Demo-only: advance a physical-product order to the next status."""
    order = STORE.get_request(actor_id, request_id)
    if not order:
        return _error("REQUEST_NOT_FOUND", "找不到這筆訂單")
    current = order.get("status")
    if current not in STATUS_PROGRESSION or current == STATUS_PROGRESSION[-1]:
        return _error("STATUS_ADVANCE_NOT_ALLOWED", "目前狀態無法再往下推進")
    next_status = STATUS_PROGRESSION[STATUS_PROGRESSION.index(current) + 1]
    order["status"] = next_status
    order["status_history"].append({"status": next_status, "at": now_iso()})
    STORE.save_request(actor_id, order)
    return {"success": True, "status": next_status}
