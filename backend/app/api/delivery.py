"""Delivery ordering API endpoints."""
from fastapi import APIRouter, Depends, HTTPException

from ..auth.cognito import CurrentUser, get_current_user
from ..services import delivery

router = APIRouter()


def _raise_api_error(status_code: int, code: str, message: str):
    raise HTTPException(status_code=status_code, detail={"success": False, "error": {"code": code, "message": message}})


# --- 簡易店家清單（暫無串接外部菜單系統，先以靜態資料呈現） ---
DELIVERY_STORES: list[dict] = [
    {
        "id": "store-001",
        "name": "好味道便當",
        "address": "台北市大安區忠孝東路四段100號",
        "cuisine": "便當",
        "image": None,
        "url": "",
        "menu": [
            {"id": "item-001", "title": "招牌雞腿便當", "price": 110, "modifier_group": [
                {"name": "加購", "options": [{"label": "加蛋", "price": 15}, {"label": "加滷肉", "price": 20}]}
            ]},
            {"id": "item-002", "title": "排骨便當", "price": 100, "modifier_group": [
                {"name": "加購", "options": [{"label": "加蛋", "price": 15}]}
            ]},
            {"id": "item-003", "title": "素食便當", "price": 90, "modifier_group": []},
        ],
    },
    {
        "id": "store-002",
        "name": "鮮茶道",
        "address": "台北市信義區松仁路28號",
        "cuisine": "飲料",
        "image": None,
        "url": "",
        "menu": [
            {"id": "item-010", "title": "珍珠奶茶（大）", "price": 65, "modifier_group": [
                {"name": "甜度", "options": [{"label": "全糖", "price": 0}, {"label": "半糖", "price": 0}, {"label": "無糖", "price": 0}]},
                {"name": "冰量", "options": [{"label": "正常冰", "price": 0}, {"label": "少冰", "price": 0}, {"label": "去冰", "price": 0}]},
            ]},
            {"id": "item-011", "title": "四季春茶（大）", "price": 40, "modifier_group": [
                {"name": "甜度", "options": [{"label": "全糖", "price": 0}, {"label": "半糖", "price": 0}, {"label": "無糖", "price": 0}]},
            ]},
            {"id": "item-012", "title": "冬瓜檸檬", "price": 55, "modifier_group": []},
        ],
    },
    {
        "id": "store-003",
        "name": "義式小館",
        "address": "台北市中山區南京東路二段50號",
        "cuisine": "義式料理",
        "image": None,
        "url": "",
        "menu": [
            {"id": "item-020", "title": "奶油培根義大利麵", "price": 180, "modifier_group": [
                {"name": "加購", "options": [{"label": "升級套餐（含湯＋飲料）", "price": 69}]}
            ]},
            {"id": "item-021", "title": "瑪格麗特披薩", "price": 220, "modifier_group": []},
            {"id": "item-022", "title": "凱薩沙拉", "price": 120, "modifier_group": []},
        ],
    },
]


@router.get("/api/delivery/stores")
def list_delivery_stores(user: CurrentUser = Depends(get_current_user)):
    """列出可外送的店家（不含完整菜單）。"""
    stores = [
        {"id": s["id"], "name": s["name"], "address": s["address"], "cuisine": s["cuisine"], "image": s["image"]}
        for s in DELIVERY_STORES
    ]
    return {"stores": stores}


@router.get("/api/delivery/stores/{store_id}")
def get_delivery_store(store_id: str, user: CurrentUser = Depends(get_current_user)):
    """取得單一店家含菜單。"""
    store = next((s for s in DELIVERY_STORES if s["id"] == store_id), None)
    if not store:
        _raise_api_error(404, "STORE_NOT_FOUND", "找不到指定的外送店家。")
    return store


@router.post("/api/delivery/submit")
def submit_delivery_order(payload: dict, user: CurrentUser = Depends(get_current_user)):
    """送出外送訂單。"""
    result = delivery.create_delivery_order(user.sub, payload)
    if not result.get("success"):
        error = result.get("error", {})
        code = error.get("code", "DELIVERY_FAILED")
        status_code = 400
        if code == "OUT_OF_RANGE":
            status_code = 422
        _raise_api_error(status_code, code, error.get("message", "外送訂單建立失敗"))
    return result


@router.get("/api/delivery/orders/{request_id}")
def get_delivery_order(request_id: str, user: CurrentUser = Depends(get_current_user)):
    """取得外送訂單詳情（含即時進度）。"""
    order = delivery.get_delivery_order(user.sub, request_id)
    if not order:
        _raise_api_error(404, "REQUEST_NOT_FOUND", "找不到對應的外送訂單。")
    # 補充狀態文字
    order["order_status_label"] = delivery.ORDER_STATUS_LABEL.get(order.get("order_status", ""), "")
    return order


@router.post("/api/delivery/orders/{request_id}/cancel")
def cancel_delivery_order(request_id: str, body: dict = None, user: CurrentUser = Depends(get_current_user)):
    """使用者取消外送訂單。"""
    reason = (body or {}).get("reason", "USER_CANCEL")
    result = delivery.cancel_delivery_order(user.sub, request_id, reason)
    if not result.get("success"):
        error = result.get("error", {})
        code = error.get("code", "CANCEL_FAILED")
        status_code = 404 if code == "REQUEST_NOT_FOUND" else 409
        _raise_api_error(status_code, code, error.get("message", "取消失敗"))
    return result


@router.post("/api/webhooks/delivery-callback")
def delivery_webhook(body: dict):
    """第三方外送系統回呼：更新訂單狀態與外送員資訊。"""
    actor_id = body.get("actor_id")
    request_id = body.get("request_id")
    vendor_status = body.get("vendor_status")

    if not actor_id or not request_id or vendor_status is None:
        _raise_api_error(400, "INVALID_CALLBACK", "缺少 actor_id、request_id 或 vendor_status。")

    delivery_info = body.get("delivery")  # e.g. {"driver_name": "...", "driver_phone": "...", "eta_minutes": 15}

    result = delivery.update_delivery_status_from_vendor(actor_id, request_id, int(vendor_status), delivery_info)
    if not result.get("success"):
        error = result.get("error", {})
        _raise_api_error(400, error.get("code", "UPDATE_FAILED"), error.get("message", "狀態更新失敗"))
    return result
