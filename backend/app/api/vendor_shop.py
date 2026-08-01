"""廠商後台：商城實體商品訂單清單與出貨推進（vendor_id 40，商城出貨中心）。

商城橫跨多間合作店家，但沿用既有「一個服務線一個廠商帳號」的慣例（跟餐廳訂位、
美食外送一樣），由單一出貨中心帳號集中處理所有實體商品訂單的出貨，不依店家拆單。

聯絡人姓名／電話是 form_data 的頂層字串欄位，跟其他服務走同一套
contact_privacy 加密與遮罩機制（見 app.services.store._for_storage）；但收件
地址是巢狀物件，那套機制只認得頂層字串，套上去只會把整包地址蓋成一個遮罩
字串，所以地址欄位另外算「只留到城市」的遮罩，不透過 contact_privacy。完整
內容一律走 POST /{request_id}/contact，比照 app.api.vendor 留下存取紀錄。
"""
from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import BaseModel, Field

from ..auth.cognito import CurrentUser, get_current_vendor
from ..services import contact_privacy, shop
from ..services.store import STORE, version_of

router = APIRouter(prefix="/api/vendor/shop-orders")

_PENDING_STATUSES = ("SUBMITTED",)
_ORDER_STATUSES = ("CONFIRMED", "IN_PROGRESS", "COMPLETED")
_CLOSED_STATUSES = ("CANCELLED",)
_VISIBLE_STATUSES = frozenset(_PENDING_STATUSES + _ORDER_STATUSES + _CLOSED_STATUSES)

_SCOPES = {
    "pending": frozenset(_PENDING_STATUSES),
    "orders": frozenset(_ORDER_STATUSES),
    "all": _VISIBLE_STATUSES,
}

_ACTION_LABELS = {"confirm": "確認訂單", "ship": "出貨", "deliver": "送達", "reject": "無法出貨"}
_CONTACT_FIELD_LABELS = {"contact_name": "聯絡人", "phone": "聯絡電話", "address": "收件地址"}


def _fail(status: int, code: str, message: str, extra: dict | None = None) -> HTTPException:
    return HTTPException(
        status_code=status,
        detail={"success": False, "error": {"code": code, "message": message} | (extra or {})},
    )


def _available_actions(status: str) -> list[str]:
    actions = [name for name, (source, _) in shop.SHOP_VENDOR_TRANSITIONS.items() if source == status]
    if status == "SUBMITTED":
        actions.append("reject")
    return actions


def _goods_summary(cart: list) -> str:
    return "、".join(f"{line['sku_id']} x{line['quantity']}" for line in cart)


def _masked_form(item: dict) -> dict:
    """聯絡人姓名／電話交給 contact_privacy 原本的遮罩；地址是巢狀物件，那套
    機制套上去只會把整包地址蓋成一個「***」字串，所以另外算一個只留城市的
    摘要，不透過 mask_for_display。
    """
    form_data = item.get("form_data") or {}
    masked = contact_privacy.mask_for_display(form_data, item.get("form_data_masked") or {})
    raw_address = form_data.get("address") or {}
    masked["address_city"] = raw_address.get("city", "")
    return masked


def _to_list_item(item: dict) -> dict:
    status = item.get("status", "")
    masked = _masked_form(item)
    return {
        "request_id": item["request_id"],
        "service_id": "shop_purchase",
        "service_name": item.get("service_name", "商城購物"),
        "status": status,
        "status_label": shop.STATUS_LABELS.get(status, status),
        "customer_name": masked.get("contact_name", ""),
        "summary": _goods_summary((item.get("form_data") or {}).get("cart") or []),
        "version": version_of(item),
        "available_actions": _available_actions(status),
        "created_at": item.get("created_at", ""),
        "updated_at": item.get("updated_at", ""),
    }


def _load_order_or_404(vendor_id: int, request_id: str) -> tuple[str, dict]:
    index = STORE.get_vendor_request(vendor_id, request_id)
    owner_id = str((index or {}).get("owner_id") or "")
    # get_stored_request 而非 get_request：比照 vendor.py 的既有慣例。商城的聯絡人
    # 姓名／電話是真的密文（跟外送訂單不同，外送的巢狀地址從沒被加密過），這裡選
    # 錯函式就會在廠商端點內多一份不必要的明文，即使目前的遮罩／解密流程能兜得住。
    order = STORE.get_stored_request(owner_id, request_id) if owner_id else None
    if not order or order.get("service_id") != "shop_purchase" or order.get("status") not in _VISIBLE_STATUSES:
        raise _fail(404, "REQUEST_NOT_FOUND", "找不到對應的訂單。")
    return owner_id, order


def _to_fields(order: dict) -> list[dict]:
    masked = _masked_form(order)
    rows = [
        {
            "id": "cart",
            "label": "商品",
            "value": _goods_summary((order.get("form_data") or {}).get("cart") or []),
            "masked": False,
        },
        {"id": "contact_name", "label": "聯絡人", "value": masked.get("contact_name", ""), "masked": True},
        {"id": "phone", "label": "聯絡電話", "value": masked.get("phone", ""), "masked": True},
    ]
    if masked.get("address_city"):
        rows.append({"id": "address", "label": "收件地址", "value": masked["address_city"], "masked": True})
    return [row for row in rows if row["value"]]


def _access_log(request_id: str, vendor_id: int) -> list[dict]:
    return [
        {
            "at": entry.get("at", ""),
            "viewer_name": entry.get("vendor_name", ""),
            "fields": [_CONTACT_FIELD_LABELS.get(f, f) for f in entry.get("fields", [])],
        }
        for entry in STORE.list_contact_access(request_id, vendor_id)
    ]


