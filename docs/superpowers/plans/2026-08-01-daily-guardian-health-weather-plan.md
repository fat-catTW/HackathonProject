# 日常的守護（天氣卡片 + 健康諮詢掛號情境）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build (1) a home-page weather card with tap-to-listen voice readout, and (2) a symptom → real-clinic-recommendation → appointment → cross-sell → family-share flow, per `docs/superpowers/specs/2026-08-01-daily-guardian-health-weather-design.md`.

**Architecture:** Follows this repo's established "dedicated flow page" pattern (same shape as `restaurant_reservation`/`ReservationFlowPage`) rather than extending the 2000-line `agent.py` conversational state machine. Real clinic data comes from Taiwan's NHI (健保署) open data API, filtered client-side by address text. Two new Bedrock-backed judgment functions (mirroring the existing `_converse_json` pattern in `llm.py`) rank clinics and cross-sell products from that real data; everything degrades to deterministic rule-based fallbacks when Bedrock/the external API is unavailable, matching every other feature in this codebase.

**Tech Stack:** FastAPI + Python 3.12 backend, React + TypeScript + Vite + Tailwind frontend, pytest + vitest/@testing-library for tests, httpx for outbound HTTP, `window.speechSynthesis` for TTS.

## Global Constraints

- Every external call (Open-Meteo, NHI open data, Bedrock) MUST have a deterministic fallback — no feature may hard-fail because a network call failed. This mirrors `health_recommendation.py`'s existing Gemini-fallback convention.
- No new secrets/config are required to run this locally in mock mode — Open-Meteo and the NHI dataset need no API key; Bedrock already falls back via `llm.is_available()` when AWS credentials are absent.
- Do not modify the existing `health_recommendation.py` Gemini-based recommendation engine or the `HealthRecommendationPage` — they are explicitly out of scope per the spec.
- Do not modify `agent.py`'s state machine beyond the one `_handle_one_shot_service` branch described in Task 8 — no new conversational field-collection logic.
- All backend tests run from the repo root (`c:/Users/user/Desktop/HackathonProject-main/HackathonProject-main`) with `python -m pytest backend/tests/<file> -v` (confirmed working convention — tests import `from backend.app.main import app`).
- All frontend tests run from `frontend/` with `npm test -- <file>` (vitest).
- Traditional Chinese for all user-facing strings, matching the rest of the app.

---

## File Structure

**Backend (new):**
- `backend/app/services/weather.py` — Open-Meteo client + fallback + cache
- `backend/app/api/weather.py` — `GET /api/weather`
- `backend/app/services/clinic_catalog.py` — NHI open-data client + fallback + cache + filtering
- `backend/app/services/clinic_appointment.py` — appointment order creation (mirrors `reservation.py`)
- `backend/app/api/clinics.py` — clinic/symptom-triage/appointment/cross-sell endpoints
- `backend/tests/test_weather_service.py`, `test_weather_api.py`, `test_clinic_catalog.py`, `test_llm_clinic_functions.py`, `test_health_catalog_cold_products.py`, `test_clinic_appointment_service.py`, `test_clinics_api.py`, `test_agent_clinic_redirect.py`

**Backend (modified):**
- `backend/app/agent/llm.py` — add `triage_symptom`, `recommend_clinic`, `recommend_health_products_for_symptom`
- `backend/app/services/health_catalog.py` — add 4 cold/throat products
- `backend/app/services/health_recommendation.py` — extend `HEALTH_KEYWORDS`
- `backend/app/services/catalog.py` — register `clinic_appointment` service
- `backend/app/agent/page_catalog.py` — add `service_form_clinic_appointment` alias keywords
- `backend/app/agent/agent.py` — one redirect branch in `_handle_one_shot_service`
- `backend/app/main.py` — register the two new routers
- `lambda_tools/page_knowledge/pages.json` — add the `service_form_clinic_appointment` page entry

**Frontend (new):**
- `frontend/src/types/weather.ts`, `frontend/src/api/weather.ts`
- `frontend/src/hooks/useSpeechSynthesis.ts` (+ `.test.ts`)
- `frontend/src/components/WeatherGreetingCard.tsx` (+ `.test.tsx`)
- `frontend/src/types/clinic.ts`, `frontend/src/api/clinics.ts`
- `frontend/src/components/ClinicCard.tsx`, `frontend/src/components/ClinicCardList.tsx` (+ `.test.tsx`)
- `frontend/src/components/ClinicSummaryCard.tsx` (+ `.test.tsx`)
- `frontend/src/pages/ClinicConsultFlowPage.tsx` (+ `.test.tsx`)

**Frontend (modified):**
- `frontend/src/pages/HomePage.tsx` — mount `WeatherGreetingCard`
- `frontend/src/data/services.ts` — register `clinic_appointment` service definition
- `frontend/src/App.tsx` — add `/services/clinic_appointment` route

---

### Task 1: Weather service (Open-Meteo + fallback + cache)

**Files:**
- Create: `backend/app/services/weather.py`
- Test: `backend/tests/test_weather_service.py`

**Interfaces:**
- Produces: `weather.DEFAULT_CITY: str`, `weather.get_weather(city: str | None = None) -> dict` returning `{"city": str, "temperature": float, "high": float, "low": float, "condition": str, "is_large_temp_swing": bool, "fallback_used": bool}`

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_weather_service.py
from backend.app.services import weather


def test_get_weather_uses_live_data_when_available(monkeypatch):
    monkeypatch.setattr(weather, "_CACHE", {})
    monkeypatch.setattr(
        weather,
        "_fetch_live_weather",
        lambda city: {
            "city": city,
            "temperature": 28.0,
            "high": 31.0,
            "low": 24.0,
            "condition": "多雲",
            "is_large_temp_swing": False,
            "fallback_used": False,
        },
    )
    result = weather.get_weather("台中市")
    assert result["fallback_used"] is False
    assert result["city"] == "台中市"
    assert result["temperature"] == 28.0


def test_get_weather_falls_back_when_live_fetch_fails(monkeypatch):
    monkeypatch.setattr(weather, "_CACHE", {})
    monkeypatch.setattr(weather, "_fetch_live_weather", lambda city: None)
    result = weather.get_weather("台中市")
    assert result["fallback_used"] is True
    assert result["city"] == "台中市"
    assert isinstance(result["temperature"], float)


def test_get_weather_defaults_to_default_city_when_blank(monkeypatch):
    monkeypatch.setattr(weather, "_CACHE", {})
    monkeypatch.setattr(weather, "_fetch_live_weather", lambda city: None)
    result = weather.get_weather("")
    assert result["city"] == weather.DEFAULT_CITY


def test_get_weather_caches_within_ttl(monkeypatch):
    monkeypatch.setattr(weather, "_CACHE", {})
    calls = {"count": 0}

    def fake_fetch(city):
        calls["count"] += 1
        return {
            "city": city,
            "temperature": 28.0,
            "high": 31.0,
            "low": 24.0,
            "condition": "多雲",
            "is_large_temp_swing": False,
            "fallback_used": False,
        }

    monkeypatch.setattr(weather, "_fetch_live_weather", fake_fetch)
    weather.get_weather("台中市")
    weather.get_weather("台中市")
    assert calls["count"] == 1


def test_fallback_weather_flags_large_temp_swing_for_known_city():
    result = weather._fallback_weather("台中市")
    assert result["high"] - result["low"] >= 7
    assert result["is_large_temp_swing"] is True


def test_fallback_weather_uses_generic_default_for_unknown_city():
    result = weather._fallback_weather("某個沒有資料的城市")
    assert result["city"] == "某個沒有資料的城市"
    assert result["fallback_used"] is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest backend/tests/test_weather_service.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'backend.app.services.weather'` (or `AttributeError`)

- [ ] **Step 3: Implement `weather.py`**

```python
# backend/app/services/weather.py
"""Home-page weather: Open-Meteo (no API key) with a deterministic static
fallback, matching the fallback convention used throughout this codebase
(see health_recommendation.py's Gemini fallback)."""
from __future__ import annotations

import time

import httpx

DEFAULT_CITY = "台中市"

_CACHE_TTL_SECONDS = 600
_TIMEOUT_SECONDS = 5.0
_CACHE: dict[str, tuple[float, dict]] = {}

_CONDITION_TEXT: dict[int, str] = {
    0: "晴朗", 1: "晴時多雲", 2: "多雲", 3: "陰天",
    45: "有霧", 48: "有霧",
    51: "毛毛雨", 53: "毛毛雨", 55: "毛毛雨",
    61: "小雨", 63: "中雨", 65: "大雨",
    71: "小雪", 73: "中雪", 75: "大雪",
    80: "陣雨", 81: "陣雨", 82: "強陣雨",
    95: "雷雨",
}

_FALLBACK_WEATHER: dict[str, dict] = {
    "台中市": {"temperature": 27.0, "high": 30.0, "low": 22.0, "condition": "晴時多雲"},
    "台北市": {"temperature": 25.0, "high": 28.0, "low": 21.0, "condition": "多雲"},
    "高雄市": {"temperature": 29.0, "high": 32.0, "low": 25.0, "condition": "晴朗"},
}
_DEFAULT_FALLBACK = {"temperature": 26.0, "high": 29.0, "low": 22.0, "condition": "多雲"}


def _condition_text(code: int) -> str:
    return _CONDITION_TEXT.get(code, "多雲")


def _fallback_weather(city: str) -> dict:
    data = _FALLBACK_WEATHER.get(city, _DEFAULT_FALLBACK)
    high, low = data["high"], data["low"]
    return {
        "city": city,
        "temperature": data["temperature"],
        "high": high,
        "low": low,
        "condition": data["condition"],
        "is_large_temp_swing": (high - low) >= 7,
        "fallback_used": True,
    }


def _geocode(city: str) -> tuple[float, float] | None:
    try:
        response = httpx.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city, "count": 1, "language": "zh", "format": "json"},
            timeout=_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        results = response.json().get("results")
        if not results:
            return None
        return results[0]["latitude"], results[0]["longitude"]
    except Exception:
        return None


def _fetch_forecast(lat: float, lon: float) -> dict | None:
    try:
        response = httpx.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,weather_code",
                "daily": "temperature_2m_max,temperature_2m_min",
                "timezone": "Asia/Taipei",
            },
            timeout=_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response.json()
    except Exception:
        return None


def _fetch_live_weather(city: str) -> dict | None:
    coords = _geocode(city)
    if coords is None:
        return None
    forecast = _fetch_forecast(*coords)
    if forecast is None:
        return None
    try:
        current = forecast["current"]
        daily = forecast["daily"]
        temperature = float(current["temperature_2m"])
        high = float(daily["temperature_2m_max"][0])
        low = float(daily["temperature_2m_min"][0])
        condition = _condition_text(int(current["weather_code"]))
    except (KeyError, IndexError, TypeError, ValueError):
        return None
    return {
        "city": city,
        "temperature": temperature,
        "high": high,
        "low": low,
        "condition": condition,
        "is_large_temp_swing": (high - low) >= 7,
        "fallback_used": False,
    }


def get_weather(city: str | None = None) -> dict:
    city = (city or DEFAULT_CITY).strip() or DEFAULT_CITY

    cached = _CACHE.get(city)
    if cached and (time.time() - cached[0]) < _CACHE_TTL_SECONDS:
        return cached[1]

    result = _fetch_live_weather(city) or _fallback_weather(city)
    _CACHE[city] = (time.time(), result)
    return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest backend/tests/test_weather_service.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/weather.py backend/tests/test_weather_service.py
git commit -m "feat: add weather service with Open-Meteo and static fallback"
```

---

### Task 2: Weather API endpoint

**Files:**
- Create: `backend/app/api/weather.py`
- Modify: `backend/app/main.py:6` (import), `backend/app/main.py:22-34` (include_router)
- Test: `backend/tests/test_weather_api.py`

**Interfaces:**
- Consumes: `weather.get_weather(city: str | None) -> dict` (Task 1)
- Produces: `GET /api/weather?city=` returning the same dict shape

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_weather_api.py
from fastapi.testclient import TestClient

from backend.app.main import app


def auth_headers(client: TestClient) -> dict:
    response = client.get("/api/auth/demo-accounts")
    token = response.json()["accounts"][0]["token"]
    return {"Authorization": f"Bearer {token}"}


def test_get_weather_returns_default_city_data():
    client = TestClient(app)
    headers = auth_headers(client)
    response = client.get("/api/weather", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["city"] == "台中市"
    assert "temperature" in body


def test_get_weather_accepts_city_query_param():
    client = TestClient(app)
    headers = auth_headers(client)
    response = client.get("/api/weather?city=台北市", headers=headers)
    assert response.status_code == 200
    assert response.json()["city"] == "台北市"


def test_get_weather_requires_auth():
    client = TestClient(app)
    response = client.get("/api/weather")
    assert response.status_code in (401, 403)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_weather_api.py -v`
