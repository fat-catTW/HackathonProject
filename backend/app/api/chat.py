"""POST /api/chat — 送訊息給 Agent（設計書 §13.1）。"""
from fastapi import APIRouter, Depends, HTTPException

from ..agent.agent import handle_message
from ..auth.cognito import CurrentUser, get_current_user
from ..models.chat import ChatRequest, ChatResponse
from ..services.store import STORE

router = APIRouter()


@router.post("/api/chat", response_model=ChatResponse)
def chat(body: ChatRequest, user: CurrentUser = Depends(get_current_user)):
    # Session 隔離：一律以已驗證 actorId 查詢（§17.3）
    session = STORE.get_session(user.sub, body.session_id)
    if not session:
        raise HTTPException(status_code=404, detail={
            "success": False,
            "error": {"code": "SESSION_NOT_FOUND", "message": "找不到 Session"}})

    session["events"].append({"role": "USER", "content": body.message})
    result = handle_message(user.sub, body.session_id, session["state"], body.message)
    session["events"].append({"role": "ASSISTANT", "content": result["reply"]})
    session["state"] = result["state"]
    STORE.save_session(user.sub, session)

    st = result["state"]
    return ChatResponse(
        session_id=body.session_id,
        reply=result["reply"],
        service_id=st["service_id"],
        service_name=st["service_name"],
        collected_fields=st["collected_fields"],
        missing_fields=st["missing_fields"],
        request_id=st["request_id"],
        status=st["status"],
    )
