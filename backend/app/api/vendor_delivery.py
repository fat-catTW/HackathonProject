"""廠商後台：美食外送訂單清單與狀態推進（vendor_id 30，唯一的外送物流廠商帳號）。

跟通用案件（vendor.py）共用同一套廠商驗證與 VENDOR# 索引查詢機制，但外送訂單的
狀態欄位形狀不一樣——粗粒度 status（PENDING／IN_PROGRESS／COMPLETED／CANCELLED）
決定廠商後台分頁，細粒度 order_status（01～90 兩位數代碼）決定廠商當下能按哪個
動作，兩者不是同一回事，所以另外開一份轉換規則，不硬塞進 vendor.py 的
VENDOR_TRANSITIONS。
"""
from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import BaseModel, Field

from ..auth.cognito import CurrentUser, get_current_vendor
from ..services import delivery
from ..services.delivery import ORDER_STATUS_LABEL
from ..services.store import STORE, version_of

router = APIRouter(prefix="/api/vendor/delivery-orders")

_PENDING_STATUSES = ("PENDING",)
_ORDER_STATUSES = ("IN_PROGRESS", "COMPLETED")
_CLOSED_STATUSES = ("CANCELLED",)
_VISIBLE_STATUSES = frozenset(_PENDING_STATUSES + _ORDER_STATUSES + _CLOSED_STATUSES)

_SCOPES = {
    "pending": frozenset(_PENDING_STATUSES),
    "orders": frozenset(_ORDER_STATUSES),
    "all": _VISIBLE_STATUSES,
}

# 動作 → (要求的來源 order_status 代碼, 要送給 apply_vendor_status 的 vendor_status 數字)。
_PROGRESS_ACTIONS: dict[str, tuple[str, int]] = {
    "accept": ("01", 1),
    "prepare": ("02", 2),
    "pickup": ("03", 3),
    "dispatch": ("04", 4),
    "deliver": ("05", 5),
}
_ACTION_LABELS = {
    "accept": "商家已接單",
    "prepare": "開始備餐",
    "pickup": "外送員已取餐",
    "dispatch": "開始配送",
    "deliver": "已送達",
    "reject": "無法接單",
}
# reject 只能在正式出餐前喊停；已經被外送員取走就不能再拒。
_REJECTABLE_ORDER_STATUSES = frozenset({"01", "02", "03"})
_REJECT_VENDOR_STATUS = 9


def _fail(status: int, code: str, message: str, extra: dict | None = None) -> HTTPException:
    return HTTPException(
        status_code=status,
        detail={"success": False, "error": {"code": code, "message": message} | (extra or {})},
    )


def _available_actions(order_status: str) -> list[str]:
    actions = [name for name, (source, _) in _PROGRESS_ACTIONS.items() if source == order_status]
    if order_status in _REJECTABLE_ORDER_STATUSES:
        actions.append("reject")
    return actions


def _to_list_item(item: dict) -> dict:
    order_status = item.get("order_status") or ""
    form_data = item.get("form_data") or {}
    address = form_data.get("address") or {}
    return {
        "request_id": item["request_id"],
        "service_id": "food_delivery",
        "service_name": item.get("service_name", "美食外送"),
        "status": item.get("status", ""),
        "status_label": ORDER_STATUS_LABEL.get(order_status, item.get("status", "")),
        "customer_name": address.get("contact_name", ""),
        "summary": form_data.get("store_name", ""),
        "version": version_of(item),
        "available_actions": _available_actions(order_status),
        "created_at": item.get("created_at", ""),
        "updated_at": item.get("updated_at", ""),
    }


def _load_order_or_404(vendor_id: int, request_id: str) -> tuple[str, dict]:
    index = STORE.get_vendor_request(vendor_id, request_id)
    owner_id = str((index or {}).get("owner_id") or "")
    order = STORE.get_request(owner_id, request_id) if owner_id else None
    if not order or order.get("service_id") != "food_delivery" or order.get("status") not in _VISIBLE_STATUSES:
        raise _fail(404, "REQUEST_NOT_FOUND", "找不到對應的外送訂單。")
    return owner_id, order


