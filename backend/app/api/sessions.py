"""POST /api/sessions — 建立新的案件 Session（設計書 §13.2）。"""
import uuid

from fastapi import APIRouter, Depends

from ..agent.agent import new_state
from ..auth.cognito import CurrentUser, get_current_user
from ..services.store import STORE, now_iso

router = APIRouter()


@router.post("/api/sessions")
def create_session(user: CurrentUser = Depends(get_current_user)):
    session_id = str(uuid.uuid4())
    STORE.save_session(user.sub, {
        "session_id": session_id,
        "entity_type": "SESSION",
        "state": new_state(),
        "events": [],           # 短期記憶：對話事件（模擬 AgentCore Memory）
        "created_at": now_iso(),
    })
    return {"session_id": session_id, "created_at": now_iso()}
