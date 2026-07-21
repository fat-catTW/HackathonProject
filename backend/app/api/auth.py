"""Demo 登入 API（Mock 模式）。正式版改用 Cognito Hosted UI / Amplify。"""
from fastapi import APIRouter, Depends

from ..auth.cognito import CurrentUser, get_current_user
from ..config import get_settings

router = APIRouter()


@router.get("/api/auth/demo-accounts")
def demo_accounts():
    s = get_settings()
    return {"accounts": [
        {"token": t, "name": u["name"]} for t, u in s.demo_users.items()
    ]}


@router.get("/api/auth/me")
def me(user: CurrentUser = Depends(get_current_user)):
    return {"sub": user.sub, "name": user.name}
