"""Retry queue for failed third-party booking calls (Requirement 9)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

TZ = timezone(timedelta(hours=8))


def mark_for_retry(order: dict) -> None:
    order["retry_info"] = {
        "retry_count": order.get("retry_info", {}).get("retry_count", 0),
        "max_retries": 3,
        "last_retry_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "needs_manual": False,
    }
