"""新手導引（Onboarding）狀態 API（M13）。

規劃書用 inbr_account_id 當查詢參數，但本專案所有 API 一律靠 Authorization
header 解出使用者（見 app.auth.cognito.get_current_user），避免任何人帶著
別人的帳號 ID 就能讀寫其 onboarding 狀態。這裡沿用同一套慣例，語意等價：
- GET /api/onboarding/status  → {completed, version}
- POST /api/onboarding/complete {version} → 寫入 completed=true, version

導引版本號採「新版本 > 舊版本」比對（見設計書②）：使用者已完成舊版本導引後，
若導引內容改版（version 提升），前端可依此重新彈出「差異式導引」。
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ..auth.cognito import CurrentUser, get_current_user
from ..services.store import STORE

router = APIRouter()


class OnboardingCompleteIn(BaseModel):
    version: int = Field(..., ge=1)


@router.get("/api/onboarding/status")
def get_onboarding_status(user: CurrentUser = Depends(get_current_user)):
    return STORE.get_onboarding_status(user.sub)


@router.post("/api/onboarding/complete")
def complete_onboarding(body: OnboardingCompleteIn, user: CurrentUser = Depends(get_current_user)):
    STORE.save_onboarding_status(user.sub, completed=True, version=body.version)
    return {"success": True, "completed": True, "version": body.version}
