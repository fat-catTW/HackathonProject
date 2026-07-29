"""Email 帳號註冊／登入（DynamoDB 儲存）。

使用者與 token 都存進共用單表（app.services.store.STORE），因此後端重啟或
多實例部署時帳號都不會消失。USE_MOCK=true 時 STORE 為記憶體實作，行為與
之前相同；要真正持久化必須設定 USE_MOCK=false（見 docs/aws-agent-setup.md）。

單表 item 的 PK/SK 版面由 BaseStore 決定（save_credential_if_absent /
save_user_profile / save_auth_token），此模組只負責帳號語意。

安全性：
- 密碼以 PBKDF2-HMAC-SHA256 + 隨機 salt 雜湊，永不明文儲存（salt／hash 以
  base64 存字串，避免 Binary 型別在不同後端間的差異）。
- 雜湊輪數隨憑證一起存，驗證時以該筆記錄的輪數計算，日後調高輪數不會讓
  既有帳號失效。
- sub 一律由後端產生，前端不得自行指定使用者 ID（設計書 §9.1、§17.2）。

正式版（Milestone 6）改用 Cognito：註冊／登入走 Cognito SignUp/InitiateAuth，
token 換成 Cognito JWT，此模組即可移除。
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import re
import secrets
import string
import threading
import time
import uuid
from contextlib import contextmanager
from typing import NamedTuple

from ..services.store import STORE, BaseStore, now_iso
from .cognito import CurrentUser

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PBKDF2_ROUNDS = 200_000
_TOKEN_TTL_SECONDS = 30 * 24 * 3600

# token → 使用者的本機快取，避免每個 API 請求都打一次 DynamoDB。撤銷（登出）
# 最久會延遲這段時間才在其他實例生效，因此刻意壓短。
_TOKEN_CACHE_SECONDS = 30
_TOKEN_CACHE_MAX_ENTRIES = 4096

# _issue_token 產生的 token 字元集與長度，用來在查表前濾掉 Cognito JWT 等
# 不可能是本模組發出的字串（JWT 含 "." 且可能超過 DynamoDB 分區鍵長度上限）。
_TOKEN_LENGTH = 43  # secrets.token_urlsafe(32)
_TOKEN_ALPHABET = frozenset(string.ascii_letters + string.digits + "-_")


class UserError(Exception):
    """帶錯誤碼的使用者操作例外，供 API 層轉成統一錯誤格式。"""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class _CachedToken(NamedTuple):
    cached_until: float  # epoch 秒；同時不會超過 token 本身的到期時間
    sub: str
    name: str


def _hash_password(password: str, salt: bytes, rounds: int = _PBKDF2_ROUNDS) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, rounds)


def _b64(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def _decode_stored_secret(value: str | bytes | None) -> bytes:
    """還原 salt／雜湊欄位；資料缺漏或損毀時回傳 b""，交由比對步驟判定失敗。"""
    if not value:
        return b""
    if isinstance(value, bytes):
        return value
    try:
        return base64.b64decode(value)
    except Exception:  # noqa: BLE001
        return b""


def _is_issued_token(token: str) -> bool:
    return len(token) == _TOKEN_LENGTH and _TOKEN_ALPHABET.issuperset(token)


@contextmanager
def _storage_errors():
    """把儲存層例外轉成 UserError，避免 DynamoDB 故障變成未處理的 500。"""
    try:
        yield
    except UserError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise UserError("STORAGE_UNAVAILABLE", "帳號服務暫時無法使用，請稍後再試") from exc


class UserStore:
    """DynamoDB 使用者表，模擬 Cognito User Pool。"""

    def __init__(self, store: BaseStore | None = None) -> None:
        self._store = store or STORE
        self._lock = threading.Lock()
        self._token_cache: dict[str, _CachedToken] = {}

    # ---- 註冊 ----
    def register(self, email: str, password: str, name: str) -> tuple[CurrentUser, str]:
        email = (email or "").strip().lower()
        name = (name or "").strip()
        if not _EMAIL_RE.match(email):
            raise UserError("INVALID_EMAIL", "Email 格式不正確")
        if len(password or "") < 8:
            raise UserError("WEAK_PASSWORD", "密碼至少需 8 碼")
        if not name:
            name = email.split("@")[0]

        salt = os.urandom(16)
        sub = f"user-{uuid.uuid4().hex[:12]}"
        created_at = now_iso()

        # 先寫 profile 再寫憑證：憑證是唯一能登入的入口，最後才建立，
        # 中途失敗只會留下一筆沒有人能登入的孤兒 profile。
        with _storage_errors():
            self._store.save_user_profile(
                sub,
                {"sub": sub, "email": email, "name": name, "created_at": created_at},
            )
            # 條件寫入：同一 Email 併發註冊只有一筆會成功。
            claimed = self._store.save_credential_if_absent(
                email,
                {
                    "sub": sub,
                    "email": email,
                    "name": name,
                    "salt": _b64(salt),
                    "pw_hash": _b64(_hash_password(password, salt)),
                    "pbkdf2_rounds": _PBKDF2_ROUNDS,
                    "created_at": created_at,
                },
            )

        if not claimed:
            self._discard_profile(sub)
            raise UserError("EMAIL_EXISTS", "此 Email 已註冊")

        token = self._issue_token(sub, name)
        return CurrentUser(sub=sub, name=name), token

    # ---- 登入 ----
    def login(self, email: str, password: str) -> tuple[CurrentUser, str]:
        email = (email or "").strip().lower()
        with _storage_errors():
            user = self._store.get_credential(email)
        # 以固定 dummy 雜湊維持等時比較，避免以耗時差異列舉 Email。
        salt = _decode_stored_secret(user.get("salt")) if user else b"\x00" * 16
        rounds = int(user.get("pbkdf2_rounds") or _PBKDF2_ROUNDS) if user else _PBKDF2_ROUNDS
        expected = _decode_stored_secret(user.get("pw_hash")) if user else _hash_password("", salt)
        ok = hmac.compare_digest(_hash_password(password or "", salt, rounds), expected)
        if not user or not ok:
            raise UserError("INVALID_CREDENTIALS", "Email 或密碼錯誤")
        sub = user["sub"]
        name = user.get("name") or email.split("@")[0]
        token = self._issue_token(sub, name)
        return CurrentUser(sub=sub, name=name), token

    # ---- token 換使用者 ----
    def resolve(self, token: str) -> CurrentUser | None:
        if not token or not _is_issued_token(token):
            return None
        now = time.time()
        with self._lock:
            cached = self._token_cache.get(token)
            if cached and cached.cached_until > now:
                return CurrentUser(sub=cached.sub, name=cached.name, access_token=token)
            if cached:
                self._token_cache.pop(token, None)

        try:
            item = self._store.get_auth_token(token)
        except Exception:  # noqa: BLE001 - DynamoDB 暫時不可用時視為未授權
            return None
        if not item:
            return None
        expires_at = float(item.get("ttl") or 0)
        if expires_at <= now:
            # 過期 token 主動清掉，不必等 DynamoDB TTL。
            self.logout(token)
            return None

        sub = item.get("sub")
        if not sub:
            return None
        name = item.get("name") or ""
        if not name:
            profile = self._store.get_user_profile(sub) or {}
            name = profile.get("name", "")
        self._cache_token(token, sub, name, expires_at)
        return CurrentUser(sub=sub, name=name, access_token=token)

    def logout(self, token: str) -> None:
        with self._lock:
            self._token_cache.pop(token, None)
        try:
            self._store.delete_auth_token(token)
        except Exception:  # noqa: BLE001 - 登出失敗不應讓請求整個失敗
            pass

    def _issue_token(self, sub: str, name: str) -> str:
        token = secrets.token_urlsafe(32)
        expires_at = int(time.time() + _TOKEN_TTL_SECONDS)
        with _storage_errors():
            self._store.save_auth_token(
                token,
                {
                    "sub": sub,
                    "name": name,
                    "issued_at": now_iso(),
                    "ttl": expires_at,  # DynamoDB TTL 屬性，同時是本模組的到期判斷依據
                },
            )
        self._cache_token(token, sub, name, expires_at)
        return token

    def _cache_token(self, token: str, sub: str, name: str, expires_at: float) -> None:
        now = time.time()
        cached_until = min(now + _TOKEN_CACHE_SECONDS, expires_at)
        with self._lock:
            if len(self._token_cache) >= _TOKEN_CACHE_MAX_ENTRIES:
                self._sweep_cache_locked(now)
            self._token_cache[token] = _CachedToken(cached_until, sub, name)

    def _sweep_cache_locked(self, now: float) -> None:
        """清掉過期項目；仍然滿了就整個丟掉（快取遺失只是多打一次 DynamoDB）。"""
        for key in [k for k, v in self._token_cache.items() if v.cached_until <= now]:
            self._token_cache.pop(key, None)
        if len(self._token_cache) >= _TOKEN_CACHE_MAX_ENTRIES:
            self._token_cache.clear()

    def _discard_profile(self, sub: str) -> None:
        try:
            self._store.delete_item(f"USER#{sub}", "PROFILE")
        except Exception:  # noqa: BLE001 - 清理失敗只留下無法登入的孤兒 profile
            pass


USERS = UserStore()
