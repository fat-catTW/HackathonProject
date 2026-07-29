"""廠商後台登入（Milestone 3）。

廠商帳號由部署端佈建（config._load_vendor_accounts / VENDOR_ACCOUNTS 環境變數），
**不開放自助註冊**：vendor_id 決定看得到哪些案件，若讓使用者註冊時自行宣告
vendor_id，等同能讀取任一廠商的訂單與住戶聯絡資料。

token 沿用 app.auth.users 的 token 表（同一套 TTL、快取與登出），只是多帶一個
vendor_id 欄位；解析回來的 CurrentUser.vendor_id 非 None 即為廠商身分。
正式版（Milestone 6）改由 Cognito 群組 vendor:{id} 帶出，本模組即可移除。
"""
from __future__ import annotations

import hmac

from ..config import get_settings
from .cognito import CurrentUser
from .users import USERS, UserError


def _account_for(email: str) -> dict | None:
    return get_settings().vendor_accounts.get(email)


def login(email: str, password: str) -> tuple[CurrentUser, str]:
    email = (email or "").strip().lower()
    account = _account_for(email)
    # 帳號不存在時仍走一次等長比較，避免用回應時間列舉有效的廠商 Email。
    expected = (account or {}).get("password", "") or "\x00"
    ok = hmac.compare_digest(password or "", expected)
    if not account or not ok:
        raise UserError("INVALID_CREDENTIALS", "Email 或密碼錯誤")

    vendor_id = int(account["vendor_id"])
    name = account.get("name") or email
    token = USERS.issue_token(sub=f"vendor-{vendor_id}", name=name, vendor_id=vendor_id)
    return CurrentUser(sub=f"vendor-{vendor_id}", name=name, vendor_id=vendor_id), token


def demo_accounts() -> list[dict]:
    """示範用的一鍵登入資料；只有內建帳號才附密碼，佈建的帳號永不外洩。"""
    settings = get_settings()
    if not settings.allow_demo_auth:
        return []
    return [
        {"email": email, "name": account.get("name") or email, "password": account["password"]}
        for email, account in settings.vendor_accounts.items()
        if account.get("builtin_demo")
    ]
