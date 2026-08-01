"""Real clinic directory, backed by Taiwan's NHI (衛福部健保署) open-data API
for contracted clinics (資源 ID A21030000I-D21004-009 — confirmed live,
free, no API key required, updated daily). Falls back to a small static
list on any fetch failure, matching health_recommendation.py's convention.

District filtering is done by substring match on the ADDRESS field rather
than the dataset's GOVAREANO code, since that code's numbering scheme isn't
confirmed to line up with this project's tw_regions.json district codes —
address-text matching is simpler to verify and debug.
"""
from __future__ import annotations

import json
import time
from datetime import datetime

import httpx

_NHI_ENDPOINT = "https://info.nhi.gov.tw/api/iode0010/v1/rest/datastore/A21030000I-D21004-009"
_PAGE_SIZE = 1000
_MAX_PAGES = 5
_CACHE_TTL_SECONDS = 24 * 3600
_TIMEOUT_SECONDS = 10.0

_WEEKDAY_CNAME = ("星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日")
_SESSION_BY_HOUR = (
    (8, 12, "上午"),
    (12, 18, "下午"),
    (18, 22, "晚上"),
)

_ALWAYS_OPEN_DUTY = "、".join(
    f"{weekday}{session}看診" for weekday in _WEEKDAY_CNAME for _, _, session in _SESSION_BY_HOUR
)

_FALLBACK_CLINICS: list[dict] = [
    {
        "id": "clinic-fallback-001",
        "name": "王耳鼻喉科診所",
        "specialties": ["耳鼻喉科"],
        "address": "台中市西屯區文心路三段100號",
        "phone": "04-2312-3456",
        "holiday_duty_cname": _ALWAYS_OPEN_DUTY,
    },
    {
        "id": "clinic-fallback-002",
        "name": "西屯家庭醫學科診所",
        "specialties": ["家醫科"],
        "address": "台中市西屯區台灣大道三段99號",
        "phone": "04-2312-9876",
        "holiday_duty_cname": _ALWAYS_OPEN_DUTY,
    },
    {
        "id": "clinic-fallback-003",
        "name": "康民內科診所",
        "specialties": ["內科"],
        "address": "台中市西屯區逢甲路50號",
        "phone": "04-2452-1122",
        "holiday_duty_cname": "",
    },
]

_cache: dict[str, tuple[float, list[dict]]] = {}


def _current_session_cname(now: datetime) -> tuple[str, str]:
    weekday_cname = _WEEKDAY_CNAME[now.weekday()]
    hour = now.hour
    for start, end, session_cname in _SESSION_BY_HOUR:
        if start <= hour < end:
            return weekday_cname, session_cname
    return weekday_cname, "晚上"


def _is_open_now(holiday_duty_cname: str, now: datetime | None = None) -> bool:
    now = now or datetime.now()
    weekday_cname, session_cname = _current_session_cname(now)
    marker = f"{weekday_cname}{session_cname}看診"
    return marker in (holiday_duty_cname or "")


def _fetch_page(offset: int) -> list[dict] | None:
    try:
        response = httpx.get(
            _NHI_ENDPOINT,
            params={"limit": _PAGE_SIZE, "offset": offset},
            timeout=_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, str):
            payload = json.loads(payload)
        return payload["result"]["records"]
    except Exception:
        return None


def _fetch_all_clinics() -> list[dict] | None:
    records: list[dict] = []
    for page in range(_MAX_PAGES):
        page_records = _fetch_page(page * _PAGE_SIZE)
        if page_records is None:
            return records or None
        records.extend(page_records)
        if len(page_records) < _PAGE_SIZE:
            break
    return records


def _normalize_record(record: dict) -> dict | None:
    hosp_id = record.get("HOSP_ID")
    name = record.get("HOSP_NAME")
    address = record.get("ADDRESS")
    if not hosp_id or not name or not address:
        return None
    functype = record.get("FUNCTYPE_CNAME") or ""
    specialties = [part.strip() for part in functype.split(",") if part.strip()]
    return {
        "id": hosp_id,
        "name": name,
        "specialties": specialties,
        "address": address,
        "phone": record.get("TEL") or "",
        "holiday_duty_cname": record.get("HOLIDAYDUTY_CNAME") or "",
    }


def _load_clinics() -> list[dict]:
    cached = _cache.get("all")
    if cached and (time.time() - cached[0]) < _CACHE_TTL_SECONDS:
        return cached[1]

    raw_records = _fetch_all_clinics()
    if raw_records:
        clinics = [c for c in (_normalize_record(r) for r in raw_records) if c is not None]
    else:
        clinics = []
    if not clinics:
        clinics = list(_FALLBACK_CLINICS)

    _cache["all"] = (time.time(), clinics)
    return clinics


def _to_public_shape(clinic: dict, now: datetime | None) -> dict:
    return {
        "id": clinic["id"],
        "name": clinic["name"],
        "specialties": clinic["specialties"],
        "address": clinic["address"],
        "phone": clinic["phone"],
        "is_open_now": _is_open_now(clinic["holiday_duty_cname"], now),
    }


def list_clinics(
    city: str, district: str, specialty: str | None = None, *, now: datetime | None = None
) -> list[dict]:
    area = f"{city}{district}"
    matches = [c for c in _load_clinics() if area in c["address"]]
    if specialty:
        matches = [c for c in matches if specialty in c["specialties"]]
    return [_to_public_shape(c, now) for c in matches]


def get_clinic(clinic_id: str, *, now: datetime | None = None) -> dict | None:
    clinic = next((c for c in _load_clinics() if c["id"] == clinic_id), None)
    return _to_public_shape(clinic, now) if clinic else None
