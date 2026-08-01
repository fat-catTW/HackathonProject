"""Google API wrappers for external product/restaurant search.

Both functions return None (not an exception) when the API key is missing
or the call fails, so callers can fall back to internal catalog matching
without special-casing errors — mirrors health_recommendation.py's existing
Gemini-unavailable-returns-None convention.
"""
from __future__ import annotations

import httpx

from ..config import get_settings

_TIMEOUT_SECONDS = 8


def google_text_search(query: str, *, num: int = 10) -> list[dict] | None:
    settings = get_settings()
    if not settings.google_search_api_key or not settings.google_search_engine_id:
        return None
    try:
        response = httpx.get(
            "https://www.googleapis.com/customsearch/v1",
            params={
                "key": settings.google_search_api_key,
                "cx": settings.google_search_engine_id,
                "q": query,
                "num": num,
            },
            timeout=_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        items = response.json().get("items", [])
    except Exception:
        return None
    return [
        {"title": item.get("title", ""), "snippet": item.get("snippet", ""), "link": item.get("link", "")}
        for item in items
    ]


def google_places_search(query: str, *, num: int = 10) -> list[dict] | None:
    settings = get_settings()
    if not settings.google_maps_api_key:
        return None
    try:
        response = httpx.get(
            "https://maps.googleapis.com/maps/api/place/textsearch/json",
            params={"key": settings.google_maps_api_key, "query": query},
            timeout=_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("status") not in ("OK", "ZERO_RESULTS"):
            return None
        results = payload.get("results", [])
    except Exception:
        return None
    return [
        {
            "place_id": r.get("place_id", ""),
            "name": r.get("name", ""),
            "address": r.get("formatted_address", ""),
            "rating": r.get("rating"),
        }
        for r in results[:num]
    ]
