"""Chat and form update APIs."""
from fastapi import APIRouter, Depends, HTTPException

from ..agent.agent import (
    apply_form_patch,
    build_form_draft,
    build_form_schema,
    current_active_field,
    handle_message,
)
from ..auth.cognito import CurrentUser, get_current_user
from ..models.chat import ChatRequest, ChatResponse, FormUpdateRequest
from ..services import clock
from ..services.conversation_memory import MEMORY

router = APIRouter()


def _load_session_or_404(actor_id: str, session_id: str) -> dict:
    session = MEMORY.get_session(actor_id, session_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "error": {
                    "code": "SESSION_NOT_FOUND",
                    "message": "找不到對應的對話 session。",
                },
            },
        )
    return session


def _chat_response(session_id: str, result: dict) -> ChatResponse:
    state = result["state"]
    return ChatResponse(
        session_id=session_id,
        reply=result["reply"],
        service_id=state["service_id"],
        service_name=state["service_name"],
        collected_fields=state["collected_fields"],
        missing_fields=state["missing_fields"],
        form_schema=build_form_schema(state),
        form_draft=build_form_draft(state),
        active_field=current_active_field(state),
        form_actions=result.get("form_actions") or [],
        request_id=state["request_id"],
        status=state["status"],
        redirect_path=result.get("redirect_path"),
        redirect_requires_confirmation=bool(result.get("redirect_requires_confirmation")),
        product_recommendations=result.get("product_recommendations"),
        debug_trace=result.get("debug_trace", state.get("debug_trace", {})),
    )


@router.post("/api/chat", response_model=ChatResponse)
def chat(body: ChatRequest, user: CurrentUser = Depends(get_current_user)):
    session = _load_session_or_404(user.sub, body.session_id)

    # 這次請求內的「今天」以使用者裝置為準（「這禮拜三」要從他當下的日期算起）。
    date_token = clock.use_client_date(body.client_date)
    try:
        result = handle_message(
            user.sub,
            body.session_id,
            session["state"],
            body.message,
            session["events"],
            current_page_id=body.current_page_id,
            auth_token=user.access_token,
            form_context=body.form_context.model_dump() if body.form_context else None,
        )
    finally:
        clock.reset_client_date(date_token)
    MEMORY.save_turn(user.sub, body.session_id, body.message, result["reply"], result["state"])
    return _chat_response(body.session_id, result)


@router.patch("/api/chat/form", response_model=ChatResponse)
def update_form(body: FormUpdateRequest, user: CurrentUser = Depends(get_current_user)):
    session = _load_session_or_404(user.sub, body.session_id)
    result = apply_form_patch(user.sub, session["state"], body.fields)
    MEMORY.save_state(user.sub, body.session_id, result["state"])
    return _chat_response(body.session_id, result)
