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
