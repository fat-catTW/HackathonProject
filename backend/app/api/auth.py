"""登入 API。

Mock 模式提供 Email 註冊／登入（app.auth.users），並保留示範帳號；
正式版改用 Cognito Hosted UI / Amplify（設計書 §6、Milestone 6）。
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..auth.cognito import CurrentUser, get_current_user
from ..auth.users import USERS, UserError
from ..config import get_settings

router = APIRouter()


class RegisterIn(BaseModel):
    email: str = Field(..., max_length=254)
    password: str = Field(..., max_length=128)
    name: str = Field("", max_length=60)


class LoginIn(BaseModel):
    email: str = Field(..., max_length=254)
    password: str = Field(..., max_length=128)


def _fail(status: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status, detail={
        "success": False, "error": {"code": code, "message": message}})


# 註冊與登入共用的錯誤碼；未列出者用各自的預設值（註冊 400、登入 401）。
_STATUS_BY_CODE = {"EMAIL_EXISTS": 409, "STORAGE_UNAVAILABLE": 503}


def _status_for(code: str, default: int) -> int:
    return _STATUS_BY_CODE.get(code, default)


@router.post("/api/auth/register")
def register(body: RegisterIn):
    try:
        user, token = USERS.register(body.email, body.password, body.name)
    except UserError as e:
        raise _fail(_status_for(e.code, default=400), e.code, e.message)
    return {"token": token, "sub": user.sub, "name": user.name}


@router.post("/api/auth/login")
def login(body: LoginIn):
    try:
        user, token = USERS.login(body.email, body.password)
    except UserError as e:
        raise _fail(_status_for(e.code, default=401), e.code, e.message)
    return {"token": token, "sub": user.sub, "name": user.name}


@router.get("/api/auth/demo-accounts")
def demo_accounts():
    s = get_settings()
    return {"accounts": [
        {"token": t, "name": u["name"]} for t, u in s.demo_users.items()
    ]}


@router.get("/api/auth/me")
def me(user: CurrentUser = Depends(get_current_user)):
    return {"sub": user.sub, "name": user.name}
