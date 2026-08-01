"""第三方 webhook 回呼的簡易身分驗證（shared secret）。

外送／訂位系統的狀態回呼目前沒有走 Cognito 或廠商登入（呼叫方是外部系統，不是
使用者），但也不能完全不驗證——沒有這道檢查，任何知道自己 request_id 的使用者
都能直接打這條路徑，繞過廠商後台把案件狀態改成任何值。先用一組共用密鑰擋掉最
明顯的濫用；真的要接上真實外送／訂位平台時，再依對方支援的機制升級成 HMAC 簽章。
"""
from __future__ import annotations

import hmac

from fastapi import Header, HTTPException

from ..config import get_settings


def verify_webhook_secret(x_webhook_secret: str | None = Header(default=None)) -> None:
    expected = get_settings().webhook_shared_secret
    # 沒設定密鑰就一律拒絕：正式環境忘記設定 WEBHOOK_SHARED_SECRET 時，寧可回呼全部
    # 失敗也不要讓這條路徑變成無驗證。
    if not expected or not hmac.compare_digest(x_webhook_secret or "", expected):
        raise HTTPException(
            status_code=401,
            detail={"success": False, "error": {"code": "UNAUTHORIZED", "message": "Invalid webhook secret."}},
        )