Expected: FAIL with 404 (route not registered)

- [ ] **Step 3: Implement the endpoint**

```python
# backend/app/api/weather.py
from fastapi import APIRouter, Depends

from ..auth.cognito import CurrentUser, get_current_user
from ..services import weather

router = APIRouter()


@router.get("/api/weather")
def get_weather(city: str | None = None, user: CurrentUser = Depends(get_current_user)):
    return weather.get_weather(city)
```

Modify `backend/app/main.py` line 6:
```python
from .api import auth, calendar, chat, clinics, delivery, health, onboarding, requests, reservations, scam_check, services, sessions, shop, vendor, weather
```
(add `clinics` and `weather` even though `clinics` isn't built until Task 7 — importing it now would fail; instead, for this task only add `weather` and leave `clinics` for Task 7's own main.py edit. Use exactly this line for Task 2:)
```python
from .api import auth, calendar, chat, delivery, health, onboarding, requests, reservations, scam_check, services, sessions, shop, vendor, weather
```
Add after line 34 (`app.include_router(onboarding.router)`):
```python
app.include_router(weather.router)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_weather_api.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/weather.py backend/app/main.py backend/tests/test_weather_api.py
git commit -m "feat: expose GET /api/weather endpoint"
```

---

### Task 3: Clinic catalog (NHI open data + fallback + cache + filtering)

**Files:**
- Create: `backend/app/services/clinic_catalog.py`
- Test: `backend/tests/test_clinic_catalog.py`

**Interfaces:**
- Produces:
  - `clinic_catalog.list_clinics(city: str, district: str, specialty: str | None = None, *, now: datetime | None = None) -> list[dict]` — each dict: `{"id": str, "name": str, "specialties": list[str], "address": str, "phone": str, "is_open_now": bool}`
  - `clinic_catalog.get_clinic(clinic_id: str, *, now: datetime | None = None) -> dict | None` — same shape as one list item

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_clinic_catalog.py
from datetime import datetime

import pytest

from backend.app.services import clinic_catalog


@pytest.fixture(autouse=True)
def clear_cache():
    clinic_catalog._cache.clear()
    yield
    clinic_catalog._cache.clear()


MONDAY_10AM = datetime(2026, 8, 3, 10, 0)  # 2026-08-03 is a Monday


def test_list_clinics_falls_back_to_static_list_when_fetch_fails(monkeypatch):
    monkeypatch.setattr(clinic_catalog, "_fetch_all_clinics", lambda: None)
    results = clinic_catalog.list_clinics("台中市", "西屯區", now=MONDAY_10AM)
    assert len(results) > 0
    assert all("台中市西屯區" in c["address"] for c in results)


def test_list_clinics_filters_by_specialty(monkeypatch):
    monkeypatch.setattr(clinic_catalog, "_fetch_all_clinics", lambda: None)
    results = clinic_catalog.list_clinics("台中市", "西屯區", "耳鼻喉科", now=MONDAY_10AM)
    assert len(results) >= 1
    assert all("耳鼻喉科" in c["specialties"] for c in results)


def test_list_clinics_excludes_other_districts(monkeypatch):
    monkeypatch.setattr(clinic_catalog, "_fetch_all_clinics", lambda: None)
    results = clinic_catalog.list_clinics("高雄市", "苓雅區", now=MONDAY_10AM)
    assert results == []


def test_get_clinic_returns_none_for_unknown_id(monkeypatch):
    monkeypatch.setattr(clinic_catalog, "_fetch_all_clinics", lambda: None)
    assert clinic_catalog.get_clinic("nope", now=MONDAY_10AM) is None


def test_get_clinic_returns_expected_shape(monkeypatch):
    monkeypatch.setattr(clinic_catalog, "_fetch_all_clinics", lambda: None)
    clinic = clinic_catalog.get_clinic("clinic-fallback-001", now=MONDAY_10AM)
    assert clinic["name"] == "王耳鼻喉科診所"
    assert clinic["is_open_now"] is True


def test_is_open_now_true_when_duty_string_matches_current_session():
    assert clinic_catalog._is_open_now("星期一上午看診", now=MONDAY_10AM) is True


def test_is_open_now_false_when_duty_string_says_closed():
    assert clinic_catalog._is_open_now("星期一上午休診", now=MONDAY_10AM) is False


def test_normalize_record_splits_comma_separated_specialties():
    record = {
        "HOSP_ID": "12345",
        "HOSP_NAME": "測試診所",
        "ADDRESS": "台中市西屯區測試路1號",
        "TEL": "04-1234567",
        "FUNCTYPE_CNAME": "內科,眼科,復健科",
        "HOLIDAYDUTY_CNAME": "星期一上午看診",
    }
    normalized = clinic_catalog._normalize_record(record)
    assert normalized["specialties"] == ["內科", "眼科", "復健科"]


def test_normalize_record_returns_none_when_missing_required_fields():
    assert clinic_catalog._normalize_record({"HOSP_ID": "1"}) is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest backend/tests/test_clinic_catalog.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement `clinic_catalog.py`**

