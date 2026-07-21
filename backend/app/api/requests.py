"""案件 API（設計書 §13.3–13.6）。"""
from fastapi import APIRouter, Depends, HTTPException

from ..auth.cognito import CurrentUser, get_current_user
from ..services.store import STORE

router = APIRouter()

STATUS_LABELS = {
    "DRAFT": "草稿", "AWAITING_USER_CONFIRMATION": "待確認",
    "SUBMITTED": "等待廠商確認", "PENDING_PROVIDER": "等待廠商確認",
    "CONFIRMED": "已確認", "IN_PROGRESS": "服務中",
    "COMPLETED": "已完成", "CANCELLED": "已取消", "FAILED": "失敗",
}


def _get_or_404(actor_id: str, request_id: str) -> dict:
    req = STORE.get_request(actor_id, request_id)
    if not req:
        raise HTTPException(status_code=404, detail={
            "success": False,
            "error": {"code": "REQUEST_NOT_FOUND", "message": "找不到案件"}})
    return req


@router.get("/api/requests")
def list_requests(user: CurrentUser = Depends(get_current_user)):
    items = [
        {
            "request_id": r["request_id"],
            "service_name": r["service_name"],
            "status": r["status"],
            "status_label": STATUS_LABELS.get(r["status"], r["status"]),
            "created_at": r["created_at"],
            "updated_at": r["updated_at"],
        }
        for r in STORE.list_requests(user.sub)
    ]
    return {"items": items}


@router.get("/api/requests/{request_id}")
def get_request(request_id: str, user: CurrentUser = Depends(get_current_user)):
    r = _get_or_404(user.sub, request_id)
    session = STORE.get_session(user.sub, r.get("session_id") or "")
    return {
        "request_id": r["request_id"],
        "session_id": r.get("session_id"),
        "service_id": r["service_id"],
        "service_name": r["service_name"],
        "status": r["status"],
        "status_label": STATUS_LABELS.get(r["status"], r["status"]),
        "form_data": r["form_data"],
        "created_at": r["created_at"],
        "updated_at": r["updated_at"],
        "events": (session or {}).get("events", []),
    }


@router.post("/api/requests/{request_id}/confirm")
def confirm_request(request_id: str, user: CurrentUser = Depends(get_current_user)):
    r = _get_or_404(user.sub, request_id)
    if r["status"] not in ("DRAFT", "AWAITING_USER_CONFIRMATION"):
        raise HTTPException(status_code=409, detail={
            "success": False,
            "error": {"code": "REQUEST_ALREADY_SUBMITTED", "message": "案件已送出"}})
    r["status"] = "SUBMITTED"
    STORE.save_request(user.sub, r)
    return {"success": True, "request_id": request_id, "status": "SUBMITTED"}


@router.post("/api/requests/{request_id}/cancel")
def cancel_request(request_id: str, user: CurrentUser = Depends(get_current_user)):
    r = _get_or_404(user.sub, request_id)
    if r["status"] in ("COMPLETED", "CANCELLED"):
        raise HTTPException(status_code=409, detail={
            "success": False,
            "error": {"code": "REQUEST_ALREADY_SUBMITTED", "message": "案件狀態不可取消"}})
    r["status"] = "CANCELLED"
    STORE.save_request(user.sub, r)
    return {"success": True, "request_id": request_id, "status": "CANCELLED"}


# Demo 輔助：模擬廠商接單／完工（正式版由廠商後台或排程更新）
@router.post("/api/requests/{request_id}/simulate/{next_status}")
def simulate_status(request_id: str, next_status: str,
                    user: CurrentUser = Depends(get_current_user)):
    allowed = {"CONFIRMED", "IN_PROGRESS", "COMPLETED"}
    if next_status not in allowed:
        raise HTTPException(status_code=400, detail={
            "success": False,
            "error": {"code": "INVALID_FORM_DATA", "message": "不支援的狀態"}})
    r = _get_or_404(user.sub, request_id)
    r["status"] = next_status
    STORE.save_request(user.sub, r)
    return {"success": True, "request_id": request_id, "status": next_status}