def _to_fields(order: dict) -> list[dict]:
    form_data = order.get("form_data") or {}
    address = form_data.get("address") or {}
    goods = form_data.get("goods") or []
    goods_summary = "、".join(f"{g.get('title', '')} x{g.get('quantity', 1)}" for g in goods)
    rows = [
        {"id": "store_name", "label": "店家", "value": form_data.get("store_name", "")},
        {"id": "goods", "label": "餐點", "value": goods_summary},
        {"id": "contact_name", "label": "收件人", "value": address.get("contact_name", "")},
        {"id": "phone", "label": "聯絡電話", "value": address.get("phone", "") or ""},
        {
            "id": "address",
            "label": "外送地址",
            "value": f"{address.get('city', '')}{address.get('area', '')}{address.get('street', '')}",
        },
    ]
    if form_data.get("note"):
        rows.append({"id": "note", "label": "備註", "value": form_data["note"]})
    return [row for row in rows if row["value"]]


def _detail_payload(order: dict) -> dict:
    order_status = order.get("order_status") or ""
    return {
        "request_id": order["request_id"],
        "service_id": "food_delivery",
        "service_name": order.get("service_name", "美食外送"),
        "status": order.get("status", ""),
        "status_label": ORDER_STATUS_LABEL.get(order_status, order.get("status", "")),
        "customer_name": ((order.get("form_data") or {}).get("address") or {}).get("contact_name", ""),
        "version": version_of(order),
        "available_actions": _available_actions(order_status),
        "fields": _to_fields(order),
        "created_at": order.get("created_at", ""),
        "updated_at": order.get("updated_at", ""),
    }


class VendorDeliveryActionIn(BaseModel):
    version: int = Field(..., ge=0)


@router.get("")
def list_vendor_delivery_orders(scope: str = "all", vendor: CurrentUser = Depends(get_current_vendor)):
    if scope not in _SCOPES:
        raise _fail(422, "INVALID_SCOPE", "scope 參數不合法。")
    stored = STORE.list_vendor_requests(vendor.vendor_id)
    items = [_to_list_item(i) for i in stored if i.get("status") in _SCOPES[scope]]
    counts = {name: sum(1 for i in stored if i.get("status") in statuses) for name, statuses in _SCOPES.items()}
    return {"items": items, "counts": counts}


@router.get("/{request_id}")
def get_vendor_delivery_order(request_id: str, vendor: CurrentUser = Depends(get_current_vendor)):
    _, order = _load_order_or_404(vendor.vendor_id, request_id)
    return _detail_payload(order)


@router.post("/{request_id}/{action}")
def act_on_vendor_delivery_order(
    body: VendorDeliveryActionIn,
    request_id: str,
    action: str = Path(pattern="^(accept|prepare|pickup|dispatch|deliver|reject)$"),
    vendor: CurrentUser = Depends(get_current_vendor),
):
    owner_id, order = _load_order_or_404(vendor.vendor_id, request_id)
    current_order_status = order.get("order_status") or ""

    if action == "reject":
        eligible = current_order_status in _REJECTABLE_ORDER_STATUSES
        vendor_status = _REJECT_VENDOR_STATUS
    else:
        source, vendor_status = _PROGRESS_ACTIONS[action]
        eligible = current_order_status == source

    if not eligible:
        raise _fail(
            409,
            "REQUEST_STATUS_CONFLICT",
            f"訂單目前是「{ORDER_STATUS_LABEL.get(current_order_status, current_order_status)}」，無法{_ACTION_LABELS[action]}。",
            _detail_payload(order),
        )

    updated = delivery.apply_vendor_status(order, vendor_status)
    if updated is None:
        raise _fail(400, "INVALID_ACTION", "不支援的動作。")

    if not STORE.save_request_if_version(owner_id, updated, body.version):
        _, current = _load_order_or_404(vendor.vendor_id, request_id)
        raise _fail(
            409,
            "REQUEST_VERSION_CONFLICT",
            "訂單已被更新，請重新整理後再操作。",
            _detail_payload(current),
        )
    return {"success": True, **_detail_payload(updated)}
