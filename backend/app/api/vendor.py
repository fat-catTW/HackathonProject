"""廠商後台 API（Milestone 3／4／15）：諮詢單／訂單清單、接單拒單、聯絡資訊檢視。

廠商只看得到自己 service_vendor_id 的案件——清單一律從 token 帶出的 vendor_id
查詢（app.auth.cognito.get_current_vendor），路徑或查詢字串都不接受 vendor_id，
避免改個參數就翻到別家廠商的訂單。

接單／拒單走兩道檢查：狀態機（app.services.statuses.VENDOR_TRANSITIONS）決定這個
狀態能不能做這個動作，樂觀鎖（case 版本號）確保切換是基於廠商當下看到的那一版，
兩者任一不過就回 409，不會把別人剛寫進去的狀態蓋掉。

聯絡資訊（姓名／電話／地址）在儲存層就是密文（app.services.contact_privacy），
清單與明細一律只給遮罩值；要看完整內容得另外呼叫 POST /requests/{id}/contact，
每次呼叫都會留下一筆存取紀錄，紀錄寫不進去就不解密。
"""
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel, Field

from ..auth.cognito import CurrentUser, get_current_vendor
from ..auth.users import UserError
from ..auth.vendors import demo_accounts, login as vendor_login
from ..config import get_settings
from ..services import catalog, contact_privacy
from ..services.statuses import (
    VENDOR_CLOSED_STATUSES,
    VENDOR_ORDER_STATUSES,
    VENDOR_PENDING_STATUSES,
    VENDOR_TRANSITIONS,
    status_label,
)
from ..services.store import STORE, now_iso, vendor_id_of, version_of

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


def _masked_form(item: dict) -> dict:
    """案件內容，但聯絡欄位換成遮罩值——廠商清單與明細一律經過這裡。"""
    return contact_privacy.mask_for_display(
        item.get("form_data") or {}, item.get("form_data_masked") or {}
    )


def _summary(form_data: dict) -> str:
    parts = [_display_value(form_data.get(f)) for f in _SUMMARY_FIELDS]
    return " ".join(p for p in parts if p)


def _available_actions(status: str, service_id: str) -> list[str]:
    """這個狀態現在可以做的動作；前端不必自己複製一份狀態機。"""
    return [
        name
        for name, t in VENDOR_TRANSITIONS.items()
        if status in t.sources and (t.applicable_services is None or service_id in t.applicable_services)
    ]


def _to_list_item(item: dict) -> dict:
    form_data = _masked_form(item)
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
        "available_actions": _available_actions(status, item.get("service_id", "")),
        "created_at": item.get("created_at", ""),
        "updated_at": item.get("updated_at", ""),
    }


def _field_labels(service_id: str) -> dict[str, str]:
    schema = catalog.get_service_schema(service_id) or {"fields": []}
    return {field["id"]: field["label"] for field in schema["fields"]}


def _to_fields(service_id: str, form_data: dict) -> list[dict]:
    """依服務 schema 的欄位順序輸出 label／值，前端不必重複一份表單定義。

    `masked=True` 的欄位拿到的是遮罩值，前端據此把它們歸到「聯絡資訊」區塊並顯示
    解鎖按鈕，不必自己維護一份聯絡欄位清單。
    """
    labels = _field_labels(service_id)
    ordered = [key for key in labels if key in form_data] + [
        # schema 之後改版時，仍把舊案件多出來的欄位原樣列出，不要默默吃掉。
        key
        for key in form_data
        if key not in labels
    ]
    return [
        {
            "id": key,
            "label": labels.get(key, key),
            "value": _display_value(form_data[key]),
            "masked": key in contact_privacy.CONTACT_FIELDS,
        }
        for key in ordered
        if form_data.get(key) not in (None, "")
    ]


def _access_log(request_id: str, vendor_id: int, service_id: str) -> list[dict]:
    """這家廠商對這張單的聯絡資訊存取紀錄，新的在前。"""
    labels = _field_labels(service_id)
    return [
        {
            "at": entry.get("at", ""),
            "viewer_name": entry.get("vendor_name", ""),
            "fields": [labels.get(f, f) for f in entry.get("fields", [])],
        }
        for entry in STORE.list_contact_access(request_id, vendor_id)
    ]


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
    # get_stored_request 而非 get_request：廠商拿到的案件聯絡欄位要保持密文，解密
    # 只發生在會留下存取紀錄的 /contact。
    request = STORE.get_stored_request(owner_id, request_id) if owner_id else None
    if (
        not request
        or vendor_id_of(request) != vendor_id
        or request.get("status") not in _VISIBLE_STATUSES
    ):
        raise _fail(404, "REQUEST_NOT_FOUND", "找不到對應的案件。")
    return owner_id, request


