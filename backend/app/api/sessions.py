"""Session API."""
import uuid

from fastapi import APIRouter, Depends

from ..agent.agent import new_state
from ..auth.cognito import CurrentUser, get_current_user
from ..services.conversation_memory import MEMORY
from ..services.store import now_iso

router = APIRouter()


@router.post("/api/sessions")
def create_session(user: CurrentUser = Depends(get_current_user)):
    session_id = str(uuid.uuid4())
    MEMORY.create_session(user.sub, session_id, new_state())
    return {"session_id": session_id, "created_at": now_iso()}
