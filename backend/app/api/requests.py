"""Request API."""
from fastapi import APIRouter, Depends, HTTPException

from ..auth.cognito import CurrentUser, get_current_user
from ..services import shop
from ..services.conversation_memory import MEMORY
from ..services.statuses import STATUS_LABELS, build_progress
from ..services.store import STORE, quote_amount_of

router = APIRouter()


def _get_or_404(actor_id: str, request_id: str) -> dict:
    request = STORE.get_request(actor_id, request_id)
    if not request:
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "error": {"code": "REQUEST_NOT_FOUND", "message": "找不到對應的案件。"},
            },
        )
    return request


@router.get("/api/requests")
def list_requests(user: CurrentUser = Depends(get_current_user)):
    items = [
        {
            "request_id": item["request_id"],
            "service_name": item["service_name"],
            "status": item["status"],
            "status_label": STATUS_LABELS.get(item["status"], item["status"]),
            # 報價金額也放進清單：案件進度通知要在卡片上直接寫出「報價 3200 元」，
            # 只給狀態的話住戶還得自己點進去才知道被報了多少。
            "quote_amount": quote_amount_of(item),
            # 用 get 而非 []：欄位不齊的案件（早期直接寫進 store 的資料）不該讓整份
            # 清單回 500——住戶會看到「我的服務」整頁掛掉，而不是少一列時間。
            "created_at": item.get("created_at", ""),
            "updated_at": item.get("updated_at", ""),
        }
        for item in STORE.list_requests(user.sub)
    ]
    return {"items": items}


@router.get("/api/requests/{request_id}")
def get_request(request_id: str, user: CurrentUser = Depends(get_current_user)):
    request = _get_or_404(user.sub, request_id)
    session_id = request.get("session_id")
    session = MEMORY.get_session(user.sub, session_id) if session_id else None
    response = {
        "request_id": request["request_id"],
        "session_id": session_id,
        "service_id": request["service_id"],
        "service_name": request["service_name"],
        "status": request["status"],
        "status_label": STATUS_LABELS.get(request["status"], request["status"]),
        "form_data": request["form_data"],
        "quote_amount": quote_amount_of(request),
        # 進度條的每一格（含還沒走到的），住戶不必自己從一個狀態徽章腦補整條流程。
        "progress": build_progress(request),
        "created_at": request.get("created_at", ""),
        "updated_at": request.get("updated_at", ""),
        "events": (session or {}).get("events", []),
    }
    if request.get("estimated_fee_min") is not None:
        response["estimated_fee_min"] = request.get("estimated_fee_min")
        response["estimated_fee_max"] = request.get("estimated_fee_max")
    return response


@router.post("/api/requests/{request_id}/confirm")
def confirm_request(request_id: str, user: CurrentUser = Depends(get_current_user)):
    request = _get_or_404(user.sub, request_id)
    if request["status"] not in ("DRAFT", "AWAITING_USER_CONFIRMATION"):
        raise HTTPException(
            status_code=409,
            detail={
                "success": False,
                "error": {"code": "REQUEST_ALREADY_SUBMITTED", "message": "案件已經送出。"},
            },
        )
    request["status"] = "SUBMITTED"
    STORE.save_request(user.sub, request)
    return {"success": True, "request_id": request_id, "status": "SUBMITTED"}


@router.post("/api/requests/{request_id}/cancel")
def cancel_request(request_id: str, user: CurrentUser = Depends(get_current_user)):
    request = _get_or_404(user.sub, request_id)
    if request.get("service_id") == "shop_purchase":
        result = shop.cancel_shop_order(user.sub, request_id)
        if not result.get("success"):
            code = result["error"]["code"]
            raise HTTPException(
                status_code=404 if code == "REQUEST_NOT_FOUND" else 409,
                detail={"success": False, "error": result["error"]},
            )
        return {"success": True, "request_id": request_id, "status": result["status"]}
    # 已完工、已取消、廠商已婉拒都是終點狀態，沒有東西可以取消。
    if request["status"] in ("COMPLETED", "CANCELLED", "REJECTED"):
        raise HTTPException(
            status_code=409,
            detail={
                "success": False,
                "error": {"code": "REQUEST_ALREADY_SUBMITTED", "message": "案件已結案。"},
            },
        )
    request["status"] = "CANCELLED"
    STORE.save_request(user.sub, request)
    return {"success": True, "request_id": request_id, "status": "CANCELLED"}
