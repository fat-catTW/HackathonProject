"""Request API."""
from fastapi import APIRouter, Depends, HTTPException

from ..auth.cognito import CurrentUser, get_current_user
from ..services.conversation_memory import MEMORY
from ..services.store import STORE

router = APIRouter()

STATUS_LABELS = {
    "DRAFT": "草稿",
    "AWAITING_USER_CONFIRMATION": "等待使用者確認",
    "SUBMITTED": "等待廠商確認",
    "PENDING_PROVIDER": "等待廠商確認",
    "CONFIRMED": "已確認",
    "IN_PROGRESS": "服務進行中",
    "COMPLETED": "已完成",
    "CANCELLED": "已取消",
    "FAILED": "失敗",
}


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
            "created_at": item["created_at"],
            "updated_at": item["updated_at"],
        }
        for item in STORE.list_requests(user.sub)
    ]
    return {"items": items}


@router.get("/api/requests/{request_id}")
def get_request(request_id: str, user: CurrentUser = Depends(get_current_user)):
    request = _get_or_404(user.sub, request_id)
    session = MEMORY.get_session(user.sub, request.get("session_id") or "")
    return {
        "request_id": request["request_id"],
        "session_id": request.get("session_id"),
        "service_id": request["service_id"],
        "service_name": request["service_name"],
        "status": request["status"],
        "status_label": STATUS_LABELS.get(request["status"], request["status"]),
        "form_data": request["form_data"],
        "created_at": request["created_at"],
        "updated_at": request["updated_at"],
        "events": (session or {}).get("events", []),
    }


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
    if request["status"] in ("COMPLETED", "CANCELLED"):
        raise HTTPException(
            status_code=409,
            detail={
                "success": False,
                "error": {"code": "REQUEST_ALREADY_SUBMITTED", "message": "案件已完成或已取消。"},
            },
        )
    request["status"] = "CANCELLED"
    STORE.save_request(user.sub, request)
    return {"success": True, "request_id": request_id, "status": "CANCELLED"}


@router.post("/api/requests/{request_id}/simulate/{next_status}")
def simulate_status(request_id: str, next_status: str, user: CurrentUser = Depends(get_current_user)):
    allowed = {"CONFIRMED", "IN_PROGRESS", "COMPLETED"}
    if next_status not in allowed:
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "error": {"code": "INVALID_FORM_DATA", "message": "不支援的模擬狀態。"},
            },
        )
    request = _get_or_404(user.sub, request_id)
    request["status"] = next_status
    STORE.save_request(user.sub, request)
    return {"success": True, "request_id": request_id, "status": next_status}