```python
# backend/app/services/clinic_catalog.py
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest backend/tests/test_clinic_catalog.py -v`
Expected: PASS (9 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/clinic_catalog.py backend/tests/test_clinic_catalog.py
git commit -m "feat: add clinic catalog backed by NHI open data with static fallback"
```

---

### Task 4: Bedrock judgment functions (symptom triage, clinic recommendation, product cross-sell)

**Files:**
- Modify: `backend/app/agent/llm.py` (add new system prompts near line 131, after `_SCAM_CHECK_SYSTEM`; add new functions near line 235, after `check_scam_message`)
- Test: `backend/tests/test_llm_clinic_functions.py`

**Interfaces:**
- Consumes: `llm._converse_json(system, prompt, max_tokens) -> dict | None` (existing), `llm.is_available()` (existing), `health_recommendation.fallback_recommend(query, products) -> list[dict]` (existing)
- Produces:
  - `llm.triage_symptom(symptom_text: str) -> dict` — always returns `{"specialty": str, "advisory": str}` (never None; falls back internally)
  - `llm.recommend_clinic(symptom_text: str, candidates: list[dict]) -> dict | None` — `candidates` are `clinic_catalog.list_clinics()` results (each with `"id"` key); returns `{"id": str, "reason": str}` or `None` if `candidates` is empty
  - `llm.recommend_health_products_for_symptom(symptom_text: str, products: list[dict]) -> dict` — `products` are `health_catalog.list_products()` results; returns `{"recommendations": [{"product_id": str, "reason": str}], "fallback_used": bool}`

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_llm_clinic_functions.py
from unittest.mock import patch

from backend.app.agent import llm
from backend.app.services import health_catalog


def test_triage_symptom_falls_back_to_keyword_rules_without_bedrock():
    with patch("backend.app.agent.llm.is_available", return_value=False):
        result = llm.triage_symptom("我一直咳嗽，喉嚨很癢")
    assert result["specialty"] == "耳鼻喉科"
    assert result["advisory"]


def test_triage_symptom_defaults_to_family_medicine_for_unmatched_symptoms():
    with patch("backend.app.agent.llm.is_available", return_value=False):
        result = llm.triage_symptom("完全不相關的描述xyz")
    assert result["specialty"] == "家醫科"


def test_triage_symptom_uses_bedrock_result_when_valid():
    with patch(
        "backend.app.agent.llm._converse_json",
        return_value={"specialty": "耳鼻喉科", "advisory": "多喝溫水喔"},
    ):
        result = llm.triage_symptom("喉嚨癢癢的")
    assert result == {"specialty": "耳鼻喉科", "advisory": "多喝溫水喔"}


def test_triage_symptom_ignores_bedrock_result_with_invalid_specialty():
    with patch(
        "backend.app.agent.llm._converse_json",
        return_value={"specialty": "不存在的科別", "advisory": "..."},
    ):
        result = llm.triage_symptom("喉嚨癢癢的")
    assert result["specialty"] in llm._VALID_SPECIALTIES


def test_recommend_clinic_returns_none_for_empty_candidates():
    assert llm.recommend_clinic("咳嗽", []) is None


def test_recommend_clinic_falls_back_to_first_open_candidate_without_bedrock():
    candidates = [
        {"id": "c1", "name": "A診所", "is_open_now": False},
        {"id": "c2", "name": "B診所", "is_open_now": True},
    ]
    with patch("backend.app.agent.llm._converse_json", return_value=None):
        result = llm.recommend_clinic("咳嗽", candidates)
    assert result["id"] == "c2"


def test_recommend_clinic_uses_bedrock_choice_when_id_is_valid():
    candidates = [{"id": "c1", "name": "A診所", "is_open_now": True}]
    with patch(
        "backend.app.agent.llm._converse_json",
        return_value={"id": "c1", "reason": "距離最近"},
    ):
        result = llm.recommend_clinic("咳嗽", candidates)
    assert result == {"id": "c1", "reason": "距離最近"}


def test_recommend_clinic_ignores_bedrock_choice_with_unknown_id():
    candidates = [{"id": "c1", "name": "A診所", "is_open_now": True}]
    with patch(
        "backend.app.agent.llm._converse_json",
        return_value={"id": "does-not-exist", "reason": "..."},
    ):
        result = llm.recommend_clinic("咳嗽", candidates)
    assert result["id"] == "c1"


def test_recommend_health_products_falls_back_to_keyword_matching_without_bedrock():
    products = health_catalog.list_products()
    with patch("backend.app.agent.llm._converse_json", return_value=None):
        result = llm.recommend_health_products_for_symptom("喉嚨癢癢的，一直咳嗽", products)
    assert result["fallback_used"] is True
    assert len(result["recommendations"]) > 0


def test_recommend_health_products_uses_bedrock_choice_when_valid():
    products = health_catalog.list_products()
    valid_id = products[0]["id"]
    with patch(
        "backend.app.agent.llm._converse_json",
        return_value={"recommendations": [{"product_id": valid_id, "reason": "適合喉嚨不適"}]},
    ):
        result = llm.recommend_health_products_for_symptom("喉嚨癢", products)
    assert result["fallback_used"] is False
    assert result["recommendations"] == [{"product_id": valid_id, "reason": "適合喉嚨不適"}]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest backend/tests/test_llm_clinic_functions.py -v`
Expected: FAIL with `AttributeError: module 'backend.app.agent.llm' has no attribute 'triage_symptom'`

- [ ] **Step 3: Implement the additions to `llm.py`**

Insert after `_SCAM_CHECK_SYSTEM` (after line 131, before the `_DEBUG_STATE = threading.local()` line):

```python
_VALID_SPECIALTIES = ("耳鼻喉科", "家醫科", "內科", "腸胃科", "皮膚科", "骨科", "眼科", "牙科")

_SYMPTOM_KEYWORD_SPECIALTY: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("耳鼻喉科", ("咳嗽", "喉嚨", "鼻塞", "流鼻水", "打噴嚏")),
    ("腸胃科", ("肚子痛", "腹瀉", "拉肚子", "胃痛", "噁心", "嘔吐")),
    ("骨科", ("腰痛", "膝蓋", "關節", "扭傷", "骨折")),
    ("皮膚科", ("皮膚", "紅疹", "起疹子")),
    ("眼科", ("眼睛", "視力")),
)
_DEFAULT_SPECIALTY = "家醫科"
_DEFAULT_ADVISORY = "身體不舒服要多休息、多喝溫水，有需要就去診所讓醫生看看喔。"

_SYMPTOM_TRIAGE_SYSTEM = (
    "You triage a Traditional-Chinese-speaking elderly user's described physical symptoms for a "
    "Taiwanese home services assistant. "
    "Choose exactly one specialty from the provided valid_specialties list that best matches the "
    "symptoms. "
    "Write a short, warm, one-sentence piece of advice in Traditional Chinese (e.g. suggesting rest "
    "or drinking warm water) — do not diagnose or promise a cure. "
    "Return JSON only in the format {\"specialty\": string, \"advisory\": string}."
)

_CLINIC_RECOMMEND_SYSTEM = (
    "You recommend one clinic from a list of real candidate clinics for a Traditional-Chinese-speaking "
    "elderly user in Taiwan, based on their described symptoms. "
    "Only choose an id that appears in the provided candidates — never invent one. "
    "Prefer clinics where is_open_now is true when possible, and give a concrete one-sentence reason "
    "in Traditional Chinese. "
    "Return JSON only in the format {\"id\": string, \"reason\": string}."
)

_HEALTH_PRODUCT_SYSTEM = (
    "You are a product advisor recommending convenience-store products for a Traditional-Chinese-"
    "speaking elderly user based on their described physical symptoms. "
    "Only choose product_id values that appear in the provided products list — never invent one. "
    "Choose up to 3 products and explain each in one short Traditional Chinese sentence. "
    "Return JSON only in the format {\"recommendations\": [{\"product_id\": string, \"reason\": string}]}."
)
```

Insert after `check_scam_message` (after line 235, before `def choose_service`):

```python
def _fallback_triage_symptom(symptom_text: str) -> dict:
    for specialty, keywords in _SYMPTOM_KEYWORD_SPECIALTY:
        if any(keyword in symptom_text for keyword in keywords):
            return {"specialty": specialty, "advisory": _DEFAULT_ADVISORY}
    return {"specialty": _DEFAULT_SPECIALTY, "advisory": _DEFAULT_ADVISORY}


def triage_symptom(symptom_text: str) -> dict:
    payload = _converse_json(
        _SYMPTOM_TRIAGE_SYSTEM,
        json.dumps(
            {"symptom_text": symptom_text, "valid_specialties": list(_VALID_SPECIALTIES)},
            ensure_ascii=False,
        ),
        max_tokens=256,
    )
    if payload:
        specialty = payload.get("specialty")
        advisory = payload.get("advisory")
        if specialty in _VALID_SPECIALTIES and isinstance(advisory, str) and advisory.strip():
            return {"specialty": specialty, "advisory": advisory.strip()}
    return _fallback_triage_symptom(symptom_text)


def recommend_clinic(symptom_text: str, candidates: list[dict]) -> dict | None:
    if not candidates:
        return None
    payload = _converse_json(
        _CLINIC_RECOMMEND_SYSTEM,
        json.dumps({"symptom_text": symptom_text, "candidates": candidates}, ensure_ascii=False),
        max_tokens=256,
    )
    valid_ids = {c["id"] for c in candidates}
    if payload:
        clinic_id = payload.get("id")
        reason = payload.get("reason")
        if clinic_id in valid_ids and isinstance(reason, str) and reason.strip():
            return {"id": clinic_id, "reason": reason.strip()}
    open_candidates = [c for c in candidates if c.get("is_open_now")]
    fallback = (open_candidates or candidates)[0]
    return {"id": fallback["id"], "reason": "距離您所在地區近，且目前有看診，優先為您推薦。"}


def recommend_health_products_for_symptom(symptom_text: str, products: list[dict]) -> dict:
    payload = _converse_json(
        _HEALTH_PRODUCT_SYSTEM,
        json.dumps({"symptom_text": symptom_text, "products": products}, ensure_ascii=False),
        max_tokens=400,
    )
    valid_ids = {p["id"] for p in products}
    if payload and isinstance(payload.get("recommendations"), list):
        items = []
        for rec in payload["recommendations"]:
            if not isinstance(rec, dict):
                continue
            product_id = rec.get("product_id")
            reason = rec.get("reason")
            if product_id in valid_ids and isinstance(reason, str) and reason.strip():
                items.append({"product_id": product_id, "reason": reason.strip()})
        if items:
            return {"recommendations": items, "fallback_used": False}

    from ..services import health_recommendation

    fallback_items = health_recommendation.fallback_recommend(symptom_text, products)
    return {
        "recommendations": [{"product_id": r["product_id"], "reason": r["reason"]} for r in fallback_items],
        "fallback_used": True,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest backend/tests/test_llm_clinic_functions.py -v`
Expected: PASS (10 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/agent/llm.py backend/tests/test_llm_clinic_functions.py
git commit -m "feat: add Bedrock-backed symptom triage, clinic, and product recommendation"
```

---

### Task 5: Cold/throat health products + keyword extension

**Files:**
- Modify: `backend/app/services/health_catalog.py:56` (append 4 products to `PRODUCTS` list, before the closing `]`)
- Modify: `backend/app/services/health_recommendation.py:18-26` (extend `HEALTH_KEYWORDS`)
- Test: `backend/tests/test_health_catalog_cold_products.py`

**Interfaces:**
- Consumes: nothing new
- Produces: `health_catalog.list_products()` now includes 4 more items with ids `P039`–`P042`; `health_recommendation.HEALTH_KEYWORDS` gains `"感冒"`, `"喉嚨"`, `"咳嗽"` keys

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_health_catalog_cold_products.py
from backend.app.services import health_catalog, health_recommendation


def test_cold_relief_products_exist_in_catalog():
    products = health_catalog.list_products()
    ids = {p["id"] for p in products}
    assert {"P039", "P040", "P041", "P042"} <= ids


def test_throat_lozenge_product_has_expected_tags():
    product = health_catalog.get_product("P039")
    assert product["name"] == "無糖喉糖"
    assert "喉嚨不適" in product["tags"]


def test_fallback_recommend_matches_cough_query_to_cold_products():
    products = health_catalog.list_products()
    recs = health_recommendation.fallback_recommend("我一直咳嗽，喉嚨很癢", products)
    matched_ids = {r["product_id"] for r in recs}
    assert matched_ids & {"P039", "P040", "P041", "P042"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest backend/tests/test_health_catalog_cold_products.py -v`
Expected: FAIL (`get_product("P039")` returns `None`, `AssertionError` on empty intersection)

- [ ] **Step 3: Add the products and keywords**

In `backend/app/services/health_catalog.py`, add before the closing `]` of `PRODUCTS` (after the `P038` entry):

```python
    {"id": "P039", "name": "無糖喉糖", "category": "藥妝保健", "price": 45, "calories": 15, "protein_g": 0, "carbs_g": 4, "fat_g": 0, "sodium_mg": 5, "tags": ["喉嚨不適", "感冒", "無糖"], "allergens": []},
    {"id": "P040", "name": "京都念慈菴川貝枇杷膏", "category": "藥妝保健", "price": 159, "calories": 60, "protein_g": 0, "carbs_g": 15, "fat_g": 0, "sodium_mg": 5, "tags": ["喉嚨不適", "感冒", "潤喉"], "allergens": []},
    {"id": "P041", "name": "維他命C發泡錠", "category": "藥妝保健", "price": 89, "calories": 10, "protein_g": 0, "carbs_g": 2, "fat_g": 0, "sodium_mg": 40, "tags": ["感冒", "保健"], "allergens": []},
    {"id": "P042", "name": "熱蜂蜜檸檬飲", "category": "飲品", "price": 55, "calories": 90, "protein_g": 0, "carbs_g": 22, "fat_g": 0, "sodium_mg": 10, "tags": ["喉嚨不適", "感冒", "潤喉"], "allergens": []},
```

In `backend/app/services/health_recommendation.py`, replace the `HEALTH_KEYWORDS` dict (lines 18-26) with:

```python
HEALTH_KEYWORDS: dict[str, list[str]] = {
    "減脂": ["減脂", "低碳", "低卡", "高蛋白"],
    "增肌": ["增肌", "高蛋白", "均衡"],
    "三高": ["低鈉", "低脂", "低糖"],
    "低鈉": ["低鈉"],
    "素食": ["素食"],
    "低糖": ["低糖"],
    "高纖": ["高纖"],
    "感冒": ["喉嚨不適", "感冒", "潤喉", "保健"],
    "喉嚨": ["喉嚨不適", "潤喉"],
    "咳嗽": ["喉嚨不適", "感冒", "潤喉"],
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest backend/tests/test_health_catalog_cold_products.py backend/tests/test_health_recommendation.py -v`
Expected: PASS (the pre-existing `test_recommend_falls_back_to_keyword_matching_without_gemini_key` failure noted during planning is caused by a `GEMINI_API_KEY` set in the local `.env`, unrelated to this change — do not try to fix it here)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/health_catalog.py backend/app/services/health_recommendation.py backend/tests/test_health_catalog_cold_products.py
git commit -m "feat: add cold/throat-relief products and matching keywords"
```

---

### Task 6: Clinic appointment order service

**Files:**
- Create: `backend/app/services/clinic_appointment.py`
- Test: `backend/tests/test_clinic_appointment_service.py`

**Interfaces:**
- Consumes: `clinic_catalog.get_clinic(clinic_id) -> dict | None` (Task 3), `STORE.next_request_id()`, `STORE.save_request(actor_id, request)`, `STORE.get_request(actor_id, request_id)`, `now_iso()` (all existing in `store.py`)
- Produces:
  - `clinic_appointment.create_appointment(actor_id: str, payload: dict) -> dict` — payload needs `clinic_id`, `appointment_date`, `appointment_time`, `contact_name`, `phone`, `symptom_note`; returns `{"success": True, "request_id": str, "status": "CONFIRMED"}` or `{"success": False, "error": {"code": str, "message": str}}`
  - `clinic_appointment.get_appointment(actor_id: str, request_id: str) -> dict | None`

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_clinic_appointment_service.py
import tempfile
from pathlib import Path

import pytest

from backend.app.services import clinic_appointment, clinic_catalog, store as store_module


@pytest.fixture(autouse=True)
def isolated_store(monkeypatch):
    clinic_catalog._cache.clear()
    monkeypatch.setattr(clinic_catalog, "_fetch_all_clinics", lambda: None)
    with tempfile.TemporaryDirectory() as tmp:
        test_store = store_module.MemoryStore(storage_path=Path(tmp) / "store.json")
        monkeypatch.setattr(store_module, "STORE", test_store)
        monkeypatch.setattr(clinic_appointment, "STORE", test_store)
        yield test_store


def valid_payload(**overrides):
    payload = {
        "clinic_id": "clinic-fallback-001",
        "appointment_date": "2026-08-02",
        "appointment_time": "15:00",
        "contact_name": "王添財",
        "phone": "0912345678",
        "symptom_note": "咳嗽、喉嚨癢",
    }
    payload.update(overrides)
    return payload


def test_create_appointment_succeeds_and_confirms_immediately():
    result = clinic_appointment.create_appointment("user-1", valid_payload())
    assert result["success"] is True
    assert result["status"] == "CONFIRMED"


def test_create_appointment_fails_for_unknown_clinic():
    result = clinic_appointment.create_appointment("user-1", valid_payload(clinic_id="nope"))
    assert result["success"] is False
    assert result["error"]["code"] == "CLINIC_NOT_FOUND"


def test_create_appointment_fails_for_missing_required_field():
    result = clinic_appointment.create_appointment("user-1", valid_payload(phone=""))
    assert result["success"] is False
    assert result["error"]["code"] == "INVALID_FORM_DATA"


def test_get_appointment_returns_saved_order_with_clinic_details():
    created = clinic_appointment.create_appointment("user-1", valid_payload())
    order = clinic_appointment.get_appointment("user-1", created["request_id"])
    assert order["order_items"]["clinic_name"] == "王耳鼻喉科診所"
    assert order["form_data"]["symptom_note"] == "咳嗽、喉嚨癢"


def test_get_appointment_returns_none_for_unknown_request_id():
    assert clinic_appointment.get_appointment("user-1", "nope") is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest backend/tests/test_clinic_appointment_service.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement `clinic_appointment.py`**

```python
# backend/app/services/clinic_appointment.py
"""Clinic appointment order — mirrors reservation.py's shape but always
confirms immediately (no third-party booking system to call for a demo
clinic), and reuses STORE.save_request's existing contact-field
encryption/masking (keyed by field name, not service_id)."""
from __future__ import annotations

from . import clinic_catalog
from .store import STORE, now_iso

_REQUIRED_FIELDS = (
    "clinic_id",
    "appointment_date",
    "appointment_time",
    "contact_name",
    "phone",
    "symptom_note",
)


def _error(code: str, message: str) -> dict:
    return {"success": False, "error": {"code": code, "message": message}}


def _validate_payload(payload: dict) -> dict | None:
    for field_id in _REQUIRED_FIELDS:
        if payload.get(field_id) in (None, ""):
            return _error("INVALID_FORM_DATA", f"Missing required field: {field_id}")
    if not clinic_catalog.get_clinic(payload["clinic_id"]):
        return _error("CLINIC_NOT_FOUND", "找不到指定的診所。")
    return None


def create_appointment(actor_id: str, payload: dict) -> dict:
    validation_error = _validate_payload(payload)
    if validation_error:
        return validation_error

    clinic = clinic_catalog.get_clinic(payload["clinic_id"])

    order_items = {
        "clinic_id": clinic["id"],
        "clinic_name": clinic["name"],
        "clinic_address": clinic["address"],
        "clinic_phone": clinic["phone"],
        "appointment_date": payload["appointment_date"],
        "appointment_time": payload["appointment_time"],
    }

    request_id = STORE.next_request_id()
    created_at = now_iso()
    order = {
        "request_id": request_id,
        "session_id": None,
        "service_id": "clinic_appointment",
        "service_name": "診所掛號",
        "order_items": order_items,
        "form_data": {
            "clinic_name": clinic["name"],
            "clinic_address": clinic["address"],
            "clinic_phone": clinic["phone"],
            "appointment_date": payload["appointment_date"],
            "appointment_time": payload["appointment_time"],
            "symptom_note": payload["symptom_note"],
            "contact_name": payload["contact_name"],
            "phone": payload["phone"],
        },
        "vendor_data": {},
        "status": "CONFIRMED",
        "status_history": [],
        "created_at": created_at,
    }
    order["status_history"].append({"status": "CONFIRMED", "at": created_at})

    try:
        STORE.save_request(actor_id, order)
    except Exception as exc:
        return _error("REQUEST_SAVE_FAILED", str(exc))

    return {"success": True, "request_id": request_id, "status": "CONFIRMED"}


def get_appointment(actor_id: str, request_id: str) -> dict | None:
    return STORE.get_request(actor_id, request_id)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest backend/tests/test_clinic_appointment_service.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/clinic_appointment.py backend/tests/test_clinic_appointment_service.py
git commit -m "feat: add clinic appointment order service"
```

---

### Task 7: Clinics API routes

**Files:**
- Create: `backend/app/api/clinics.py`
- Modify: `backend/app/main.py:6` (add `clinics` to the import), `backend/app/main.py` (add `app.include_router(clinics.router)` near the other routers)
- Test: `backend/tests/test_clinics_api.py`

**Interfaces:**
- Consumes: `clinic_catalog.list_clinics`/`get_clinic` (Task 3), `llm.triage_symptom`/`recommend_clinic`/`recommend_health_products_for_symptom` (Task 4), `clinic_appointment.create_appointment`/`get_appointment` (Task 6), `health_catalog.list_products()` (existing)
- Produces:
  - `GET /api/clinics?city=&district=&specialty=` → `{"clinics": [...]}`
  - `POST /api/symptom-triage` body `{"symptom_text": str, "city"?: str, "district"?: str}` → `{"specialty": str, "advisory": str, "clinics": [...], "recommended_clinic_id": str | None, "recommend_reason": str | None}`
  - `POST /api/clinic-appointments` body matching `clinic_appointment.create_appointment`'s payload → its return dict
  - `GET /api/clinic-appointments/{request_id}` → the saved order
  - `POST /api/clinic-appointments/{request_id}/cross-sell` → `{"recommendations": [...], "fallback_used": bool}`

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_clinics_api.py
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services import clinic_appointment, clinic_catalog, store as store_module
import tempfile
from pathlib import Path
import pytest


@pytest.fixture(autouse=True)
def isolated_store(monkeypatch):
    clinic_catalog._cache.clear()
    monkeypatch.setattr(clinic_catalog, "_fetch_all_clinics", lambda: None)
    with tempfile.TemporaryDirectory() as tmp:
        test_store = store_module.MemoryStore(storage_path=Path(tmp) / "store.json")
        monkeypatch.setattr(store_module, "STORE", test_store)
        monkeypatch.setattr(clinic_appointment, "STORE", test_store)
        yield test_store


@pytest.fixture
def client():
    return TestClient(app)


def auth_headers(client: TestClient) -> dict:
    response = client.get("/api/auth/demo-accounts")
    token = response.json()["accounts"][0]["token"]
    return {"Authorization": f"Bearer {token}"}


def valid_appointment_payload(**overrides):
    payload = {
        "clinic_id": "clinic-fallback-001",
        "appointment_date": "2026-08-02",
        "appointment_time": "15:00",
        "contact_name": "王添財",
        "phone": "0912345678",
        "symptom_note": "咳嗽、喉嚨癢",
    }
    payload.update(overrides)
    return payload


def test_list_clinics_endpoint_returns_filtered_results(client):
    headers = auth_headers(client)
    response = client.get("/api/clinics?city=台中市&district=西屯區", headers=headers)
    assert response.status_code == 200
    assert len(response.json()["clinics"]) > 0


def test_symptom_triage_endpoint_returns_specialty_and_clinics(client):
    headers = auth_headers(client)
    response = client.post(
        "/api/symptom-triage",
        json={"symptom_text": "我一直咳嗽，喉嚨很癢", "city": "台中市", "district": "西屯區"},
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["specialty"] == "耳鼻喉科"
    assert len(body["clinics"]) > 0
    assert body["recommended_clinic_id"] is not None


def test_symptom_triage_endpoint_requires_symptom_text(client):
    headers = auth_headers(client)
    response = client.post(
        "/api/symptom-triage", json={"symptom_text": "", "city": "台中市", "district": "西屯區"}, headers=headers
    )
    assert response.status_code == 400


def test_submit_appointment_creates_order(client):
    headers = auth_headers(client)
    response = client.post("/api/clinic-appointments", json=valid_appointment_payload(), headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "CONFIRMED"


def test_submit_appointment_unknown_clinic_returns_404(client):
    headers = auth_headers(client)
    response = client.post(
        "/api/clinic-appointments", json=valid_appointment_payload(clinic_id="nope"), headers=headers
    )
    assert response.status_code == 404


def test_get_appointment_detail(client):
    headers = auth_headers(client)
    created = client.post("/api/clinic-appointments", json=valid_appointment_payload(), headers=headers).json()
    response = client.get(f"/api/clinic-appointments/{created['request_id']}", headers=headers)
    assert response.status_code == 200
    assert response.json()["order_items"]["clinic_id"] == "clinic-fallback-001"


def test_get_appointment_detail_not_found_returns_404(client):
    headers = auth_headers(client)
    response = client.get("/api/clinic-appointments/nope", headers=headers)
    assert response.status_code == 404


def test_cross_sell_endpoint_returns_recommendations(client):
    headers = auth_headers(client)
    created = client.post("/api/clinic-appointments", json=valid_appointment_payload(), headers=headers).json()
    response = client.post(f"/api/clinic-appointments/{created['request_id']}/cross-sell", headers=headers)
    assert response.status_code == 200
    assert len(response.json()["recommendations"]) > 0


def test_cross_sell_endpoint_not_found_returns_404(client):
    headers = auth_headers(client)
    response = client.post("/api/clinic-appointments/nope/cross-sell", headers=headers)
    assert response.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest backend/tests/test_clinics_api.py -v`
Expected: FAIL with 404 on every route (not registered)

- [ ] **Step 3: Implement `clinics.py`**

```python
# backend/app/api/clinics.py
from fastapi import APIRouter, Depends, HTTPException

from ..agent import llm
from ..auth.cognito import CurrentUser, get_current_user
from ..services import clinic_appointment, clinic_catalog, health_catalog

router = APIRouter()


def _raise_api_error(status_code: int, code: str, message: str):
    raise HTTPException(status_code=status_code, detail={"success": False, "error": {"code": code, "message": message}})


@router.get("/api/clinics")
def list_clinics(
    city: str,
    district: str,
    specialty: str | None = None,
    user: CurrentUser = Depends(get_current_user),
):
    return {"clinics": clinic_catalog.list_clinics(city, district, specialty)}


@router.post("/api/symptom-triage")
def symptom_triage(payload: dict, user: CurrentUser = Depends(get_current_user)):
    symptom_text = str(payload.get("symptom_text") or "").strip()
    if not symptom_text:
        _raise_api_error(400, "INVALID_FORM_DATA", "請描述您的症狀。")
    city = str(payload.get("city") or "台中市").strip()
    district = str(payload.get("district") or "西屯區").strip()

    triage = llm.triage_symptom(symptom_text)
    candidates = clinic_catalog.list_clinics(city, district, triage["specialty"])
    recommendation = llm.recommend_clinic(symptom_text, candidates)

    return {
        "specialty": triage["specialty"],
        "advisory": triage["advisory"],
        "clinics": candidates,
        "recommended_clinic_id": recommendation["id"] if recommendation else None,
        "recommend_reason": recommendation["reason"] if recommendation else None,
    }


@router.post("/api/clinic-appointments")
def submit_appointment(payload: dict, user: CurrentUser = Depends(get_current_user)):
    result = clinic_appointment.create_appointment(user.sub, payload)
    if not result.get("success"):
        error = result.get("error", {})
        status_code = 404 if error.get("code") == "CLINIC_NOT_FOUND" else 400
        _raise_api_error(status_code, error.get("code", "APPOINTMENT_FAILED"), error.get("message", "掛號失敗"))
    return result


@router.get("/api/clinic-appointments/{request_id}")
def get_clinic_appointment_detail(request_id: str, user: CurrentUser = Depends(get_current_user)):
    order = clinic_appointment.get_appointment(user.sub, request_id)
    if not order:
        _raise_api_error(404, "REQUEST_NOT_FOUND", "找不到對應的掛號紀錄。")
    return order


@router.post("/api/clinic-appointments/{request_id}/cross-sell")
def cross_sell(request_id: str, user: CurrentUser = Depends(get_current_user)):
    order = clinic_appointment.get_appointment(user.sub, request_id)
    if not order:
        _raise_api_error(404, "REQUEST_NOT_FOUND", "找不到對應的掛號紀錄。")
    symptom_text = order["form_data"].get("symptom_note", "")
    return llm.recommend_health_products_for_symptom(symptom_text, health_catalog.list_products())
```

Modify `backend/app/main.py` line 6 to:
```python
from .api import auth, calendar, chat, clinics, delivery, health, onboarding, requests, reservations, scam_check, services, sessions, shop, vendor, weather
```
Add near the other `include_router` calls:
```python
app.include_router(clinics.router)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest backend/tests/test_clinics_api.py -v`
Expected: PASS (9 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/clinics.py backend/app/main.py backend/tests/test_clinics_api.py
git commit -m "feat: expose clinic, symptom-triage, appointment, and cross-sell endpoints"
```

---

### Task 8: Register `clinic_appointment` service + agent redirect

**Files:**
- Modify: `backend/app/services/catalog.py` (append a new service entry to the `SERVICES` list, after the `shop_price_compare` entry, before `restaurant_reservation`)
- Modify: `backend/app/agent/page_catalog.py:48-97` (add an entry to `SERVICE_FORM_ALIASES`)
- Modify: `backend/app/agent/agent.py` (add one branch inside `_handle_one_shot_service`, around line 1095, right after the `shop_purchase` branch and before the `shop_price_compare` branch)
- Modify: `lambda_tools/page_knowledge/pages.json` (append a new page entry)
- Test: `backend/tests/test_agent_clinic_redirect.py`

**Interfaces:**
- Consumes: `_reply(state, reply, redirect_path=None, ...) -> dict` (existing, confirmed signature at `agent.py:2029`)
- Produces: `catalog.list_services()` includes `clinic_appointment`; a chat message that resolves to the `clinic_appointment` service redirects to `/services/clinic_appointment` instead of collecting form fields

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_agent_clinic_redirect.py
from unittest.mock import patch

from backend.app.agent import agent
from backend.app.services import catalog


def test_clinic_appointment_registered_in_service_list():
    services = catalog.list_services()
    ids = [s["id"] for s in services]
    assert "clinic_appointment" in ids


def test_agent_redirects_to_clinic_appointment_flow_page():
    state = agent.new_state()
    with patch(
        "backend.app.agent.agent._available_services",
        return_value=[
            {
                "id": "clinic_appointment",
                "name": "診所掛號",
                "description": "描述症狀，AI 幫您找附近診所並掛號",
                "keywords": ["掛號", "看醫生", "診所", "看診"],
            }
        ],
    ):
        result = agent.handle_message("user-1", "sess-1", state, "我想掛號看醫生")

    assert result["redirect_path"] == "/services/clinic_appointment"
    state = result["state"]
    assert state["service_id"] is None
    assert state["request_id"] is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_agent_clinic_redirect.py -v`
Expected: FAIL — `clinic_appointment` not in service list, and `redirect_path` is `None`

- [ ] **Step 3: Implement the registrations**

In `backend/app/services/catalog.py`, append this entry to the `SERVICES` list (anywhere after `shop_price_compare`'s closing `},`):

```python
    {
        "id": "clinic_appointment",
        "name": "診所掛號",
        "description": "描述症狀，AI 幫您找附近診所並掛號",
        "service_vendor_id": None,
        "cms_type": None,
        "enabled": True,
        "keywords": ["掛號", "看醫生", "診所", "看診", "身體不舒服", "門診"],
        "schema": {
            "fields": [
                {
                    "id": "symptom_note",
                    "label": "症狀描述",
                    "type": "textarea",
                    "required": True,
                    "question": "請問您哪裡不舒服呢？",
                },
            ],
        },
    },
```

In `backend/app/agent/page_catalog.py`, add to `SERVICE_FORM_ALIASES` (after the `service_form_health_product_recommendation` entry, before the closing `}`):

```python
    "service_form_clinic_appointment": (
        "掛號",
        "看醫生",
        "診所",
        "看診",
    ),
```

In `backend/app/agent/agent.py`, inside `_handle_one_shot_service`, insert this branch right after the `shop_purchase` block's `return _reply(...)` and before the `if service_id == "shop_price_compare":` line:

```python
    if service_id == "clinic_appointment":
        # Same treatment as shop_purchase: this needs a district/specialty
        # picker and a real-clinic recommendation step, not conversational
        # field collection — redirect to the dedicated flow page.
        state["service_id"] = None
        state["service_name"] = None
        state["service_schema"] = None
        state["collected_fields"] = {}
        state["missing_fields"] = []
        return _reply(
            state,
            "掛號需要先描述症狀、挑選診所和看診時段，這部分請到「診所掛號」頁面操作會更方便，我幫你導過去囉！",
            redirect_path="/services/clinic_appointment",
        )

```

In `lambda_tools/page_knowledge/pages.json`, append (as a new array element, comma-separated after the last existing entry):

```json
  {
    "page_id": "service_form_clinic_appointment",
    "route": "/services/clinic_appointment",
    "title": "診所掛號",
    "summary": "描述症狀，AI 依所在地區與科別推薦附近診所，並直接掛號。",
    "features": [
      "語音或文字描述症狀",
      "AI 建議科別與注意事項",
      "依縣市/鄉鎮區查詢真實診所資料並推薦一間",
      "選擇日期時段與聯絡資訊後直接掛號",
      "掛號成功後推薦對症商品並可加購",
      "自動產生可分享給家人的通知文字"
    ],
    "available_actions": [
      "描述症狀",
      "選擇縣市/鄉鎮區",
      "選擇診所",
      "選擇日期時段",
      "輸入聯絡人姓名",
      "輸入聯絡電話",
      "送出掛號申請",
      "加購推薦商品",
      "分享通知給家人"
    ],
    "next_steps": [
      "確認科別建議與推薦診所",
      "填妥日期時段與聯絡資訊",
      "確認資料無誤後送出掛號"
    ],
    "related_pages": ["home", "assistant", "request_detail"],
    "keywords": ["診所掛號", "看醫生", "看診", "clinic appointment", "健康諮詢", "掛號申請"]
  }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_agent_clinic_redirect.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Run the full backend suite to check for regressions**

Run: `python -m pytest backend/tests -q`
Expected: All tests pass except the pre-existing, unrelated `test_recommend_falls_back_to_keyword_matching_without_gemini_key` failure noted in Task 5 (caused by a `GEMINI_API_KEY` already set in the local environment — not something this plan introduces or should fix).

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/catalog.py backend/app/agent/page_catalog.py backend/app/agent/agent.py lambda_tools/page_knowledge/pages.json backend/tests/test_agent_clinic_redirect.py
git commit -m "feat: register clinic_appointment service and redirect chat requests to its flow page"
```

---

### Task 9: Frontend weather types + API client

**Files:**
- Create: `frontend/src/types/weather.ts`
- Create: `frontend/src/api/weather.ts`

**Interfaces:**
- Produces: `WeatherInfo` type, `getWeather(city?: string): Promise<WeatherInfo>`

- [ ] **Step 1: Create the type file**

```typescript
// frontend/src/types/weather.ts
export interface WeatherInfo {
  city: string;
  temperature: number;
  high: number;
  low: number;
  condition: string;
  is_large_temp_swing: boolean;
  fallback_used: boolean;
}
```

- [ ] **Step 2: Create the API client**

```typescript
// frontend/src/api/weather.ts
import type { WeatherInfo } from "../types/weather";
import { api } from "./client";

export function getWeather(city?: string): Promise<WeatherInfo> {
  const query = city ? `?city=${encodeURIComponent(city)}` : "";
  return api<WeatherInfo>(`/api/weather${query}`);
}
```

- [ ] **Step 3: Verify the project still type-checks**

Run (from `frontend/`): `npx tsc -b --noEmit`
Expected: no new errors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/types/weather.ts frontend/src/api/weather.ts
git commit -m "feat: add weather types and API client"
```

---

### Task 10: `useSpeechSynthesis` hook

**Files:**
- Create: `frontend/src/hooks/useSpeechSynthesis.ts`
- Test: `frontend/src/hooks/useSpeechSynthesis.test.ts`

**Interfaces:**
- Produces: `useSpeechSynthesis() -> { speaking: boolean; supported: boolean; speak: (text: string) => void; stop: () => void }`

- [ ] **Step 1: Write the failing test**

```typescript
// frontend/src/hooks/useSpeechSynthesis.test.ts
import { renderHook, act } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useSpeechSynthesis } from "./useSpeechSynthesis";

const originalSpeechSynthesis = window.speechSynthesis;
const originalUtterance = window.SpeechSynthesisUtterance;

describe("useSpeechSynthesis", () => {
  let speakMock: ReturnType<typeof vi.fn>;
  let cancelMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    speakMock = vi.fn();
    cancelMock = vi.fn();
    Object.defineProperty(window, "speechSynthesis", {
      value: { speak: speakMock, cancel: cancelMock, speaking: false },
      writable: true,
      configurable: true,
    });
    Object.defineProperty(window, "SpeechSynthesisUtterance", {
      value: vi.fn().mockImplementation((text: string) => ({ text, lang: "", onend: null, onerror: null })),
      writable: true,
      configurable: true,
    });
  });

  afterEach(() => {
    Object.defineProperty(window, "speechSynthesis", { value: originalSpeechSynthesis, configurable: true });
    Object.defineProperty(window, "SpeechSynthesisUtterance", { value: originalUtterance, configurable: true });
  });

  it("reports supported=true when window.speechSynthesis exists", () => {
    const { result } = renderHook(() => useSpeechSynthesis());
    expect(result.current.supported).toBe(true);
  });

  it("calls speechSynthesis.speak with a zh-TW utterance when speak() is called", () => {
    const { result } = renderHook(() => useSpeechSynthesis());
    act(() => result.current.speak("阿伯早安"));
    expect(speakMock).toHaveBeenCalledTimes(1);
    const utterance = speakMock.mock.calls[0][0];
    expect(utterance.text).toBe("阿伯早安");
    expect(utterance.lang).toBe("zh-TW");
  });

  it("calls speechSynthesis.cancel when stop() is called", () => {
    const { result } = renderHook(() => useSpeechSynthesis());
    act(() => result.current.stop());
    expect(cancelMock).toHaveBeenCalledTimes(1);
  });

  it("reports supported=false when window.speechSynthesis is undefined", () => {
    Object.defineProperty(window, "speechSynthesis", { value: undefined, configurable: true });
    const { result } = renderHook(() => useSpeechSynthesis());
    expect(result.current.supported).toBe(false);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run (from `frontend/`): `npm test -- useSpeechSynthesis.test.ts`
Expected: FAIL — module not found

- [ ] **Step 3: Implement the hook**

```typescript
// frontend/src/hooks/useSpeechSynthesis.ts
import { useCallback, useEffect, useRef, useState } from "react";

/** 瀏覽器內建語音朗讀（zh-TW），按了才念，不自動播放。不支援時 supported=false。 */
export function useSpeechSynthesis() {
  const [speaking, setSpeaking] = useState(false);
  const [supported, setSupported] = useState(true);

  useEffect(() => {
    setSupported(typeof window !== "undefined" && !!window.speechSynthesis);
  }, []);

  const speak = useCallback((text: string) => {
    if (!window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = "zh-TW";
    utterance.onend = () => setSpeaking(false);
    utterance.onerror = () => setSpeaking(false);
    setSpeaking(true);
    window.speechSynthesis.speak(utterance);
  }, []);

  const stop = useCallback(() => {
    window.speechSynthesis?.cancel();
    setSpeaking(false);
  }, []);

  return { speaking, supported, speak, stop };
}
```

- [ ] **Step 4: Run test to verify it passes**

Run (from `frontend/`): `npm test -- useSpeechSynthesis.test.ts`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/hooks/useSpeechSynthesis.ts frontend/src/hooks/useSpeechSynthesis.test.ts
git commit -m "feat: add tap-to-listen speech synthesis hook"
```

---

### Task 11: `WeatherGreetingCard` + mount on `HomePage`

**Files:**
- Create: `frontend/src/components/WeatherGreetingCard.tsx`
- Test: `frontend/src/components/WeatherGreetingCard.test.tsx`
- Modify: `frontend/src/pages/HomePage.tsx` (mount the card; add import near the other component imports at the top, and render it as a new `<section>` right after the AI-butler entry section, before the "熱門服務" section)

**Interfaces:**
- Consumes: `getWeather(city?: string): Promise<WeatherInfo>` (Task 9), `useSpeechSynthesis()` (Task 10), `useAuth().name` (existing, already used in `HomePage.tsx`)
- Produces: `<WeatherGreetingCard userName={string} />`

- [ ] **Step 1: Write the failing test**

```typescript
// frontend/src/components/WeatherGreetingCard.test.tsx
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { WeatherGreetingCard } from "./WeatherGreetingCard";
import * as weatherApi from "../api/weather";

vi.mock("../api/weather");

const speakMock = vi.fn();
vi.mock("../hooks/useSpeechSynthesis", () => ({
  useSpeechSynthesis: () => ({ speaking: false, supported: true, speak: speakMock, stop: vi.fn() }),
}));

beforeEach(() => {
  speakMock.mockClear();
  vi.mocked(weatherApi.getWeather).mockResolvedValue({
    city: "台中市",
    temperature: 27,
    high: 30,
    low: 22,
    condition: "晴時多雲",
    is_large_temp_swing: true,
    fallback_used: false,
  });
});

describe("WeatherGreetingCard", () => {
  it("shows the city, temperature, and condition once loaded", async () => {
    render(<WeatherGreetingCard userName="添財" />);
    expect(await screen.findByText(/台中市/)).toBeInTheDocument();
    expect(screen.getByText(/晴時多雲/)).toBeInTheDocument();
  });

  it("speaks a greeting including the user's name when the button is tapped", async () => {
    const user = userEvent.setup();
    render(<WeatherGreetingCard userName="添財" />);
    const button = await screen.findByRole("button", { name: /播放語音/ });
    await user.click(button);
    await waitFor(() => expect(speakMock).toHaveBeenCalledTimes(1));
    expect(speakMock.mock.calls[0][0]).toContain("添財");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run (from `frontend/`): `npm test -- WeatherGreetingCard.test.tsx`
Expected: FAIL — module not found

- [ ] **Step 3: Implement the component**

```tsx
// frontend/src/components/WeatherGreetingCard.tsx
import { useEffect, useState } from "react";
import { getWeather } from "../api/weather";
import { useSpeechSynthesis } from "../hooks/useSpeechSynthesis";
import type { WeatherInfo } from "../types/weather";
import { ServiceIcon } from "./ServiceIcon";

interface Props {
  userName: string;
}

export function WeatherGreetingCard({ userName }: Props) {
  const [weather, setWeather] = useState<WeatherInfo | null>(null);
  const { speaking, supported, speak, stop } = useSpeechSynthesis();

  useEffect(() => {
    getWeather()
      .then(setWeather)
      .catch(() => setWeather(null));
  }, []);

  if (!weather) return null;

  const greeting = `${userName}早安，今天${weather.city}${weather.condition}，氣溫約${Math.round(
    weather.temperature,
  )}度。${weather.is_large_temp_swing ? "早晚溫差大，要記得多穿一件外套喔！" : "祝你今天有個好心情！"}`;

  return (
    <section className="mt-6 rounded-[22px] bg-[var(--color-surface)] p-4 shadow-sm">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <span className="flex h-11 w-11 items-center justify-center rounded-full bg-[var(--color-info-soft)] text-[var(--color-info)]">
            <ServiceIcon type="sun" size={22} />
          </span>
          <div>
            <p className="text-sm font-extrabold text-[var(--color-foreground)]">
              {weather.city} · {weather.condition}
            </p>
            <p className="text-sm text-[var(--color-muted-foreground)]">
              {Math.round(weather.temperature)}°（{Math.round(weather.low)}°–{Math.round(weather.high)}°）
            </p>
          </div>
        </div>
        {supported && (
          <button
            type="button"
            onClick={() => (speaking ? stop() : speak(greeting))}
            className="flex min-h-[44px] items-center gap-1.5 rounded-full bg-brand px-4 text-sm font-bold text-[var(--color-on-primary)]"
          >
            <ServiceIcon type="chat" size={16} />
            {speaking ? "停止" : "播放語音"}
          </button>
        )}
      </div>
    </section>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run (from `frontend/`): `npm test -- WeatherGreetingCard.test.tsx`
Expected: PASS (2 passed)

- [ ] **Step 5: Mount on `HomePage`**

In `frontend/src/pages/HomePage.tsx`, add the import after the other component imports (near `import { SupportPanel } from "../components/SupportPanel";`):
```typescript
import { WeatherGreetingCard } from "../components/WeatherGreetingCard";
```
Add this section right after the "AI 管家入口" `<section className="mt-8">...</section>` block and before the "熱門服務" `<section className="mt-6">...</section>` block:
```tsx
        <WeatherGreetingCard userName={name} />
```

- [ ] **Step 6: Run the frontend test suite to check for regressions**

Run (from `frontend/`): `npm test`
Expected: all tests pass

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/WeatherGreetingCard.tsx frontend/src/components/WeatherGreetingCard.test.tsx frontend/src/pages/HomePage.tsx
git commit -m "feat: add weather greeting card with tap-to-listen readout to home page"
```

---

### Task 12: Frontend clinic types + API client

**Files:**
- Create: `frontend/src/types/clinic.ts`
- Create: `frontend/src/api/clinics.ts`

**Interfaces:**
- Produces: `ClinicInfo`, `SymptomTriageResult`, `ClinicAppointmentPayload`, `ClinicAppointmentResult`, `CrossSellResult` types; `listClinics`, `triageSymptom`, `submitClinicAppointment`, `getClinicAppointment`, `getCrossSellRecommendations` functions

- [ ] **Step 1: Create the type file**

```typescript
// frontend/src/types/clinic.ts
export interface ClinicInfo {
  id: string;
  name: string;
  specialties: string[];
  address: string;
  phone: string;
  is_open_now: boolean;
}

export interface SymptomTriageResult {
  specialty: string;
  advisory: string;
  clinics: ClinicInfo[];
  recommended_clinic_id: string | null;
  recommend_reason: string | null;
}

export interface ClinicAppointmentPayload {
  clinic_id: string;
  appointment_date: string; // YYYY-MM-DD
  appointment_time: string; // HH:MM
  symptom_note: string;
  contact_name: string;
  phone: string;
}

export interface ClinicAppointmentResult {
  success: boolean;
  request_id: string;
  status: string;
}

export interface ClinicAppointmentOrder {
  request_id: string;
  status: string;
  order_items: {
    clinic_id: string;
    clinic_name: string;
    clinic_address: string;
    clinic_phone: string;
    appointment_date: string;
    appointment_time: string;
  };
}

export interface HealthProductRecommendationItem {
  product_id: string;
  reason: string;
}

export interface CrossSellResult {
  recommendations: HealthProductRecommendationItem[];
  fallback_used: boolean;
}
```

- [ ] **Step 2: Create the API client**

```typescript
// frontend/src/api/clinics.ts
import type {
  ClinicAppointmentOrder,
  ClinicAppointmentPayload,
  ClinicAppointmentResult,
  ClinicInfo,
  CrossSellResult,
  SymptomTriageResult,
} from "../types/clinic";
import { api } from "./client";

export function listClinics(city: string, district: string, specialty?: string) {
  const params = new URLSearchParams({ city, district });
  if (specialty) params.set("specialty", specialty);
  return api<{ clinics: ClinicInfo[] }>(`/api/clinics?${params.toString()}`).then((r) => r.clinics);
}

export function triageSymptom(symptomText: string, city: string, district: string) {
  return api<SymptomTriageResult>("/api/symptom-triage", {
    method: "POST",
    body: JSON.stringify({ symptom_text: symptomText, city, district }),
  });
}

export function submitClinicAppointment(payload: ClinicAppointmentPayload) {
  return api<ClinicAppointmentResult>("/api/clinic-appointments", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getClinicAppointment(requestId: string) {
  return api<ClinicAppointmentOrder>(`/api/clinic-appointments/${encodeURIComponent(requestId)}`);
}

export function getCrossSellRecommendations(requestId: string) {
  return api<CrossSellResult>(`/api/clinic-appointments/${encodeURIComponent(requestId)}/cross-sell`, {
    method: "POST",
  });
}
```

- [ ] **Step 3: Verify the project still type-checks**

Run (from `frontend/`): `npx tsc -b --noEmit`
Expected: no new errors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/types/clinic.ts frontend/src/api/clinics.ts
git commit -m "feat: add clinic types and API client"
```

---

### Task 13: `ClinicCard` + `ClinicCardList`

**Files:**
- Create: `frontend/src/components/ClinicCard.tsx`
- Create: `frontend/src/components/ClinicCardList.tsx`
- Test: `frontend/src/components/ClinicCardList.test.tsx`

**Interfaces:**
- Consumes: `ClinicInfo` (Task 12)
- Produces: `<ClinicCardList clinics={ClinicInfo[]} selectedId={string|null} recommendedId={string|null} recommendReason={string|null} onSelect={(id: string) => void} />`

- [ ] **Step 1: Write the failing test**

```typescript
// frontend/src/components/ClinicCardList.test.tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ClinicCardList } from "./ClinicCardList";
import type { ClinicInfo } from "../types/clinic";

const clinics: ClinicInfo[] = [
  { id: "c1", name: "王耳鼻喉科診所", specialties: ["耳鼻喉科"], address: "台中市西屯區文心路100號", phone: "04-1111111", is_open_now: true },
  { id: "c2", name: "西屯家醫科診所", specialties: ["家醫科"], address: "台中市西屯區台灣大道99號", phone: "04-2222222", is_open_now: false },
];

describe("ClinicCardList", () => {
  it("renders every clinic's name and open/closed status", () => {
    render(
      <ClinicCardList clinics={clinics} selectedId={null} recommendedId={null} recommendReason={null} onSelect={vi.fn()} />,
    );
    expect(screen.getByText("王耳鼻喉科診所")).toBeInTheDocument();
    expect(screen.getByText(/現在有看診/)).toBeInTheDocument();
    expect(screen.getByText(/目前休診/)).toBeInTheDocument();
  });

  it("marks the AI-recommended clinic and shows its reason", () => {
    render(
      <ClinicCardList clinics={clinics} selectedId={null} recommendedId="c1" recommendReason="距離最近" onSelect={vi.fn()} />,
    );
    expect(screen.getByText("AI 推薦")).toBeInTheDocument();
    expect(screen.getByText("距離最近")).toBeInTheDocument();
  });

  it("calls onSelect with the clinic id when a card is clicked", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(
      <ClinicCardList clinics={clinics} selectedId={null} recommendedId={null} recommendReason={null} onSelect={onSelect} />,
    );
    await user.click(screen.getByText("西屯家醫科診所"));
    expect(onSelect).toHaveBeenCalledWith("c2");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run (from `frontend/`): `npm test -- ClinicCardList.test.tsx`
Expected: FAIL — module not found

- [ ] **Step 3: Implement the components**

```tsx
// frontend/src/components/ClinicCard.tsx
import type { ClinicInfo } from "../types/clinic";
import { ServiceIcon } from "./ServiceIcon";

interface Props {
  clinic: ClinicInfo;
  selected: boolean;
  recommended: boolean;
  recommendReason: string | null;
  onSelect: () => void;
}

export function ClinicCard({ clinic, selected, recommended, recommendReason, onSelect }: Props) {
  return (
    <button
      type="button"
      aria-pressed={selected}
      onClick={onSelect}
      className={`min-h-[44px] w-64 flex-none snap-start rounded-2xl border-2 p-4 text-left transition ${
        selected
          ? "border-[var(--color-primary)] bg-[var(--color-primary-soft)]"
          : "border-[var(--color-border)] bg-[var(--color-surface)]"
      }`}
    >
      {recommended && (
        <span className="mb-2 inline-block rounded-full bg-[var(--color-primary)] px-2.5 py-0.5 text-xs font-bold text-[var(--color-on-primary)]">
          AI 推薦
        </span>
      )}
      <p className="text-base font-black leading-normal text-[var(--color-foreground)]">{clinic.name}</p>
      <p className="mt-1 text-sm font-bold text-[var(--color-muted-foreground)]">
        {clinic.specialties.join("、")} · {clinic.is_open_now ? "現在有看診" : "目前休診"}
      </p>
      <div className="mt-2 flex items-start gap-1.5 text-sm leading-relaxed text-[var(--color-muted-foreground)]">
        <ServiceIcon type="location" size={16} className="mt-0.5 flex-none" />
        <span>{clinic.address}</span>
      </div>
      <div className="mt-1 flex items-center gap-1.5 text-sm leading-relaxed text-[var(--color-muted-foreground)]">
        <ServiceIcon type="phone" size={16} className="flex-none" />
        <span className="font-[family-name:var(--font-mono)]">{clinic.phone}</span>
      </div>
      {recommended && recommendReason && (
        <p className="mt-2 text-sm leading-relaxed text-[var(--color-primary)]">{recommendReason}</p>
      )}
    </button>
  );
}
```

```tsx
// frontend/src/components/ClinicCardList.tsx
import type { ClinicInfo } from "../types/clinic";
import { ClinicCard } from "./ClinicCard";

interface Props {
  clinics: ClinicInfo[];
  selectedId: string | null;
  recommendedId: string | null;
  recommendReason: string | null;
  onSelect: (id: string) => void;
}

export function ClinicCardList({ clinics, selectedId, recommendedId, recommendReason, onSelect }: Props) {
  return (
    <div className="flex snap-x gap-3 overflow-x-auto pb-2">
      {clinics.map((clinic) => (
        <ClinicCard
          key={clinic.id}
          clinic={clinic}
          selected={selectedId === clinic.id}
          recommended={recommendedId === clinic.id}
          recommendReason={recommendedId === clinic.id ? recommendReason : null}
          onSelect={() => onSelect(clinic.id)}
        />
      ))}
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run (from `frontend/`): `npm test -- ClinicCardList.test.tsx`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ClinicCard.tsx frontend/src/components/ClinicCardList.tsx frontend/src/components/ClinicCardList.test.tsx
git commit -m "feat: add clinic card list with AI-recommendation highlight"
```

---

### Task 14: `ClinicSummaryCard`

**Files:**
- Create: `frontend/src/components/ClinicSummaryCard.tsx`
- Test: `frontend/src/components/ClinicSummaryCard.test.tsx`

**Interfaces:**
- Produces: `<ClinicSummaryCard data={{clinicName, clinicAddress, date, time, symptomNote, contactName, phone}} onConfirm={() => void} onEdit={() => void} submitting={boolean} />`

- [ ] **Step 1: Write the failing test**

```typescript
// frontend/src/components/ClinicSummaryCard.test.tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ClinicSummaryCard } from "./ClinicSummaryCard";

const data = {
  clinicName: "王耳鼻喉科診所",
  clinicAddress: "台中市西屯區文心路100號",
  date: "2026-08-02",
  time: "15:00",
  symptomNote: "咳嗽、喉嚨癢",
  contactName: "王添財",
  phone: "0912345678",
};

describe("ClinicSummaryCard", () => {
  it("renders every field from the summary data", () => {
    render(<ClinicSummaryCard data={data} onConfirm={vi.fn()} onEdit={vi.fn()} submitting={false} />);
    expect(screen.getByText("王耳鼻喉科診所")).toBeInTheDocument();
    expect(screen.getByText("咳嗽、喉嚨癢")).toBeInTheDocument();
    expect(screen.getByText("王添財")).toBeInTheDocument();
  });

  it("calls onConfirm when the confirm button is clicked", async () => {
    const user = userEvent.setup();
    const onConfirm = vi.fn();
    render(<ClinicSummaryCard data={data} onConfirm={onConfirm} onEdit={vi.fn()} submitting={false} />);
    await user.click(screen.getByRole("button", { name: "確認掛號" }));
    expect(onConfirm).toHaveBeenCalledTimes(1);
  });

  it("disables both buttons while submitting", () => {
    render(<ClinicSummaryCard data={data} onConfirm={vi.fn()} onEdit={vi.fn()} submitting={true} />);
    expect(screen.getByRole("button", { name: /掛號處理中/ })).toBeDisabled();
    expect(screen.getByRole("button", { name: "返回修改" })).toBeDisabled();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run (from `frontend/`): `npm test -- ClinicSummaryCard.test.tsx`
Expected: FAIL — module not found

- [ ] **Step 3: Implement the component**

```tsx
// frontend/src/components/ClinicSummaryCard.tsx
import { GlassPanel } from "./GlassPanel";

interface SummaryData {
  clinicName: string;
  clinicAddress: string;
  date: string;
  time: string;
  symptomNote: string;
  contactName: string;
  phone: string;
}

interface Props {
  data: SummaryData;
  onConfirm: () => void;
  onEdit: () => void;
  submitting: boolean;
}

const ROWS: { key: keyof SummaryData; label: string }[] = [
  { key: "clinicName", label: "診所名稱" },
  { key: "clinicAddress", label: "診所地址" },
  { key: "date", label: "看診日期" },
  { key: "time", label: "看診時間" },
  { key: "symptomNote", label: "症狀描述" },
  { key: "contactName", label: "聯絡人" },
  { key: "phone", label: "聯絡電話" },
];

const MONO_KEYS = new Set<keyof SummaryData>(["date", "time", "phone"]);

export function ClinicSummaryCard({ data, onConfirm, onEdit, submitting }: Props) {
  return (
    <GlassPanel className="rounded-3xl p-5">
      {ROWS.map((row) => (
        <div
          key={row.key}
          className="flex justify-between gap-3 border-b border-[var(--color-border)] py-3.5 text-base leading-relaxed last:border-b-0"
        >
          <span className="font-bold text-[var(--color-muted-foreground)]">{row.label}</span>
          <span
            className={`text-right font-bold text-[var(--color-foreground)] ${
              MONO_KEYS.has(row.key) ? "font-[family-name:var(--font-mono)]" : ""
            }`}
          >
            {data[row.key]}
          </span>
        </div>
      ))}

      <div className="mt-5 flex flex-col gap-3">
        <button
          type="button"
          onClick={onConfirm}
          disabled={submitting}
          className="min-h-[44px] rounded-2xl bg-[var(--color-primary)] px-6 py-4 text-base font-bold text-[var(--color-on-primary)] disabled:opacity-60"
        >
          {submitting ? "掛號處理中，請稍候" : "確認掛號"}
        </button>
        <button
          type="button"
          onClick={onEdit}
          disabled={submitting}
          className="min-h-[44px] rounded-2xl border-2 border-[var(--color-primary)] px-6 py-4 text-base font-bold text-[var(--color-primary)] disabled:opacity-60"
        >
          返回修改
        </button>
      </div>
    </GlassPanel>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run (from `frontend/`): `npm test -- ClinicSummaryCard.test.tsx`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ClinicSummaryCard.tsx frontend/src/components/ClinicSummaryCard.test.tsx
git commit -m "feat: add clinic appointment summary card"
```

---

### Task 15: `ClinicConsultFlowPage` + routing

**Files:**
- Create: `frontend/src/pages/ClinicConsultFlowPage.tsx`
- Test: `frontend/src/pages/ClinicConsultFlowPage.test.tsx`
- Modify: `frontend/src/App.tsx:19` (import), `frontend/src/App.tsx:60-62` (add route, right after the `health_product_recommendation` route)
- Modify: `frontend/src/data/services.ts:381` (append a new service entry right after `health_product_recommendation`, before `restaurant_reservation`)

**Interfaces:**
- Consumes: `useSpeechRecognition` (existing), `VoiceButton` (existing), `counties`/`getDistrictsByCountyName` (existing, `frontend/src/data/twRegions.ts`), `ReservationDatePicker` (existing, reused as-is since its label "用餐日期" is reservation-specific — see Step 3 note below), `ClinicCardList` (Task 13), `ClinicSummaryCard` (Task 14), `ShareWithFamilyButton` (existing), `listClinics`/`triageSymptom`/`submitClinicAppointment`/`getCrossSellRecommendations` (Task 12)
- Produces: page mounted at `/services/clinic_appointment`

- [ ] **Step 1: Write the failing test**

```typescript
// frontend/src/pages/ClinicConsultFlowPage.test.tsx
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { ClinicConsultFlowPage } from "./ClinicConsultFlowPage";
import * as clinicsApi from "../api/clinics";

vi.mock("../api/clinics");

const clinics = [
  {
    id: "c1",
    name: "王耳鼻喉科診所",
    specialties: ["耳鼻喉科"],
    address: "台中市西屯區文心路100號",
    phone: "04-1111111",
    is_open_now: true,
  },
];

function renderPage() {
  return render(
    <MemoryRouter>
      <ClinicConsultFlowPage />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.mocked(clinicsApi.triageSymptom).mockResolvedValue({
    specialty: "耳鼻喉科",
    advisory: "聽起來像是感冒了，要多喝溫水喔！",
    clinics,
    recommended_clinic_id: "c1",
    recommend_reason: "距離近且目前有看診",
  });
  vi.mocked(clinicsApi.submitClinicAppointment).mockResolvedValue({
    success: true,
    request_id: "REQ-1",
    status: "CONFIRMED",
  });
  vi.mocked(clinicsApi.getCrossSellRecommendations).mockResolvedValue({
    recommendations: [{ product_id: "P039", reason: "適合喉嚨不適" }],
    fallback_used: false,
  });
});

describe("ClinicConsultFlowPage", () => {
  it("walks through symptom entry to clinic recommendation", async () => {
    const user = userEvent.setup();
    renderPage();

    const input = screen.getByLabelText("症狀描述");
    await user.type(input, "我一直咳嗽，喉嚨很癢");
    await user.click(screen.getByRole("button", { name: "送出" }));

    expect(await screen.findByText(/聽起來像是感冒了/)).toBeInTheDocument();
    expect(screen.getByText("王耳鼻喉科診所")).toBeInTheDocument();
    expect(screen.getByText("AI 推薦")).toBeInTheDocument();
  });

  it("submits the appointment and shows the cross-sell + family-share step", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByLabelText("症狀描述"), "我一直咳嗽，喉嚨很癢");
    await user.click(screen.getByRole("button", { name: "送出" }));
    await screen.findByText("王耳鼻喉科診所");

    await user.click(screen.getByText("王耳鼻喉科診所"));
    await user.click(screen.getByRole("button", { name: "下一步" }));

    const dateInput = screen.getByLabelText("看診日期");
    await user.type(dateInput, "2026-08-02");
    await user.type(screen.getByLabelText("看診時間"), "15:00");
    await user.click(screen.getByRole("button", { name: "下一步" }));

    await user.type(screen.getByLabelText("聯絡人姓名"), "王添財");
    await user.type(screen.getByLabelText("聯絡電話"), "0912345678");
    await user.click(screen.getByRole("button", { name: "下一步" }));

    await user.click(screen.getByRole("button", { name: "確認掛號" }));

    await waitFor(() => expect(clinicsApi.submitClinicAppointment).toHaveBeenCalledTimes(1));
    expect(await screen.findByText(/適合喉嚨不適/)).toBeInTheDocument();
    expect(screen.getByText(/爸爸今天有點咳嗽/)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run (from `frontend/`): `npm test -- ClinicConsultFlowPage.test.tsx`
Expected: FAIL — module not found

- [ ] **Step 3: Implement the page**

Note: this page uses its own plain `<input type="date">` / `<input type="time">` (not `ReservationDatePicker`/`TimeSlotSelector`, whose labels and slot-only design are restaurant-specific) so the "看診日期"/"看診時間" labels used by the test above are accurate for this domain.

```tsx
// frontend/src/pages/ClinicConsultFlowPage.tsx
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ButlerLauncher } from "../components/ButlerLauncher";
import { ClinicCardList } from "../components/ClinicCardList";
import { ClinicSummaryCard } from "../components/ClinicSummaryCard";
import { ServiceIcon } from "../components/ServiceIcon";
import { ShareWithFamilyButton } from "../components/ShareWithFamilyButton";
import { Toast } from "../components/Toast";
import { VoiceButton } from "../components/VoiceButton";
import {
  getCrossSellRecommendations,
  submitClinicAppointment,
  triageSymptom,
} from "../api/clinics";
import { counties, getDistrictsByCountyName } from "../data/twRegions";
import { useSpeechRecognition } from "../hooks/useSpeechRecognition";
import type { ClinicInfo, HealthProductRecommendationItem } from "../types/clinic";

type Step = "symptom" | "clinic" | "datetime" | "contact" | "summary" | "crosssell" | "share";
const STEP_ORDER: Step[] = ["symptom", "clinic", "datetime", "contact", "summary", "crosssell", "share"];

const DEFAULT_CITY = "台中市";
const DEFAULT_DISTRICT = "西屯區";

export function ClinicConsultFlowPage() {
  const navigate = useNavigate();
  const [stepIndex, setStepIndex] = useState(0);
  const [toastText, setToastText] = useState<string | null>(null);

  const [symptomNote, setSymptomNote] = useState("");
  const [city, setCity] = useState(DEFAULT_CITY);
  const [district, setDistrict] = useState(DEFAULT_DISTRICT);
  const [advisory, setAdvisory] = useState("");
  const [clinics, setClinics] = useState<ClinicInfo[]>([]);
  const [recommendedClinicId, setRecommendedClinicId] = useState<string | null>(null);
  const [recommendReason, setRecommendReason] = useState<string | null>(null);
  const [selectedClinicId, setSelectedClinicId] = useState<string | null>(null);
  const [triaging, setTriaging] = useState(false);

  const [date, setDate] = useState("");
  const [time, setTime] = useState("");
  const [contactName, setContactName] = useState("");
  const [phone, setPhone] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [requestId, setRequestId] = useState<string | null>(null);

  const [crossSellItems, setCrossSellItems] = useState<HealthProductRecommendationItem[]>([]);

  const step = STEP_ORDER[stepIndex];
  const goNext = () => setStepIndex((i) => Math.min(i + 1, STEP_ORDER.length - 1));
  const goBack = () => setStepIndex((i) => Math.max(i - 1, 0));
  const selectedClinic = clinics.find((c) => c.id === selectedClinicId) ?? null;
  const districtOptions = getDistrictsByCountyName(city);

  const speech = useSpeechRecognition((text) => setSymptomNote(text));

  async function submitSymptom() {
    if (!symptomNote.trim() || triaging) return;
    setTriaging(true);
    try {
      const result = await triageSymptom(symptomNote, city, district);
      setAdvisory(result.advisory);
      setClinics(result.clinics);
      setRecommendedClinicId(result.recommended_clinic_id);
      setRecommendReason(result.recommend_reason);
      setSelectedClinicId(result.recommended_clinic_id ?? result.clinics[0]?.id ?? null);
      goNext();
    } catch (error) {
      setToastText(error instanceof Error ? error.message : "查詢失敗，請稍後再試");
    } finally {
      setTriaging(false);
    }
  }

  async function handleConfirmAppointment() {
    if (!selectedClinicId) return;
    setSubmitting(true);
    try {
      const result = await submitClinicAppointment({
        clinic_id: selectedClinicId,
        appointment_date: date,
        appointment_time: time,
        symptom_note: symptomNote,
        contact_name: contactName,
        phone,
      });
      setRequestId(result.request_id);
      const crossSell = await getCrossSellRecommendations(result.request_id);
      setCrossSellItems(crossSell.recommendations);
      goNext();
    } catch (error) {
      setToastText(error instanceof Error ? error.message : "掛號未成功送出，請重新嘗試");
    } finally {
      setSubmitting(false);
    }
  }

  const familyShareText = selectedClinic
    ? `${contactName ? "家人" : "爸爸"}今天有點不舒服（${symptomNote}），已預約${date} ${time}去${selectedClinic.name}看診，請不用擔心。`
    : "";

  return (
    <>
      <main className="mx-auto min-h-dvh max-w-md bg-canvas px-5 pb-32 pt-8">
        <header className="flex items-center gap-3 pb-4">
          <button
            type="button"
            onClick={() => navigate("/home")}
            aria-label="返回"
            className="flex h-11 w-11 items-center justify-center text-[var(--color-muted-foreground)]"
          >
            <ServiceIcon type="back" size={22} />
          </button>
          <h1 className="text-xl font-black text-[var(--color-foreground)]">診所掛號</h1>
        </header>

        {step === "symptom" && (
          <section className="flex flex-col gap-4">
            <p className="text-base font-bold leading-relaxed text-[var(--color-foreground)]">
              請描述您哪裡不舒服
            </p>
            <div className="grid grid-cols-2 gap-3">
              <select
                aria-label="縣市"
                value={city}
                onChange={(e) => {
                  setCity(e.target.value);
                  setDistrict("");
                }}
                className="min-h-[44px] rounded-2xl border-2 border-[var(--color-border)] bg-[var(--color-surface)] px-3.5"
              >
                {counties.map((c) => (
                  <option key={c.code} value={c.name}>
                    {c.name}
                  </option>
                ))}
              </select>
              <select
                aria-label="鄉鎮市區"
                value={district}
                onChange={(e) => setDistrict(e.target.value)}
                className="min-h-[44px] rounded-2xl border-2 border-[var(--color-border)] bg-[var(--color-surface)] px-3.5"
              >
                <option value="">請選擇</option>
                {districtOptions.map((name) => (
                  <option key={name} value={name}>
                    {name}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex items-center gap-3">
              <VoiceButton
                listening={speech.listening}
                supported={speech.supported}
                onStart={speech.start}
                onStop={speech.stop}
              />
              <textarea
                aria-label="症狀描述"
                value={symptomNote}
                onChange={(e) => setSymptomNote(e.target.value)}
                placeholder="例如：我今天開始咳嗽，喉嚨癢癢乾乾的"
                rows={4}
                className="min-w-0 flex-1 rounded-2xl border-2 border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-3.5 outline-none focus:border-brand"
              />
            </div>
            <button
              type="button"
              disabled={!symptomNote.trim() || triaging}
              onClick={() => void submitSymptom()}
              className="min-h-[44px] rounded-2xl bg-brand px-6 py-4 text-base font-bold text-[var(--color-on-primary)] disabled:opacity-40"
            >
              送出
            </button>
          </section>
        )}

        {step === "clinic" && (
          <section className="flex flex-col gap-4">
            <p className="text-base font-bold leading-relaxed text-[var(--color-foreground)]">{advisory}</p>
            <ClinicCardList
              clinics={clinics}
              selectedId={selectedClinicId}
              recommendedId={recommendedClinicId}
              recommendReason={recommendReason}
              onSelect={setSelectedClinicId}
            />
            <button
              type="button"
              disabled={!selectedClinicId}
              onClick={goNext}
              className="mt-2 min-h-[44px] rounded-2xl bg-brand px-6 py-4 text-base font-bold text-[var(--color-on-primary)] disabled:opacity-40"
            >
              下一步
            </button>
          </section>
        )}

        {step === "datetime" && (
          <section className="flex flex-col gap-4">
            <div>
              <label htmlFor="clinic-date" className="block text-base font-bold text-[var(--color-foreground)]">
                看診日期
              </label>
              <input
                id="clinic-date"
                aria-label="看診日期"
                type="date"
                value={date}
                onChange={(e) => setDate(e.target.value)}
                className="mt-2 min-h-[44px] w-full rounded-xl border-2 border-[var(--color-border)] bg-[var(--color-surface)] px-3.5 py-2.5 font-[family-name:var(--font-mono)]"
              />
            </div>
            <div>
              <label htmlFor="clinic-time" className="block text-base font-bold text-[var(--color-foreground)]">
                看診時間
              </label>
              <input
                id="clinic-time"
                aria-label="看診時間"
                type="time"
                value={time}
                onChange={(e) => setTime(e.target.value)}
                className="mt-2 min-h-[44px] w-full rounded-xl border-2 border-[var(--color-border)] bg-[var(--color-surface)] px-3.5 py-2.5 font-[family-name:var(--font-mono)]"
              />
            </div>
            <div className="flex gap-3">
              <button type="button" onClick={goBack} className="min-h-[44px] flex-1 rounded-2xl border-2 border-brand px-6 py-4 text-base font-bold text-brand">
                上一步
              </button>
              <button
                type="button"
                disabled={!date || !time}
                onClick={goNext}
                className="min-h-[44px] flex-1 rounded-2xl bg-brand px-6 py-4 text-base font-bold text-[var(--color-on-primary)] disabled:opacity-40"
              >
                下一步
              </button>
            </div>
          </section>
        )}

        {step === "contact" && (
          <section className="flex flex-col gap-4">
            <div>
              <label htmlFor="clinic-contact-name" className="block text-base font-bold text-[var(--color-foreground)]">
                聯絡人姓名
              </label>
              <input
                id="clinic-contact-name"
                aria-label="聯絡人姓名"
                type="text"
                value={contactName}
                onChange={(e) => setContactName(e.target.value)}
                className="mt-2 min-h-[44px] w-full rounded-xl border-2 border-[var(--color-border)] bg-[var(--color-surface)] px-3.5 py-2.5"
              />
            </div>
            <div>
              <label htmlFor="clinic-contact-phone" className="block text-base font-bold text-[var(--color-foreground)]">
                聯絡電話
              </label>
              <input
                id="clinic-contact-phone"
                aria-label="聯絡電話"
                type="tel"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                className="mt-2 min-h-[44px] w-full rounded-xl border-2 border-[var(--color-border)] bg-[var(--color-surface)] px-3.5 py-2.5 font-[family-name:var(--font-mono)]"
              />
            </div>
            <div className="flex gap-3">
              <button type="button" onClick={goBack} className="min-h-[44px] flex-1 rounded-2xl border-2 border-brand px-6 py-4 text-base font-bold text-brand">
                上一步
              </button>
              <button
                type="button"
                disabled={!contactName.trim() || !phone.trim()}
                onClick={goNext}
                className="min-h-[44px] flex-1 rounded-2xl bg-brand px-6 py-4 text-base font-bold text-[var(--color-on-primary)] disabled:opacity-40"
              >
                下一步
              </button>
            </div>
          </section>
        )}

        {step === "summary" && selectedClinic && (
          <ClinicSummaryCard
            data={{
              clinicName: selectedClinic.name,
              clinicAddress: selectedClinic.address,
              date,
              time,
              symptomNote,
              contactName,
              phone,
            }}
            onConfirm={() => void handleConfirmAppointment()}
            onEdit={goBack}
            submitting={submitting}
          />
        )}

        {step === "crosssell" && (
          <section className="flex flex-col gap-4">
            <p className="text-base font-bold leading-relaxed text-[var(--color-foreground)]">
              掛號已完成！針對您的狀況，為您推薦以下商品：
            </p>
            {crossSellItems.map((item) => (
              <div
                key={item.product_id}
                className="rounded-2xl border-2 border-[var(--color-border)] bg-[var(--color-surface)] p-4"
              >
                <p className="text-sm leading-relaxed text-[var(--color-foreground)]">{item.reason}</p>
              </div>
            ))}
            <button
              type="button"
              onClick={goNext}
              className="min-h-[44px] rounded-2xl bg-brand px-6 py-4 text-base font-bold text-[var(--color-on-primary)]"
            >
              下一步
            </button>
          </section>
        )}

        {step === "share" && requestId && (
          <section className="flex flex-col gap-4">
            <p className="text-base font-bold leading-relaxed text-[var(--color-foreground)]">{familyShareText}</p>
            <ShareWithFamilyButton text={familyShareText} />
            <button
              type="button"
              onClick={() => navigate(`/requests/${requestId}`)}
              className="min-h-[44px] rounded-2xl border-2 border-brand px-6 py-4 text-base font-bold text-brand"
            >
              查看掛號紀錄
            </button>
          </section>
        )}
      </main>

      <Toast text={toastText} onHide={() => setToastText(null)} />
      <ButlerLauncher currentPageId="clinic_appointment_flow" />
    </>
  );
}
```

- [ ] **Step 4: Register the route and service entry**

In `frontend/src/App.tsx`, add the import after `import { HealthRecommendationPage } from "./pages/HealthRecommendationPage";`:
```typescript
import { ClinicConsultFlowPage } from "./pages/ClinicConsultFlowPage";
```
Add the route right after the `health_product_recommendation` route:
```tsx
        <Route
          path="/services/clinic_appointment"
          element={<Protected><ClinicConsultFlowPage /></Protected>}
        />
```

In `frontend/src/data/services.ts`, add this entry to the `SERVICES` array right after the `health_product_recommendation` entry (before `restaurant_reservation`):
```typescript
  {
    service_id: "clinic_appointment",
    title: "診所掛號",
    subtitle: "描述症狀，AI 幫您找附近診所並掛號",
    description: "說出哪裡不舒服，AI 會建議科別、推薦附近真實診所，並協助掛號、加購對症商品。",
    icon: "health",
    fields: [],
  },
```

- [ ] **Step 5: Run test to verify it passes**

Run (from `frontend/`): `npm test -- ClinicConsultFlowPage.test.tsx`
Expected: PASS (2 passed)

- [ ] **Step 6: Run the full frontend suite to check for regressions**

Run (from `frontend/`): `npm test`
Expected: all tests pass

- [ ] **Step 7: Commit**

```bash
git add frontend/src/pages/ClinicConsultFlowPage.tsx frontend/src/pages/ClinicConsultFlowPage.test.tsx frontend/src/App.tsx frontend/src/data/services.ts
git commit -m "feat: add clinic consult flow page (symptom to appointment to cross-sell to family share)"
```

---

## Self-Review

**Spec coverage:**
- 診所真實資料（NHI 開放資料）→ Task 3 ✓
- 症狀→科別 Bedrock 判斷 → Task 4 (`triage_symptom`) ✓
- 診所推薦 Bedrock 判斷（基於真實候選資料）→ Task 4 (`recommend_clinic`) ✓
- 加購商品 Bedrock 判斷 → Task 4 (`recommend_health_products_for_symptom`) + Task 5（新商品/關鍵字）✓
- 掛號本身（不進對話狀態機、獨立服務）→ Task 6, 7, 8 ✓
- 前端流程頁（symptom → clinic → datetime → contact → summary → crosssell → share）→ Task 15 ✓
- 家人分享沿用既有 `ShareWithFamilyButton`，不新增機制 → Task 15 (imports the existing component, no new share logic) ✓
- 天氣卡片（Open-Meteo + fallback + cache）→ Task 1, 2 ✓
- 語音朗讀（tap-to-listen）→ Task 10, 11 ✓
- 不動 `health_recommendation.py`/`HealthRecommendationPage` 既有邏輯 → confirmed no task touches them beyond additive `HEALTH_KEYWORDS` entries in Task 5, which is backward-compatible (existing keys/behavior unchanged) ✓
- 不擴充 `agent.py` 狀態機、只加一個導頁分支 → Task 8 ✓

**Placeholder scan:** no TBD/TODO; every step has complete code.

**Type consistency:** `ClinicInfo.id` (not `clinic_id`) is used consistently from `clinic_catalog.py` → `llm.recommend_clinic` → `/api/clinics` → `ClinicInfo` (frontend) → `ClinicCardList`/`ClinicCard`. `HealthProductRecommendationItem` matches the shape returned by `recommend_health_products_for_symptom` and consumed in `ClinicConsultFlowPage`'s cross-sell step. `ClinicAppointmentPayload` field names (`clinic_id`, `appointment_date`, `appointment_time`, `symptom_note`, `contact_name`, `phone`) match `clinic_appointment.create_appointment`'s `_REQUIRED_FIELDS` exactly.