def _detail_payload(owner_id: str, request: dict, vendor_id: int) -> dict:
    status = request.get("status", "")
    service_id = request.get("service_id", "")
    fields = _to_fields(service_id, _masked_form(request))
    payload = {
        "request_id": request["request_id"],
        "service_id": service_id,
        "service_name": request.get("service_name", ""),
        "status": status,
        "status_label": status_label(status),
        "customer_name": _customer_name(owner_id),
        # 建單當下算好的一句話重點；舊案件沒有這個欄位，前端就不顯示那一列。
        "ai_summary": request.get("ai_summary") or "",
        "version": version_of(request),
        "available_actions": _available_actions(status, request.get("service_id", "")),
        "fields": fields,
        # 有遮罩欄位才需要顯示「檢視完整聯絡資訊」；純商品訂單沒有就不用。
        "has_contact": any(field["masked"] for field in fields),
        "contact_access_log": _access_log(request["request_id"], vendor_id, service_id),
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
    return _detail_payload(owner_id, request, vendor.vendor_id)


# 這條要排在 /{action} 前面：路徑樣板一樣，FastAPI 依宣告順序比對，排在後面的話
# "contact" 會先被當成 action 而卡在 422。
@router.post("/requests/{request_id}/contact")
def reveal_contact(request_id: str, vendor: CurrentUser = Depends(get_current_vendor)):
    """解密顯示聯絡人資料，並留下一筆存取紀錄。

    紀錄寫不進去就不給資料（回 503）：存取軌跡是這條 API 存在的前提，先吐出電話再
    去記錄，記錄失敗時就成了一次查不到的存取。
    """
    owner_id, request = _load_case_or_404(vendor.vendor_id, request_id)
    plain = contact_privacy.decrypt_form_data(request.get("form_data") or {})
    labels = _field_labels(request.get("service_id", ""))
    contact = [
        {
            "id": key,
            "label": labels.get(key, key),
            # 解不開的欄位（金鑰換過）照實說，不要把密文當成電話號碼顯示出去。
            "value": "（無法解密）" if contact_privacy.is_encrypted(value) else str(value),
        }
        for key, value in plain.items()
        if key in contact_privacy.CONTACT_FIELDS and value not in (None, "")
    ]
    if not contact:
        raise _fail(404, "CONTACT_NOT_FOUND", "這筆案件沒有聯絡資訊。")

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
        "contact_access_log": _access_log(
            request_id, vendor.vendor_id, request.get("service_id", "")
        ),
    }


@router.post("/requests/{request_id}/{action}")
def act_on_vendor_request(
    body: VendorActionIn,
    request_id: str,
    action: str = Path(pattern="^(accept|reject|start|complete|verify)$"),
    vendor: CurrentUser = Depends(get_current_vendor),
):
    """接單／拒單／開始／完成／核銷：狀態機決定能不能切，樂觀鎖確保沒有人搶先改過。"""
    owner_id, request = _load_case_or_404(vendor.vendor_id, request_id)
    transition = VENDOR_TRANSITIONS[action]
    status = request.get("status", "")
    service_id = request.get("service_id", "")
    eligible = status in transition.sources and (
        transition.applicable_services is None or service_id in transition.applicable_services
    )

    if not eligible:
        # 例如住戶已取消、另一位同事剛按過接單、或這個服務根本沒有核銷這個動作。
        raise _fail(
            409,
            "REQUEST_STATUS_CONFLICT",
            f"案件目前是「{status_label(status)}」，無法{transition.label}。",
            _detail_payload(owner_id, request, vendor.vendor_id),
        )

    updated = dict(request) | {"status": transition.target}
    if service_id == "restaurant_reservation":
        # 餐廳訂位案件另外維護一份兩位數 order_status／歷程，要跟 status 同步推進，
        # 否則住戶端看到的 order_status 會卡在舊狀態（沿用原本 simulate 端點的邏輯）。
        from ..services.reservation import TEXT_TO_ORDER_STATUS

        order_status = TEXT_TO_ORDER_STATUS.get(transition.target)
        if order_status:
            updated["order_status"] = order_status
            updated.setdefault("status_history", []).append({"status": order_status, "at": now_iso()})

    if not STORE.save_request_if_version(owner_id, updated, body.version):
        # 版本對不上：狀態檢查到寫入之間有人改過，或這是重複送出的同一個按鈕。
        _, current = _load_case_or_404(vendor.vendor_id, request_id)
        raise _fail(
            409,
            "REQUEST_VERSION_CONFLICT",
            "案件已被更新，請重新整理後再操作。",
            _detail_payload(owner_id, current, vendor.vendor_id),
        )
    return {"success": True, **_detail_payload(owner_id, updated, vendor.vendor_id)}