def _detail_payload(order: dict, vendor_id: int) -> dict:
    status = order.get("status", "")
    fields = _to_fields(order)
    return {
        "request_id": order["request_id"],
        "service_id": "shop_purchase",
        "service_name": order.get("service_name", "商城購物"),
        "status": status,
        "status_label": shop.STATUS_LABELS.get(status, status),
        "customer_name": _masked_form(order).get("contact_name", ""),
        "version": version_of(order),
        "available_actions": _available_actions(status),
        "fields": fields,
        "has_contact": any(field["masked"] for field in fields),
        "contact_access_log": _access_log(order["request_id"], vendor_id),
        "created_at": order.get("created_at", ""),
        "updated_at": order.get("updated_at", ""),
    }


class VendorShopActionIn(BaseModel):
    version: int = Field(..., ge=0)


@router.get("")
def list_vendor_shop_orders(scope: str = "all", vendor: CurrentUser = Depends(get_current_vendor)):
    if scope not in _SCOPES:
        raise _fail(422, "INVALID_SCOPE", "scope 參數不合法。")
    stored = STORE.list_vendor_requests(vendor.vendor_id)
    items = [_to_list_item(i) for i in stored if i.get("status") in _SCOPES[scope]]
    counts = {name: sum(1 for i in stored if i.get("status") in statuses) for name, statuses in _SCOPES.items()}
    return {"items": items, "counts": counts}


@router.get("/{request_id}")
def get_vendor_shop_order(request_id: str, vendor: CurrentUser = Depends(get_current_vendor)):
    _, order = _load_order_or_404(vendor.vendor_id, request_id)
    return _detail_payload(order, vendor.vendor_id)


# 這條要排在 /{action} 前面：路徑樣板一樣，FastAPI 依宣告順序比對，排在後面的話
# "contact" 會先被當成 action 而卡在 422（比照 vendor.py 的既有寫法）。
@router.post("/{request_id}/contact")
def reveal_vendor_shop_contact(request_id: str, vendor: CurrentUser = Depends(get_current_vendor)):
    """顯示完整聯絡資訊，並留下一筆存取紀錄——跟 vendor.py 的 /contact 端點同一套稽核規則。"""
    owner_id, order = _load_order_or_404(vendor.vendor_id, request_id)
    plain = contact_privacy.decrypt_form_data(order.get("form_data") or {})
    address = plain.get("address") or {}

    def _value(key: str) -> str:
        value = plain.get(key)
        if contact_privacy.is_encrypted(value):
            return "（無法解密）"
        return str(value or "")

    contact = [
        {"id": "contact_name", "label": "聯絡人", "value": _value("contact_name")},
        {"id": "phone", "label": "聯絡電話", "value": _value("phone")},
        {
            "id": "address",
            "label": "收件地址",
            "value": f"{address.get('city', '')}{address.get('street', '')}",
        },
    ]
    contact = [item for item in contact if item["value"]]
    if not contact:
        raise _fail(404, "CONTACT_NOT_FOUND", "這筆訂單沒有聯絡資訊。")

    try:
        STORE.log_contact_access(
            request_id,
            {
                "vendor_id": vendor.vendor_id,
                "vendor_name": vendor.name,
                "owner_id": owner_id,
                "fields": [item["id"] for item in contact],
            },
        )
    except Exception:  # noqa: BLE001
        raise _fail(503, "CONTACT_LOG_UNAVAILABLE", "無法寫入存取紀錄，請稍後再試。")

    return {
        "success": True,
        "request_id": request_id,
        "contact": contact,
        "contact_access_log": _access_log(request_id, vendor.vendor_id),
    }


@router.post("/{request_id}/{action}")
def act_on_vendor_shop_order(
    body: VendorShopActionIn,
    request_id: str,
    action: str = Path(pattern="^(confirm|ship|deliver|reject)$"),
    vendor: CurrentUser = Depends(get_current_vendor),
):
    owner_id, order = _load_order_or_404(vendor.vendor_id, request_id)
    status = order.get("status", "")

    if action == "reject":
        if status != "SUBMITTED":
            raise _fail(
                409,
                "REQUEST_STATUS_CONFLICT",
                f"訂單目前是「{shop.STATUS_LABELS.get(status, status)}」，無法{_ACTION_LABELS[action]}。",
                _detail_payload(order, vendor.vendor_id),
            )
        result = shop.cancel_shop_order(owner_id, request_id, reason="VENDOR_CANCEL", expected_version=body.version)
    else:
        source, _target = shop.SHOP_VENDOR_TRANSITIONS[action]
        if status != source:
            raise _fail(
                409,
                "REQUEST_STATUS_CONFLICT",
                f"訂單目前是「{shop.STATUS_LABELS.get(status, status)}」，無法{_ACTION_LABELS[action]}。",
                _detail_payload(order, vendor.vendor_id),
            )
        result = shop.advance_shop_order_for_vendor(owner_id, request_id, action, body.version)

    if not result.get("success"):
        code = result["error"]["code"]
        _, current = _load_order_or_404(vendor.vendor_id, request_id)
        raise _fail(409, code, result["error"]["message"], _detail_payload(current, vendor.vendor_id))

    _, updated = _load_order_or_404(vendor.vendor_id, request_id)
    return {"success": True, **_detail_payload(updated, vendor.vendor_id)}
