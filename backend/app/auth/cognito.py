"""Authentication helpers."""
from __future__ import annotations

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ..config import get_settings

_bearer = HTTPBearer(auto_error=False)


class CurrentUser:
    def __init__(self, sub: str, name: str, access_token: str | None = None) -> None:
        self.sub = sub
        self.name = name
        self.access_token = access_token


def _demo_user_or_401(token: str) -> CurrentUser:
    settings = get_settings()
    user = settings.demo_users.get(token)
    if not user:
        raise HTTPException(
            status_code=401,
            detail={
                "success": False,
                "error": {"code": "UNAUTHORIZED", "message": "Invalid demo token."},
            },
        )
    return CurrentUser(sub=user["sub"], name=user["name"], access_token=token)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> CurrentUser:
    settings = get_settings()
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail={
                "success": False,
                "error": {"code": "UNAUTHORIZED", "message": "Missing Authorization header."},
            },
        )

    token = credentials.credentials
    if settings.use_mock:
        return _demo_user_or_401(token)

    if settings.allow_demo_auth and token in settings.demo_users:
        return _demo_user_or_401(token)

    try:
        import jwt
        from jwt import PyJWKClient

        issuer = (
            f"https://cognito-idp.{settings.aws_region}.amazonaws.com/"
            f"{settings.cognito_user_pool_id}"
        )
        jwks = PyJWKClient(f"{issuer}/.well-known/jwks.json")
        signing_key = jwks.get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=settings.cognito_client_id,
            issuer=issuer,
        )
        return CurrentUser(
            sub=claims["sub"],
            name=claims.get("name") or claims.get("cognito:username", ""),
            access_token=token,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=401,
            detail={
                "success": False,
                "error": {"code": "UNAUTHORIZED", "message": f"JWT verification failed: {exc}"},
            },
        )
