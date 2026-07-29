"""Authentication helpers."""
from __future__ import annotations

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ..config import get_settings

_bearer = HTTPBearer(auto_error=False)


class CurrentUser:
    def __init__(
        self,
        sub: str,
        name: str,
        access_token: str | None = None,
        vendor_id: int | None = None,
    ) -> None:
        self.sub = sub
        self.name = name
        self.access_token = access_token
        # 非 None 代表這是廠商後台帳號；住戶端 API 一律拒絕，見 get_current_user。
        self.vendor_id = vendor_id


def _demo_user_or_401(token: str) -> CurrentUser:
    """示範帳號 token → 使用者；註冊帳號的 token 已在 get_current_user 解析過。"""
    settings = get_settings()
    user = settings.demo_users.get(token)
    if not user:
        raise HTTPException(
            status_code=401,
            detail={
                "success": False,
                "error": {"code": "UNAUTHORIZED", "message": "Invalid token."},
            },
        )
    return CurrentUser(sub=user["sub"], name=user["name"], access_token=token)


def get_current_vendor(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> CurrentUser:
    """廠商後台專用：只接受帶 vendor_id 的 token，住戶 token 一律 403。"""
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail={
                "success": False,
                "error": {"code": "UNAUTHORIZED", "message": "Missing Authorization header."},
            },
        )

    from .users import USERS

    token = credentials.credentials
    vendor = USERS.resolve(token)
    if vendor is None:
        # 住戶示範帳號要回 403 而非 401：401 會讓前端把 token 清掉，等於把還在
        # 使用住戶端的人登出。
        if token in get_settings().demo_users:
            raise HTTPException(
                status_code=403,
                detail={
                    "success": False,
                    "error": {"code": "VENDOR_FORBIDDEN", "message": "此帳號沒有廠商後台權限。"},
                },
            )
        raise HTTPException(
            status_code=401,
            detail={
                "success": False,
                "error": {"code": "UNAUTHORIZED", "message": "Invalid or expired token."},
            },
        )
    if vendor.vendor_id is None:
        raise HTTPException(
            status_code=403,
            detail={
                "success": False,
                "error": {"code": "VENDOR_FORBIDDEN", "message": "此帳號沒有廠商後台權限。"},
            },
        )
    return vendor


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

    # Email 註冊／登入的 token 存在 DynamoDB，mock 與正式模式都要能換回使用者。
    from .users import USERS

    registered = USERS.resolve(token)
    if registered is not None:
        if registered.vendor_id is not None:
            # 廠商帳號沒有住戶身分（沒有自己的案件、偏好與對話），誤用只會建立
            # 掛在 vendor-* 名下的孤兒資料，這裡直接擋掉。
            raise HTTPException(
                status_code=403,
                detail={
                    "success": False,
                    "error": {
                        "code": "VENDOR_ACCOUNT_NOT_ALLOWED",
                        "message": "廠商帳號請使用廠商後台。",
                    },
                },
            )
        return registered

    if settings.use_mock:
        return _demo_user_or_401(token)

    if settings.allow_demo_auth and token in settings.demo_users:
        return _demo_user_or_401(token)

    if not (settings.cognito_user_pool_id and settings.cognito_client_id):
        raise HTTPException(
            status_code=401,
            detail={
                "success": False,
                "error": {"code": "UNAUTHORIZED", "message": "Invalid or expired token."},
            },
        )

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
