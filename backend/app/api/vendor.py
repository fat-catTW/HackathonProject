"""廠商後台 API（Milestone 3）：諮詢單／訂單清單。

廠商只看得到自己 service_vendor_id 的案件——清單一律從 token 帶出的 vendor_id
查詢（app.auth.cognito.get_current_vendor），路徑或查詢字串都不接受 vendor_id，
避免改個參數就翻到別家廠商的訂單。
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..auth.cognito import CurrentUser, get_current_vendor
from ..auth.users import UserError
from ..auth.vendors import demo_accounts, login as vendor_login
from ..config import get_settings
from ..services import catalog
from ..services.statuses import (
    VENDOR_ORDER_STATUSES,
    VENDOR_PENDING_STATUSES,
    status_label,
)
from ..services.store import STORE

router = APIRouter(prefix="/api/vendor")

# 住戶還沒送出的案件（草稿、等待使用者確認）不該出現在廠商後台。
_VISIBLE_STATUSES = frozenset(
    VENDOR_PENDING_STATUSES + VENDOR_ORDER_STATUSES + ("CANCELLED", "FAILED")
)

_SCOPES = {
    "pending": frozenset(VENDOR_PENDING_STATUSES),
    "orders": frozenset(VENDOR_ORDER_STATUSES),
    "all": _VISIBLE_STATUSES,
}

# 清單上顯示的摘要欄位，依序取第一個有值的日期／時段／地址。
_SUMMARY_FIELDS = ("preferred_date", "preferred_time_slot", "address")


class VendorLoginIn(BaseModel):
    email: str = Field(..., max_length=254)
    password: str = Field(..., max_length=128)


def _fail(status: int, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status,
        detail={"success": False, "error": {"code": code, "message": message}},
    )


def _customer_name(owner_id: str) -> str:
    profile = STORE.get_user_profile(owner_id) or {}
    if profile.get("name"):
        return profile["name"]
    demo = next(
        (u["name"] for u in get_settings().demo_users.values() if u["sub"] == owner_id),
        None,
    )
    return demo or "住戶"


def _display_value(value) -> str:
    if value is None:
        return ""
    return catalog.SELECT_LABELS.get(str(value), str(value))


def _summary(form_data: dict) -> str:
    parts = [_display_value(form_data.get(f)) for f in _SUMMARY_FIELDS]
    return " ".join(p for p in parts if p)


def _to_list_item(item: dict) -> dict:
    form_data = item.get("form_data") or {}
    return {
        "request_id": item["request_id"],
        "service_id": item.get("service_id", ""),
        "service_name": item.get("service_name", ""),
        "status": item.get("status", ""),
        "status_label": status_label(item.get("status", "")),
        "customer_name": _customer_name(item.get("owner_id", "")),
        "summary": _summary(form_data),
        "created_at": item.get("created_at", ""),
        "updated_at": item.get("updated_at", ""),
    }


def _to_fields(service_id: str, form_data: dict) -> list[dict]:
    """依服務 schema 的欄位順序輸出 label／值，前端不必重複一份表單定義。"""
    schema = catalog.get_service_schema(service_id) or {"fields": []}
    known = [
        {
            "id": field["id"],
            "label": field["label"],
            "value": _display_value(form_data.get(field["id"])),
        }
        for field in schema["fields"]
        if form_data.get(field["id"]) not in (None, "")
    ]
    known_ids = {field["id"] for field in schema["fields"]}
    # schema 之後改版時，仍把舊案件多出來的欄位原樣列出，不要默默吃掉。
    extra = [
        {"id": key, "label": key, "value": _display_value(value)}
        for key, value in form_data.items()
        if key not in known_ids and value not in (None, "")
    ]
    return known + extra


@router.post("/login")
def login(body: VendorLoginIn):
    try:
        vendor, token = vendor_login(body.email, body.password)
    except UserError as e:
        status = 503 if e.code == "STORAGE_UNAVAILABLE" else 401
        raise _fail(status, e.code, e.message)
    return {"token": token, "vendor_id": vendor.vendor_id, "name": vendor.name}


@router.get("/demo-accounts")
def vendor_demo_accounts():
    return {"accounts": demo_accounts()}


@router.get("/me")
def me(vendor: CurrentUser = Depends(get_current_vendor)):
    return {
        "vendor_id": vendor.vendor_id,
        "name": vendor.name,
        "service_ids": catalog.service_ids_for_vendor(vendor.vendor_id),
    }


@router.get("/requests")
def list_vendor_requests(
    scope: str = Query("all", pattern="^(all|pending|orders)$"),
    vendor: CurrentUser = Depends(get_current_vendor),
):
    stored = STORE.list_vendor_requests(vendor.vendor_id)
    items = [_to_list_item(item) for item in stored if item.get("status") in _SCOPES[scope]]
    # 各分頁的筆數一起回傳，前端切換 tab 時不必再打一次 API。
    counts = {
        name: sum(1 for item in stored if item.get("status") in statuses)
        for name, statuses in _SCOPES.items()
    }
    return {"items": items, "counts": counts}


@router.get("/requests/{request_id}")
def get_vendor_request(request_id: str, vendor: CurrentUser = Depends(get_current_vendor)):
    item = STORE.get_vendor_request(vendor.vendor_id, request_id)
    if not item or item.get("status") not in _VISIBLE_STATUSES:
        raise _fail(404, "REQUEST_NOT_FOUND", "找不到對應的案件。")
    form_data = item.get("form_data") or {}
    response = {
        "request_id": item["request_id"],
        "service_id": item.get("service_id", ""),
        "service_name": item.get("service_name", ""),
        "status": item.get("status", ""),
        "status_label": status_label(item.get("status", "")),
        "customer_name": _customer_name(item.get("owner_id", "")),
        "fields": _to_fields(item.get("service_id", ""), form_data),
        "created_at": item.get("created_at", ""),
        "updated_at": item.get("updated_at", ""),
    }
    if item.get("estimated_fee_min") is not None:
        response["estimated_fee_min"] = item.get("estimated_fee_min")
        response["estimated_fee_max"] = item.get("estimated_fee_max")
    return response
