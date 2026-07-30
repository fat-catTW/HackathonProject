"""廠商後台 API（Milestone 3／4）：諮詢單／訂單清單與接單、拒單。

廠商只看得到自己 service_vendor_id 的案件——清單一律從 token 帶出的 vendor_id
查詢（app.auth.cognito.get_current_vendor），路徑或查詢字串都不接受 vendor_id，
避免改個參數就翻到別家廠商的訂單。

接單／拒單走兩道檢查：狀態機（app.services.statuses.VENDOR_TRANSITIONS）決定這個
狀態能不能做這個動作，樂觀鎖（case 版本號）確保切換是基於廠商當下看到的那一版，
兩者任一不過就回 409，不會把別人剛寫進去的狀態蓋掉。
"""
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel, Field

from ..auth.cognito import CurrentUser, get_current_vendor
from ..auth.users import UserError
from ..auth.vendors import demo_accounts, login as vendor_login
from ..config import get_settings
from ..services import catalog
from ..services.statuses import (
    VENDOR_CLOSED_STATUSES,
    VENDOR_ORDER_STATUSES,
    VENDOR_PENDING_STATUSES,
    VENDOR_TRANSITIONS,
    status_label,
)
from ..services.store import STORE, vendor_id_of, version_of

router = APIRouter(prefix="/api/vendor")

# 住戶還沒送出的案件（草稿、等待使用者確認）不該出現在廠商後台。
_VISIBLE_STATUSES = frozenset(
    VENDOR_PENDING_STATUSES + VENDOR_ORDER_STATUSES + VENDOR_CLOSED_STATUSES
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


class VendorActionIn(BaseModel):
    # 廠商按下按鈕時看到的案件版本；對不上代表案件在這期間被改過。
    version: int = Field(..., ge=0)


def _fail(status: int, code: str, message: str, extra: dict | None = None) -> HTTPException:
    return HTTPException(
        status_code=status,
        detail={"success": False, "error": {"code": code, "message": message} | (extra or {})},
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


def _available_actions(status: str) -> list[str]:
    """這個狀態現在可以做的動作；前端不必自己複製一份狀態機。"""
    return [name for name, t in VENDOR_TRANSITIONS.items() if status in t.sources]


def _to_list_item(item: dict) -> dict:
    form_data = item.get("form_data") or {}
    status = item.get("status", "")
    return {
        "request_id": item["request_id"],
        "service_id": item.get("service_id", ""),
        "service_name": item.get("service_name", ""),
        "status": status,
        "status_label": status_label(status),
        "customer_name": _customer_name(item.get("owner_id", "")),
        "summary": _summary(form_data),
        "version": version_of(item),
        "available_actions": _available_actions(status),
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


def _load_case_or_404(vendor_id: int, request_id: str) -> tuple[str, dict]:
    """回傳 (住戶 actor_id, 案件本體)。

    VENDOR# 索引只用來確認案件屬於這家廠商、以及案件掛在哪位住戶底下；狀態與版本
    一律以 USER# 分區的案件本體為準——索引是盡力而為的鏡射，可能落後一版，拿它當
    樂觀鎖的基準會讓廠商永遠對不上版本。
    """
    index = STORE.get_vendor_request(vendor_id, request_id)
    owner_id = str((index or {}).get("owner_id") or "")
    request = STORE.get_request(owner_id, request_id) if owner_id else None
    if (
        not request
        or vendor_id_of(request) != vendor_id
        or request.get("status") not in _VISIBLE_STATUSES
    ):
        raise _fail(404, "REQUEST_NOT_FOUND", "找不到對應的案件。")
    return owner_id, request


def _detail_payload(owner_id: str, request: dict) -> dict:
    status = request.get("status", "")
    payload = {
        "request_id": request["request_id"],
        "service_id": request.get("service_id", ""),
        "service_name": request.get("service_name", ""),
        "status": status,
        "status_label": status_label(status),
        "customer_name": _customer_name(owner_id),
        "version": version_of(request),
        "available_actions": _available_actions(status),
        "fields": _to_fields(request.get("service_id", ""), request.get("form_data") or {}),
        "created_at": request.get("created_at", ""),
        "updated_at": request.get("updated_at", ""),
    }
    if request.get("estimated_fee_min") is not None:
        payload["estimated_fee_min"] = request.get("estimated_fee_min")
        payload["estimated_fee_max"] = request.get("estimated_fee_max")
    return payload


@router.get("/requests/{request_id}")
def get_vendor_request(request_id: str, vendor: CurrentUser = Depends(get_current_vendor)):
    owner_id, request = _load_case_or_404(vendor.vendor_id, request_id)
    return _detail_payload(owner_id, request)


@router.post("/requests/{request_id}/{action}")
def act_on_vendor_request(
    body: VendorActionIn,
    request_id: str,
    action: str = Path(pattern="^(accept|reject)$"),
    vendor: CurrentUser = Depends(get_current_vendor),
):
    """接單／拒單：狀態機決定能不能切，樂觀鎖確保沒有人搶先改過。"""
    owner_id, request = _load_case_or_404(vendor.vendor_id, request_id)
    transition = VENDOR_TRANSITIONS[action]
    status = request.get("status", "")

    if status not in transition.sources:
        # 例如住戶已取消、或另一位同事剛按過接單——案件現在的狀態不允許這個動作。
        raise _fail(
            409,
            "REQUEST_STATUS_CONFLICT",
            f"案件目前是「{status_label(status)}」，無法{transition.label}。",
            _detail_payload(owner_id, request),
        )

    updated = dict(request) | {"status": transition.target}
    if not STORE.save_request_if_version(owner_id, updated, body.version):
        # 版本對不上：狀態檢查到寫入之間有人改過，或這是重複送出的同一個按鈕。
        _, current = _load_case_or_404(vendor.vendor_id, request_id)
        raise _fail(
            409,
            "REQUEST_VERSION_CONFLICT",
            "案件已被更新，請重新整理後再操作。",
            _detail_payload(owner_id, current),
        )
    return {"success": True, **_detail_payload(owner_id, updated)}
