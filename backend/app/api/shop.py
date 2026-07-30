"""REST endpoints for the shop_purchase (M10) service."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..auth.cognito import CurrentUser, get_current_user
from ..services import shop, shop_catalog
from ..services.store import STORE

router = APIRouter()


def _raise_api_error(status_code: int, code: str, message: str) -> None:
    raise HTTPException(status_code=status_code, detail={"success": False, "error": {"code": code, "message": message}})


@router.get("/api/shop/stores")
def list_shop_stores() -> dict:
    return {"stores": shop_catalog.list_stores()}


@router.get("/api/shop/products")
def list_shop_products(store_id: str | None = None) -> dict:
    return {"products": shop_catalog.list_products(store_id)}


@router.get("/api/shop/products/{product_id}")
def get_shop_product(product_id: str) -> dict:
    product = shop_catalog.get_product(product_id)
    if not product:
        _raise_api_error(404, "PRODUCT_NOT_FOUND", "找不到這項商品")
    return product


@router.get("/api/shop/points")
def get_my_shop_points(user: CurrentUser = Depends(get_current_user)) -> dict:
    return {"balance": STORE.get_user_points(user.sub)}


@router.post("/api/shop/submit")
def submit_shop_order(payload: dict, user: CurrentUser = Depends(get_current_user)) -> dict:
    result = shop.create_shop_order(user.sub, payload)
    if not result.get("success"):
        _raise_api_error(400, result["error"]["code"], result["error"]["message"])
    return result


@router.get("/api/shop/orders/{request_id}")
def get_shop_order(request_id: str, user: CurrentUser = Depends(get_current_user)) -> dict:
    order = shop.get_shop_order(user.sub, request_id)
    if not order:
        _raise_api_error(404, "REQUEST_NOT_FOUND", "找不到這筆訂單")
    return order


@router.post("/api/shop/orders/{request_id}/cancel")
def cancel_shop_order(request_id: str, body: dict | None = None, user: CurrentUser = Depends(get_current_user)) -> dict:
    reason = (body or {}).get("reason", "USER_CANCEL")
    result = shop.cancel_shop_order(user.sub, request_id, reason)
    if not result.get("success"):
        code = result["error"]["code"]
        _raise_api_error(404 if code == "REQUEST_NOT_FOUND" else 409, code, result["error"]["message"])
    return result


@router.post("/api/shop/orders/{request_id}/simulate")
def simulate_shop_order_progress(request_id: str, user: CurrentUser = Depends(get_current_user)) -> dict:
    """Demo-only: advance a physical-product order to its next status."""
    result = shop.advance_shop_order_status(user.sub, request_id)
    if not result.get("success"):
        code = result["error"]["code"]
        _raise_api_error(404 if code == "REQUEST_NOT_FOUND" else 409, code, result["error"]["message"])
    return result
