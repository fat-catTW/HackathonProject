"""身分驗證。

Mock 模式：Authorization: Bearer demo-token-vincent / demo-token-mei。
正式模式：驗證 Cognito JWT（RS256 + JWKS），actorId 一律取自已驗證 token
的 sub，絕不信任前端自行提供的使用者 ID（設計書 §9.1、§17.2）。
"""
from __future__ import annotations

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ..config import get_settings

_bearer = HTTPBearer(auto_error=False)


class CurrentUser:
    def __init__(self, sub: str, name: str) -> None:
        self.sub = sub
        self.name = name


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> CurrentUser:
    settings = get_settings()
    if credentials is None:
        raise HTTPException(status_code=401, detail={
            "success": False,
            "error": {"code": "UNAUTHORIZED", "message": "缺少 Authorization"}})

    token = credentials.credentials
    if settings.use_mock:
        user = settings.demo_users.get(token)
        if not user:
            raise HTTPException(status_code=401, detail={
                "success": False,
                "error": {"code": "UNAUTHORIZED", "message": "無效的示範 Token"}})
        return CurrentUser(sub=user["sub"], name=user["name"])

    # ---- 正式模式：Cognito JWT 驗證（Milestone 6） ----
    try:
        import jwt
        from jwt import PyJWKClient

        issuer = (f"https://cognito-idp.{settings.aws_region}.amazonaws.com/"
                  f"{settings.cognito_user_pool_id}")
        jwks = PyJWKClient(f"{issuer}/.well-known/jwks.json")
        signing_key = jwks.get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token, signing_key.key, algorithms=["RS256"],
            audience=settings.cognito_client_id, issuer=issuer)
        return CurrentUser(sub=claims["sub"],
                           name=claims.get("name") or claims.get("cognito:username", ""))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=401, detail={
            "success": False,
            "error": {"code": "UNAUTHORIZED", "message": f"JWT 驗證失敗: {exc}"}})
