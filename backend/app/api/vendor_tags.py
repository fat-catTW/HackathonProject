"""廠商後台的案件標籤（P1 V5 案件分類與標籤）。

一般服務／美食外送／商城出貨各有自己的清單端點，但「貼標籤」對三邊是同一件事：
在自己的案件上加一段內部註記，方便在清單裡挑出急件、大型案件、等著報價的單。因此
標籤只做這一份實作，靠 VENDOR# 索引確認案件歸屬——索引存在就代表這張單是這家廠商
的，跟它屬於哪條服務線無關。

標籤不寫進案件本體（見 store.save_case_tags 的說明）：它是廠商的內部註記，住戶端
看不到，也不該因為貼個標籤就推進案件版本、害後台另一個分頁的接單被樂觀鎖擋下。
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..auth.cognito import CurrentUser, get_current_vendor
from ..services.case_tags import MAX_TAGS, TagError, normalize_tags
from ..services.store import STORE

router = APIRouter(prefix="/api/vendor/case-tags")

# 住戶還沒送出的案件（草稿、等待使用者確認）在廠商清單上本來就看不到，也就不該
# 能貼標籤。用排除法而不是列出可見狀態：三條服務線的狀態字彙不同（PENDING、
# PENDING_PROVIDER、SUBMITTED…），維護一份聯集只會在新增狀態時漏掉。
_HIDDEN_STATUSES = frozenset({"DRAFT", "AWAITING_USER_CONFIRMATION"})


class CaseTagsIn(BaseModel):
    # 整組覆寫而不是逐個增刪：標籤編輯器一次送出使用者當下看到的完整清單，語意單純
    # 且可重送。上限比 MAX_TAGS 寬一格，讓超量的請求走 normalize_tags 回中文訊息，
    # 而不是被 pydantic 擋成 422。
    tags: list[str] = Field(default_factory=list, max_length=MAX_TAGS + 1)


def _fail(status: int, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status,
        detail={"success": False, "error": {"code": code, "message": message}},
    )


def _assert_owns_case(vendor_id: int, request_id: str) -> None:
    """這張單不是這家廠商的（或還沒送出）就當作不存在，不透露它存在於別家後台。"""
    index = STORE.get_vendor_request(vendor_id, request_id)
    if not index or index.get("status") in _HIDDEN_STATUSES:
        raise _fail(404, "REQUEST_NOT_FOUND", "找不到對應的案件。")


@router.get("")
def list_case_tags(vendor: CurrentUser = Depends(get_current_vendor)):
    """這家廠商所有案件的標籤：`{案件編號: [標籤…]}`。

    清單頁一次拿齊，才能在不逐張查詢的情況下畫出標籤 chip 與標籤篩選器。沒貼標籤
    的案件不會出現在這份字典裡。
    """
    return {"tags": STORE.list_case_tags(vendor.vendor_id)}


@router.get("/{request_id}")
def get_case_tags(request_id: str, vendor: CurrentUser = Depends(get_current_vendor)):
    _assert_owns_case(vendor.vendor_id, request_id)
    return {"request_id": request_id, "tags": STORE.get_case_tags(vendor.vendor_id, request_id)}


@router.put("/{request_id}")
def put_case_tags(
    body: CaseTagsIn,
    request_id: str,
    vendor: CurrentUser = Depends(get_current_vendor),
):
    """整組覆寫這張單的標籤，回傳實際存下來的樣子（已去空白、去重）。"""
    _assert_owns_case(vendor.vendor_id, request_id)
    try:
        tags = normalize_tags(body.tags)
    except TagError as e:
        raise _fail(400, e.code, e.message)
    STORE.save_case_tags(vendor.vendor_id, request_id, tags)
    return {"success": True, "request_id": request_id, "tags": tags}
