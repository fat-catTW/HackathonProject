"""Short-lived server-side cache for external (Google) search results.

Booking/checkout flows must not trust restaurant/product details a client
sends back verbatim (name, address, price) since search results are not
under our control. Storing the last search response per actor lets those
flows re-derive trusted details from the id the client selects, instead of
trusting whatever the client echoes back.
"""
from __future__ import annotations

import time

_TTL_SECONDS = 30 * 60
_cache: dict[tuple[str, str], tuple[float, dict[str, dict]]] = {}


def store_results(actor_id: str, namespace: str, results: list[dict], *, id_key: str) -> None:
    _cache[(actor_id, namespace)] = (time.time(), {r[id_key]: r for r in results})


def get_result(actor_id: str, namespace: str, result_id: str) -> dict | None:
    entry = _cache.get((actor_id, namespace))
    if not entry:
        return None
    stored_at, by_id = entry
    if time.time() - stored_at > _TTL_SECONDS:
        del _cache[(actor_id, namespace)]
        return None
    return by_id.get(result_id)
