"""Standalone scam-message classification, independent of the booking chat flow."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..agent import llm
from ..auth.cognito import CurrentUser, get_current_user

router = APIRouter()


class ScamCheckRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)


class ScamCheckResponse(BaseModel):
    category: str
    explanation: str


@router.post("/api/scam-check", response_model=ScamCheckResponse)
def scam_check(body: ScamCheckRequest, _user: CurrentUser = Depends(get_current_user)):
    result = llm.check_scam_message(body.message)
    if not result:
        raise HTTPException(
            status_code=503,
            detail={
                "success": False,
                "error": {"code": "SCAM_CHECK_UNAVAILABLE", "message": "目前無法判斷這則訊息，請稍後再試。"},
            },
        )
    return ScamCheckResponse(**result)
