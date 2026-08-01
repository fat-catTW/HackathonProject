"""Restaurant search: merges the internal restaurant directory with Google
Places results near the user's address, ranked by Bedrock, capped at 5.
Picks are cached per actor so reservation.create_reservation_order can
verify a Google-sourced pick without trusting client-supplied details."""
from __future__ import annotations

from ..agent import llm
from . import external_search, external_search_cache, restaurant_catalog

MAX_RESULTS = 5
CACHE_NAMESPACE = "restaurant_search"


def _internal_candidates() -> list[dict]:
    return [
        {
            "id": r["id"],
            "name": r["name"],
            "address": r["address"],
            "phone": r["phone"],
            "source": "internal",
        }
        for r in restaurant_catalog.RESTAURANTS
    ]


def search_restaurants(actor_id: str, address: str, preference: str = "") -> dict:
    candidates = _internal_candidates()
    query_text = f"{address} {preference}".strip() or address

    if llm.is_available():
        search_query = llm.plan_external_query(query_text, purpose="附近餐廳搜尋")
        if search_query:
            places = external_search.google_places_search(search_query)
            if places:
                candidates.extend(
                    {
                        "id": p["place_id"],
                        "name": p["name"],
                        "address": p["address"],
                        "phone": "",
                        "source": "google_places",
                    }
                    for p in places
                    if p.get("place_id")
                )

    picks = None
    if llm.is_available():
        picks = llm.rank_external_results(query_text, candidates, id_key="id", max_results=MAX_RESULTS)
    if not picks:
        picks = candidates[:MAX_RESULTS]
        for pick in picks:
            pick.setdefault("reason", "")

    external_search_cache.store_results(actor_id, CACHE_NAMESPACE, picks, id_key="id")
    return {"restaurants": picks}
