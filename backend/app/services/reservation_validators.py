"""Validation rules for the restaurant reservation flow."""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone

TZ = timezone(timedelta(hours=8))

_PHONE_RE = re.compile(r"^09\d{8}$")
_LUNCH_TIMES = [f"{h:02d}:{m:02d}" for h in range(11, 14) for m in (0, 30)]
_DINNER_TIMES = [f"{h:02d}:{m:02d}" for h in range(17, 21) for m in (0, 30)]


def validate_phone(phone: str) -> bool:
    """台灣手機號碼驗證：09 開頭、共 10 碼純數字 (Requirement 5.3)"""
    return bool(_PHONE_RE.match(phone))


def validate_contact_name(name: str) -> bool:
    """聯絡人姓名驗證：1-50 字元，不可為空白 (Requirement 5.1, 5.6)"""
    stripped = name.strip()
    return 1 <= len(stripped) <= 50


def validate_date(selected_date: str, today: date | None = None) -> bool:
    """日期驗證：今日起 60 天內 (Requirement 3.2, 3.5)"""
    try:
        d = date.fromisoformat(selected_date)
    except ValueError:
        return False
    reference = today or datetime.now(TZ).date()
    return reference <= d <= reference + timedelta(days=60)


def validate_people(people) -> bool:
    """人數驗證：1-20 人正整數 (Requirement 4.2, 4.5)"""
    if isinstance(people, bool) or not isinstance(people, int):
        return False
    return 1 <= people <= 20


def validate_time_slot(time_slot: str) -> bool:
    """時段驗證 (Requirement 3.4)"""
    return time_slot in ("LUNCH", "DINNER")


def validate_specific_time(time_slot: str, specific_time: str) -> bool:
    """30 分鐘間隔精細時間驗證 (Requirement 3.4)"""
    if time_slot == "LUNCH":
        return specific_time in _LUNCH_TIMES
    if time_slot == "DINNER":
        return specific_time in _DINNER_TIMES
    return False


def validate_preference_note(note: str | None) -> bool:
    """偏好需求文字驗證：最多 200 字 (Requirement 2.3)"""
    if note is None:
        return True
    return len(note) <= 200


def build_service_time(date_str: str, specific_time: str | None, time_slot: str) -> str:
    """
    組合 service_time ISO 8601 格式 (Requirement 7.3)
    若無 specific_time，使用時段預設時間（午餐 12:00, 晚餐 18:00）
    """
    if specific_time:
        return f"{date_str}T{specific_time}:00+08:00"
    default_time = "12:00" if time_slot == "LUNCH" else "18:00"
    return f"{date_str}T{default_time}:00+08:00"