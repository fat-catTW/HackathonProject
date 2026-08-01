# Bedrock + Google External Search Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace keyword/Gemini-based recommendation in health products, quick-purchase bundles, and restaurant reservation with a Bedrock-planned Google API search that's merged with the existing internal catalog, plus fix the pre-existing broken `shop_price_compare` reply.

**Architecture:** A new `external_search.py` wraps Google Custom Search / Places APIs (returns `None` on any failure or missing key). A new pair of `llm.py` functions do Bedrock two-step orchestration: turn free text into a search query, then rank a candidate list (internal + external) picking only real candidate ids — mirrors the existing anti-hallucination pattern in `health_recommendation.py`'s current Gemini call. A new `external_search_cache.py` holds each actor's most recent search results in memory (TTL 30 min) so booking/checkout flows never trust client-echoed restaurant/product details for externally-sourced picks.

**Tech Stack:** Python 3.12, FastAPI, boto3 (Bedrock `converse`), httpx (Google HTTP calls), pytest + `unittest.mock.patch`.

## Global Constraints

- Every external-search code path must degrade to the existing internal-only behavior (no exception, no broken reply) when Bedrock is unavailable, a Google key is unset, or the Google call fails — spec's "三層 fallback".
- Bedrock ranking must only return ids that exist in the candidate list passed to it — never invent an item.
- Google-sourced picks always land in a `PENDING_PROVIDER` case (no stock/points mutation, no third-party booking API call) — spec's "待確認案件".
- Booking/purchase endpoints must resolve externally-sourced item details from the server-side cache by id, never from client-supplied fields.
- Design doc: `docs/superpowers/specs/2026-08-01-bedrock-google-external-search-design.md`.

---

### Task 1: Google API wrappers + result cache + config

**Files:**
- Create: `backend/app/services/external_search.py`
- Create: `backend/app/services/external_search_cache.py`
- Test: `backend/tests/test_external_search.py`
- Test: `backend/tests/test_external_search_cache.py`
- Modify: `backend/app/config.py`
- Modify: `backend/.env.example`
- Modify: `.env.example`

**Interfaces:**
- Produces: `external_search.google_text_search(query: str, *, num: int = 10) -> list[dict] | None` — each item `{"title": str, "snippet": str, "link": str}`.
- Produces: `external_search.google_places_search(query: str, *, num: int = 10) -> list[dict] | None` — each item `{"place_id": str, "name": str, "address": str, "rating": float | None}`.
- Produces: `external_search_cache.store_results(actor_id: str, namespace: str, results: list[dict], *, id_key: str) -> None`.
- Produces: `external_search_cache.get_result(actor_id: str, namespace: str, result_id: str) -> dict | None`.
- Produces: `Settings.google_search_api_key`, `Settings.google_search_engine_id`, `Settings.google_maps_api_key` (all `str`, default `""`).

- [ ] **Step 1: Add config fields**

In `backend/app/config.py`, inside the `Settings` dataclass, right after the `bedrock_model_id` field, add:

```python
    google_search_api_key: str = os.getenv("GOOGLE_SEARCH_API_KEY", "")
    google_search_engine_id: str = os.getenv("GOOGLE_SEARCH_ENGINE_ID", "")
    google_maps_api_key: str = os.getenv("GOOGLE_MAPS_API_KEY", "")
```

- [ ] **Step 2: Document the new env vars**

In `backend/.env.example`, after the `GEMINI_API_KEY=` line, add:

```
GOOGLE_SEARCH_API_KEY=
GOOGLE_SEARCH_ENGINE_ID=
GOOGLE_MAPS_API_KEY=
```

In the root `.env.example`, after the `BEDROCK_MODEL_ID=...` line, add the same three lines.

- [ ] **Step 3: Write the failing cache tests**

Create `backend/tests/test_external_search_cache.py`:

```python
import time
from unittest.mock import patch

from backend.app.services import external_search_cache


def test_store_and_get_result_round_trips():
    external_search_cache.store_results(
        "user-1", "ns", [{"id": "a", "name": "A"}, {"id": "b", "name": "B"}], id_key="id"
    )
    assert external_search_cache.get_result("user-1", "ns", "a") == {"id": "a", "name": "A"}


def test_get_result_returns_none_for_unknown_id():
    external_search_cache.store_results("user-1", "ns", [{"id": "a"}], id_key="id")
    assert external_search_cache.get_result("user-1", "ns", "missing") is None


def test_get_result_returns_none_when_never_searched():
    assert external_search_cache.get_result("user-2", "ns", "a") is None


def test_get_result_expires_after_ttl():
    external_search_cache.store_results("user-3", "ns", [{"id": "a"}], id_key="id")
    with patch("backend.app.services.external_search_cache.time.time", return_value=time.time() + 3600):
        assert external_search_cache.get_result("user-3", "ns", "a") is None
```

- [ ] **Step 4: Run cache tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_external_search_cache.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'backend.app.services.external_search_cache'`

- [ ] **Step 5: Implement the cache**

Create `backend/app/services/external_search_cache.py`:

```python
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
```

- [ ] **Step 6: Run cache tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_external_search_cache.py -v`
Expected: 4 passed

- [ ] **Step 7: Write the failing external_search tests**

Create `backend/tests/test_external_search.py`:

```python
from unittest.mock import patch

from backend.app.services import external_search


def test_google_text_search_returns_none_without_api_key(monkeypatch):
    monkeypatch.setattr(external_search, "get_settings", lambda: type(
        "S", (), {"google_search_api_key": "", "google_search_engine_id": ""}
    )())
    assert external_search.google_text_search("foo") is None


def test_google_text_search_returns_parsed_items(monkeypatch):
    monkeypatch.setattr(external_search, "get_settings", lambda: type(
        "S", (), {"google_search_api_key": "k", "google_search_engine_id": "cx"}
    )())

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"items": [{"title": "T", "snippet": "S", "link": "L"}]}

    with patch("backend.app.services.external_search.httpx.get", return_value=FakeResponse()):
        result = external_search.google_text_search("foo")
    assert result == [{"title": "T", "snippet": "S", "link": "L"}]


def test_google_text_search_returns_none_on_http_error(monkeypatch):
    monkeypatch.setattr(external_search, "get_settings", lambda: type(
        "S", (), {"google_search_api_key": "k", "google_search_engine_id": "cx"}
    )())
    with patch("backend.app.services.external_search.httpx.get", side_effect=Exception("boom")):
        assert external_search.google_text_search("foo") is None


def test_google_places_search_returns_none_without_api_key(monkeypatch):
    monkeypatch.setattr(external_search, "get_settings", lambda: type(
        "S", (), {"google_maps_api_key": ""}
    )())
    assert external_search.google_places_search("foo") is None


def test_google_places_search_returns_parsed_results(monkeypatch):
    monkeypatch.setattr(external_search, "get_settings", lambda: type(
        "S", (), {"google_maps_api_key": "k"}
    )())

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "status": "OK",
                "results": [
                    {"place_id": "p1", "name": "N", "formatted_address": "A", "rating": 4.2}
                ],
            }

    with patch("backend.app.services.external_search.httpx.get", return_value=FakeResponse()):
        result = external_search.google_places_search("foo")
    assert result == [{"place_id": "p1", "name": "N", "address": "A", "rating": 4.2}]
```

- [ ] **Step 8: Run external_search tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_external_search.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'backend.app.services.external_search'`

- [ ] **Step 9: Implement the Google API wrappers**

Create `backend/app/services/external_search.py`:

```python
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
```

- [ ] **Step 10: Run external_search tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_external_search.py -v`
Expected: 5 passed

- [ ] **Step 11: Commit**

```bash
git add backend/app/services/external_search.py backend/app/services/external_search_cache.py backend/tests/test_external_search.py backend/tests/test_external_search_cache.py backend/app/config.py backend/.env.example .env.example
git commit -m "feat: add Google API wrappers and external search result cache"
```

---

### Task 2: Bedrock query-planning and result-ranking helpers

**Files:**
- Modify: `backend/app/agent/llm.py`
- Test: `backend/tests/test_llm_external_search.py`

**Interfaces:**
- Consumes: `_converse_json(system: str, prompt: str, *, max_tokens: int = 512) -> dict | None` (existing, in this file).
- Produces: `llm.plan_external_query(user_text: str, *, purpose: str) -> str | None`.
- Produces: `llm.rank_external_results(user_text: str, candidates: list[dict], *, id_key: str, max_results: int) -> list[dict] | None` — each returned item is the original candidate dict plus a `"reason": str` key.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_llm_external_search.py`:

```python
from unittest.mock import patch

from backend.app.agent import llm


def test_plan_external_query_returns_query_string():
    with patch("backend.app.agent.llm._converse_json", return_value={"query": "台中 餐廳"}):
        assert llm.plan_external_query("我想在台中吃飯", purpose="restaurant") == "台中 餐廳"


def test_plan_external_query_returns_none_when_bedrock_unavailable():
    with patch("backend.app.agent.llm._converse_json", return_value=None):
        assert llm.plan_external_query("foo", purpose="x") is None


def test_rank_external_results_filters_to_valid_ids_and_caps_length():
    candidates = [{"pid": "a", "name": "A"}, {"pid": "b", "name": "B"}, {"pid": "c", "name": "C"}]
    fake_payload = {
        "picks": [
            {"id": "b", "reason": "matches"},
            {"id": "does-not-exist", "reason": "ignored"},
            {"id": "a", "reason": "also matches"},
            {"id": "c", "reason": "third"},
        ]
    }
    with patch("backend.app.agent.llm._converse_json", return_value=fake_payload):
        result = llm.rank_external_results("query", candidates, id_key="pid", max_results=2)
    assert [r["pid"] for r in result] == ["b", "a"]
    assert result[0]["reason"] == "matches"
    assert result[0]["name"] == "B"


def test_rank_external_results_returns_none_when_bedrock_unavailable():
    with patch("backend.app.agent.llm._converse_json", return_value=None):
        assert llm.rank_external_results("q", [{"pid": "a"}], id_key="pid", max_results=3) is None


def test_rank_external_results_returns_none_when_no_valid_picks():
    candidates = [{"pid": "a"}]
    with patch("backend.app.agent.llm._converse_json", return_value={"picks": [{"id": "z"}]}):
        assert llm.rank_external_results("q", candidates, id_key="pid", max_results=3) is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_llm_external_search.py -v`
Expected: FAIL with `AttributeError: module 'backend.app.agent.llm' has no attribute 'plan_external_query'`

- [ ] **Step 3: Implement the helpers**

In `backend/app/agent/llm.py`, add these two system prompt constants near the other `_..._SYSTEM` constants (after `_PAGE_HELP_SYSTEM`):

```python
_EXTERNAL_QUERY_SYSTEM = (
    "You turn a Taiwanese user's request into a short, effective search-engine query in Traditional "
    "Chinese, for finding real-world products or restaurants on the web. "
    "Keep it to a few keywords, no explanations. "
    "Return JSON only in the format {\"query\": string}."
)

_EXTERNAL_RANK_SYSTEM = (
    "You pick and rank the best matches for a user's request from a provided candidate list. "
    "You may ONLY choose ids that appear in the candidate list — never invent an id or describe an "
    "item that is not in the list. "
    "Pick at most the requested max_results items, best match first, and give each a short "
    "one-sentence reason in Traditional Chinese. "
    "Return JSON only in the format {\"picks\": [{\"id\": string, \"reason\": string}]}."
)
```

Then add these two functions at the end of the file:

```python
def plan_external_query(user_text: str, *, purpose: str) -> str | None:
    payload = _converse_json(
        _EXTERNAL_QUERY_SYSTEM,
        f"Purpose: {purpose}\nUser request:\n{user_text}",
        max_tokens=128,
    )
    if not payload:
        return None
    query = payload.get("query")
    return query.strip() if isinstance(query, str) and query.strip() else None


def rank_external_results(
    user_text: str, candidates: list[dict], *, id_key: str, max_results: int
) -> list[dict] | None:
    prompt = (
        f"User request:\n{user_text}\n\n"
        f"max_results: {max_results}\n\n"
        f"Candidates (id field is \"{id_key}\"):\n"
        + json.dumps(candidates, ensure_ascii=False, indent=2)
    )
    payload = _converse_json(_EXTERNAL_RANK_SYSTEM, prompt, max_tokens=768)
    if not payload or not isinstance(payload.get("picks"), list):
        return None

    by_id = {c[id_key]: c for c in candidates}
    picks: list[dict] = []
    for pick in payload["picks"]:
        if not isinstance(pick, dict):
            continue
        pick_id = pick.get("id")
        if pick_id not in by_id:
            continue
        reason = pick.get("reason")
        picks.append({
            **by_id[pick_id],
            "reason": reason.strip() if isinstance(reason, str) and reason.strip() else "",
        })
        if len(picks) >= max_results:
            break
    return picks or None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_llm_external_search.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/agent/llm.py backend/tests/test_llm_external_search.py
git commit -m "feat: add Bedrock query-planning and result-ranking helpers"
```

---

### Task 3: Fix the missing `_answer_price_compare` (shop_price_compare bug)

**Files:**
- Modify: `backend/app/agent/agent.py`
- Test: `backend/tests/test_shop_price_compare.py` (existing, currently 3 FAILED)

**Interfaces:**
- Consumes: `tools.call("compare_product_prices", {"query": str}, auth_token=...) -> dict` (existing embedded tool, returns `{"success", "group_id", "product_name", "offers": [{"store_name", "unit_price"}]}` on success, `{"success": False, "error": {"code", "message"}}` on failure).
- Produces: `_answer_price_compare(query: str, auth_token: str | None) -> tuple[str, str | None]` — `(reply_text, redirect_path_or_None)`. Called at `agent.py:1099`, which already exists and expects exactly this signature.

- [ ] **Step 1: Confirm the current failure**

Run: `cd backend && python -m pytest tests/test_shop_price_compare.py tests/test_agent_quick_purchase_submit.py tests/test_customer_support_requests.py -v`
Expected: 6 FAIL, all with `NameError: name '_answer_price_compare' is not defined` (verified against this worktree's actual baseline, which has more callers hitting this code path than the design assumed): `test_agent_detects_price_compare_and_replies_with_redirect`, `test_agent_detects_natural_compare_phrasing_with_product_name_in_the_middle`, `test_agent_price_compare_not_found_has_no_redirect` (in `test_shop_price_compare.py`), `test_quick_purchase_chat_flow_creates_order_end_to_end` (in `test_agent_quick_purchase_submit.py`), and `test_keyword_detection_survives_services_without_keywords` (in `test_customer_support_requests.py`).

- [ ] **Step 2: Implement the missing function**

In `backend/app/agent/agent.py`, add this function directly above `_handle_one_shot_service` (the function that calls it at line 1099):

```python
def _answer_price_compare(query: str, auth_token: str | None) -> tuple[str, str | None]:
    result = tools.call("compare_product_prices", {"query": query}, auth_token=auth_token)
    if not result.get("success"):
        message = result.get("error", {}).get("message", "查詢失敗")
        return f"抱歉，這次比價沒有成功，原因是：{message}。你可以換個商品名稱再試一次。", None

    offers = result.get("offers") or []
    lines = [f"「{result.get('product_name', '')}」目前各店家的點數兌換價格："]
    for index, offer in enumerate(offers, start=1):
        lines.append(f"{index}. {offer.get('store_name', '')}：{offer.get('unit_price', '')} 元")
    if offers:
        lines.append(f"目前最便宜的是 {offers[0].get('store_name', '')}。")
    lines.append("我幫你導到商城購物頁面，可以直接看到完整比價和下單。")
    reply = "\n".join(lines)
    redirect_path = f"/services/shop_purchase?compare={result['group_id']}"
    return reply, redirect_path
```

- [ ] **Step 3: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_shop_price_compare.py tests/test_agent_quick_purchase_submit.py tests/test_customer_support_requests.py -v`
Expected: all passed (10 in `test_shop_price_compare.py` plus the 2 other previously-failing tests)

- [ ] **Step 4: Commit**

```bash
git add backend/app/agent/agent.py
git commit -m "fix: implement missing _answer_price_compare for shop_price_compare"
```

---

### Task 4: Health product recommendation — Bedrock + Google instead of Gemini

**Files:**
- Modify: `backend/app/services/health_recommendation.py`
- Modify: `backend/tests/test_health_recommendation.py`
- Modify: `backend/.env.example`, `.env.example` (remove `GEMINI_API_KEY`)
- Modify: `backend/app/config.py` (remove `gemini_api_key` field)

**Interfaces:**
- Consumes: `external_search.google_text_search(query, *, num=10) -> list[dict] | None` (Task 1), `llm.is_available() -> bool`, `llm.plan_external_query(user_text, *, purpose) -> str | None`, `llm.rank_external_results(user_text, candidates, *, id_key, max_results) -> list[dict] | None` (Task 2).
- Produces: `recommend(query: str, products: list[dict]) -> dict` — **unchanged external signature**, still returns `{"query", "recommendations", "fallback_used"}`. `tools.py`'s `_embedded_recommend_products_by_health_need` calls this and needs no changes.

- [ ] **Step 1: Update the existing Gemini test to test the Bedrock/Google fallback instead**

In `backend/tests/test_health_recommendation.py`, replace `test_recommend_falls_back_to_keyword_matching_without_gemini_key` with:

```python
def test_recommend_falls_back_to_keyword_matching_without_bedrock_or_google():
    """Neither Bedrock nor a Google key is configured in the test env, so
    recommend() must use the rule-based fallback and mark fallback_used=True."""
    result = health_recommendation.recommend("我想減脂", health_catalog.list_products())
    assert result["fallback_used"] is True
    assert len(result["recommendations"]) > 0
```

Then add these new tests to the same file:

```python
def test_recommend_uses_bedrock_and_google_when_available():
    products = health_catalog.list_products()[:2]
    fake_external = [{"title": "外部商品A", "snippet": "低卡高蛋白", "link": "https://example.com/a"}]
    fake_picks = [
        {"product_id": products[0]["id"], "name": products[0]["name"], "source": "internal",
         "detail": "x", "reason": "符合減脂需求"},
    ]
    with patch("backend.app.services.health_recommendation.llm.is_available", return_value=True), \
         patch("backend.app.services.health_recommendation.llm.plan_external_query", return_value="低卡商品"), \
         patch("backend.app.services.health_recommendation.external_search.google_text_search", return_value=fake_external), \
         patch("backend.app.services.health_recommendation.llm.rank_external_results", return_value=fake_picks):
        result = health_recommendation.recommend("我想減脂", products)

    assert result["fallback_used"] is False
    assert result["recommendations"][0]["product_id"] == products[0]["id"]
    assert result["recommendations"][0]["reason"] == "符合減脂需求"
    assert result["recommendations"][0]["source"] == "internal"


def test_recommend_falls_back_when_bedrock_ranking_returns_nothing():
    products = health_catalog.list_products()[:2]
    with patch("backend.app.services.health_recommendation.llm.is_available", return_value=True), \
         patch("backend.app.services.health_recommendation.llm.plan_external_query", return_value="q"), \
         patch("backend.app.services.health_recommendation.external_search.google_text_search", return_value=None), \
         patch("backend.app.services.health_recommendation.llm.rank_external_results", return_value=None):
        result = health_recommendation.recommend("我想減脂", products)
    assert result["fallback_used"] is True
```

Add `from unittest.mock import patch` to the top of the test file if not already imported (it already is, per the existing `from unittest.mock import patch` on line 3).

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_health_recommendation.py -v`
Expected: the two new tests FAIL (AttributeError, module has no attribute `llm`/`external_search`), the renamed test still passes (it only calls the existing `recommend`, which currently ignores Bedrock).

- [ ] **Step 3: Rewrite health_recommendation.py**

Replace the full contents of `backend/app/services/health_recommendation.py` with:

```python
"""Health-need -> product recommendation engine.

Uses the shared Bedrock two-step orchestration (app/agent/llm.py's
plan_external_query / rank_external_results) to search Google for products
beyond the static internal catalog, then falls back to rule-based
keyword/tag matching when Bedrock is unavailable, no Google key is
configured, or the Google call fails for any reason.
"""
from __future__ import annotations

from ..agent import llm
from . import external_search

HEALTH_KEYWORDS: dict[str, list[str]] = {
    "減脂": ["減脂", "低碳", "低卡", "高蛋白"],
    "增肌": ["增肌", "高蛋白", "均衡"],
    "三高": ["低鈉", "低脂", "低糖"],
    "低鈉": ["低鈉"],
    "素食": ["素食"],
    "低糖": ["低糖"],
    "高纖": ["高纖"],
}

UNHEALTHY_TAGS = ["高糖", "高鈉", "高脂", "高熱量"]

MAX_RECOMMENDATIONS = 5


def fallback_recommend(query: str, products: list[dict]) -> list[dict]:
    """Rule-based keyword/tag matching, used when Bedrock/Google are unavailable."""
    matched = [
        product
        for product in products
        if any(tag in query for tag in product["tags"])
        or any(
            keyword in query and any(tag in product["tags"] for tag in related_tags)
            for keyword, related_tags in HEALTH_KEYWORDS.items()
        )
    ]
    pool = matched if matched else [
        product for product in products if not any(tag in UNHEALTHY_TAGS for tag in product["tags"])
    ]
    return [
        {
            "product_id": product["id"],
            "name": product["name"],
            "reason": f"關鍵字比對：商品標籤包含 {'、'.join(product['tags'])}",
            "match_tags": product["tags"],
            "source": "internal",
        }
        for product in pool[:MAX_RECOMMENDATIONS]
    ]


def _internal_candidates(products: list[dict]) -> list[dict]:
    return [
        {
            "product_id": p["id"],
            "name": p["name"],
            "source": "internal",
            "detail": f"{p['category']}|熱量{p['calories']}kcal|標籤:{','.join(p['tags'])}",
        }
        for p in products
    ]


def _analyze_with_bedrock_and_google(query: str, products: list[dict]) -> list[dict] | None:
    if not llm.is_available():
        return None

    candidates = _internal_candidates(products)
    search_query = llm.plan_external_query(query, purpose="health/diet product search")
    if search_query:
        external_results = external_search.google_text_search(search_query)
        if external_results:
            for index, item in enumerate(external_results):
                candidates.append({
                    "product_id": f"external:{index}",
                    "name": item["title"],
                    "source": "google_search",
                    "detail": item["snippet"],
                    "link": item["link"],
                })

    picks = llm.rank_external_results(
        query, candidates, id_key="product_id", max_results=MAX_RECOMMENDATIONS
    )
    if not picks:
        return None

    by_internal_id = {p["id"]: p for p in products}
    recommendations = []
    for pick in picks:
        product = by_internal_id.get(pick["product_id"])
        recommendations.append({
            "product_id": pick["product_id"],
            "name": pick["name"],
            "reason": pick["reason"],
            "match_tags": product["tags"] if product else [],
            "source": pick["source"],
            "link": pick.get("link"),
        })
    return recommendations


def recommend(query: str, products: list[dict]) -> dict:
    """Returns {"query", "recommendations", "fallback_used"}."""
    recommendations = _analyze_with_bedrock_and_google(query, products)
    if recommendations is not None:
        return {"query": query, "recommendations": recommendations, "fallback_used": False}
    return {
        "query": query,
        "recommendations": fallback_recommend(query, products),
        "fallback_used": True,
    }
```

- [ ] **Step 4: Remove the now-unused `gemini_api_key` setting**

In `backend/app/config.py`, delete the line `gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")`.

In `backend/.env.example` and `.env.example`, delete the `GEMINI_API_KEY=` line.

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_health_recommendation.py -v`
Expected: all passed (renamed test + 2 new tests + all pre-existing tests in the file)

Also run the full suite once to catch any other Gemini reference:
Run: `cd backend && python -m pytest -q`
Expected: no failures related to `gemini_api_key` or `google.genai` imports.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/health_recommendation.py backend/tests/test_health_recommendation.py backend/app/config.py backend/.env.example .env.example
git commit -m "feat: health recommendation uses Bedrock+Google search instead of Gemini"
```

---

### Task 5: Quick purchase (供品/水果) — Google search fallback with pending-case creation

**Files:**
- Modify: `backend/app/services/quick_purchase.py`
- Test: `backend/tests/test_quick_purchase_service.py`

**Interfaces:**
- Consumes: `quick_purchase_catalog.match_bundle(query) -> dict | None` (existing, unchanged), `shop.create_shop_order` (existing, unchanged), `llm.is_available()`, `llm.plan_external_query`, `llm.rank_external_results` (Task 2), `external_search.google_text_search` (Task 1), `STORE.next_request_id()`, `STORE.save_request(actor_id, order)`, `now_iso()` (existing, from `.store`).
- Produces: `create_quick_purchase_order(actor_id, query, *, contact_name, phone, address) -> dict` — **unchanged external signature**. On success with an externally-sourced match, returns `{"success": True, "request_id", "status": "PENDING_PROVIDER", "bundle_name", "source": "google_search"}`.

- [ ] **Step 1: Extend the existing `isolated_store` fixture to also patch `quick_purchase.STORE`**

The current fixture in `backend/tests/test_quick_purchase_service.py` only patches `store_module.STORE` and `shop.STORE`, because today `quick_purchase.py` has no direct `STORE` usage (it delegates entirely to `shop.create_shop_order`). Step 4 below adds direct `STORE` usage to `quick_purchase.py`, so the fixture must patch it too. Change:

```python
@pytest.fixture(autouse=True)
def isolated_store(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        test_store = store_module.MemoryStore(storage_path=Path(tmp) / "store.json")
        monkeypatch.setattr(store_module, "STORE", test_store)
        monkeypatch.setattr(shop, "STORE", test_store)
        test_store.restock_sku("sku_fruit_offering_set", 5)
        yield test_store
```

to:

```python
@pytest.fixture(autouse=True)
def isolated_store(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        test_store = store_module.MemoryStore(storage_path=Path(tmp) / "store.json")
        monkeypatch.setattr(store_module, "STORE", test_store)
        monkeypatch.setattr(shop, "STORE", test_store)
        monkeypatch.setattr(quick_purchase, "STORE", test_store)
        test_store.restock_sku("sku_fruit_offering_set", 5)
        yield test_store
```

- [ ] **Step 2: Write the failing tests**

Add to `backend/tests/test_quick_purchase_service.py`:

```python
from unittest.mock import patch


def test_quick_purchase_falls_back_to_bundle_not_found_without_bedrock():
    with patch("backend.app.services.quick_purchase.llm.is_available", return_value=False):
        result = quick_purchase.create_quick_purchase_order(
            "user-1", "完全不相關的字串xyz", contact_name="王大明", phone="0912345678", address="台北市"
        )
    assert result["success"] is False
    assert result["error"]["code"] == "BUNDLE_NOT_FOUND"


def test_quick_purchase_creates_pending_case_for_external_match(isolated_store):
    fake_external = [{"title": "現烤供品組合", "snippet": "在地烘焙供品組合", "link": "https://example.com/x"}]
    fake_pick = [{"result_id": "0", "name": "現烤供品組合", "detail": "在地烘焙供品組合",
                  "link": "https://example.com/x", "reason": "符合供品需求"}]
    with patch("backend.app.services.quick_purchase.llm.is_available", return_value=True), \
         patch("backend.app.services.quick_purchase.llm.plan_external_query", return_value="供品組合"), \
         patch("backend.app.services.quick_purchase.external_search.google_text_search", return_value=fake_external), \
         patch("backend.app.services.quick_purchase.llm.rank_external_results", return_value=fake_pick):
        result = quick_purchase.create_quick_purchase_order(
            "user-1", "完全不相關的字串xyz", contact_name="王大明", phone="0912345678", address="台北市"
        )

    assert result["success"] is True
    assert result["status"] == "PENDING_PROVIDER"
    assert result["source"] == "google_search"
    assert result["bundle_name"] == "現烤供品組合"

    order = isolated_store.get_request("user-1", result["request_id"])
    assert order["status"] == "PENDING_PROVIDER"
    assert order["form_data"]["external_link"] == "https://example.com/x"
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_quick_purchase_service.py -v`
Expected: FAIL — `create_quick_purchase_order` currently only returns `BUNDLE_NOT_FOUND` for unmatched queries, and the module has no `llm`/`external_search` attributes to patch.

- [ ] **Step 4: Implement the Google search fallback**

Replace the full contents of `backend/app/services/quick_purchase.py` with:

```python
"""One-shot 'quick purchase' order: match free text to a curated bundle and
submit directly. Falls back to a Bedrock-ranked Google search when no
internal bundle keyword matches, creating a PENDING_PROVIDER case for the
externally-sourced pick instead of a real stocked/pointed order."""
from __future__ import annotations

from ..agent import llm
from . import external_search, quick_purchase_catalog, shop
from .store import STORE, now_iso


def create_quick_purchase_order(
    actor_id: str, query: str, *, contact_name: str, phone: str, address: str
) -> dict:
    bundle = quick_purchase_catalog.match_bundle(query)
    if bundle:
        payload = {
            "cart": [{"sku_id": bundle["sku_id"], "quantity": 1}],
            "contact_name": contact_name,
            "phone": phone,
            "address": {"city": "", "street": address, "contact_name": contact_name},
        }
        result = shop.create_shop_order(actor_id, payload)
        if result.get("success"):
            result["bundle_name"] = bundle["name"]
        return result

    external = _find_external_bundle(query)
    if not external:
        return {
            "success": False,
            "error": {"code": "BUNDLE_NOT_FOUND", "message": f"找不到符合「{query}」的商品組合"},
        }
    return _create_external_quick_purchase_order(
        actor_id, external, contact_name=contact_name, phone=phone, address=address
    )


def _find_external_bundle(query: str) -> dict | None:
    if not llm.is_available():
        return None
    search_query = llm.plan_external_query(query, purpose="one-shot 供品/生活用品採購")
    if not search_query:
        return None
    results = external_search.google_text_search(search_query)
    if not results:
        return None
    candidates = [
        {"result_id": str(i), "name": r["title"], "detail": r["snippet"], "link": r["link"]}
        for i, r in enumerate(results)
    ]
    picks = llm.rank_external_results(query, candidates, id_key="result_id", max_results=1)
    return picks[0] if picks else None


def _create_external_quick_purchase_order(
    actor_id: str, external: dict, *, contact_name: str, phone: str, address: str
) -> dict:
    request_id = STORE.next_request_id()
    created_at = now_iso()
    order = {
        "request_id": request_id,
        "service_id": "shop_purchase",
        "service_name": "商城購物（網路搜尋商品）",
        "order_type": "10",
        "status": "PENDING_PROVIDER",
        "source": "google_search",
        "form_data": {
            "query_matched_name": external["name"],
            "external_detail": external.get("detail", ""),
            "external_link": external.get("link", ""),
            "contact_name": contact_name,
            "phone": phone,
            "address": address,
        },
        "status_history": [{"status": "PENDING_PROVIDER", "at": created_at}],
        "created_at": created_at,
    }
    try:
        STORE.save_request(actor_id, order)
    except Exception:
        return {
            "success": False,
            "error": {"code": "ORDER_SAVE_FAILED", "message": "訂單建立失敗，請稍後再試"},
        }
    return {
        "success": True,
        "request_id": request_id,
        "status": "PENDING_PROVIDER",
        "bundle_name": external["name"],
        "source": "google_search",
    }
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_quick_purchase_service.py -v`
Expected: all passed

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/quick_purchase.py backend/tests/test_quick_purchase_service.py
git commit -m "feat: quick purchase falls back to Bedrock+Google search with pending case creation"
```

---

### Task 6: Restaurant search — Google Places merged with internal directory, capped at 5

**Files:**
- Create: `backend/app/services/restaurant_search.py`
- Test: `backend/tests/test_restaurant_search.py`
- Modify: `backend/app/api/reservations.py`

**Interfaces:**
- Consumes: `restaurant_catalog.RESTAURANTS` (existing list constant), `llm.is_available/plan_external_query/rank_external_results` (Task 2), `external_search.google_places_search` (Task 1), `external_search_cache.store_results` (Task 1).
- Produces: `restaurant_search.search_restaurants(actor_id: str, address: str, preference: str = "") -> dict` — `{"restaurants": [{"id", "name", "address", "phone", "source", "reason"}, ...]}`, capped at 5.
- Produces: `POST /api/restaurants/search` with body `{"address": str, "preference"?: str}` → same shape as above.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_restaurant_search.py`:

```python
from unittest.mock import patch

from backend.app.services import external_search_cache, restaurant_search


def test_search_falls_back_to_internal_list_without_bedrock():
    with patch("backend.app.services.restaurant_search.llm.is_available", return_value=False):
        result = restaurant_search.search_restaurants("user-1", "台中市")
    assert len(result["restaurants"]) == 5
    assert all(r["source"] == "internal" for r in result["restaurants"])


def test_search_merges_and_caches_google_places_results():
    fake_places = [{"place_id": "p1", "name": "測試餐廳", "address": "台中市西區", "rating": 4.5}]
    fake_picks = [
        {"id": "p1", "name": "測試餐廳", "address": "台中市西區", "phone": "",
         "source": "google_places", "reason": "離你最近"}
    ]
    with patch("backend.app.services.restaurant_search.llm.is_available", return_value=True), \
         patch("backend.app.services.restaurant_search.llm.plan_external_query", return_value="台中市 餐廳"), \
         patch("backend.app.services.restaurant_search.external_search.google_places_search", return_value=fake_places), \
         patch("backend.app.services.restaurant_search.llm.rank_external_results", return_value=fake_picks):
        result = restaurant_search.search_restaurants("user-9", "台中市")

    assert result["restaurants"] == fake_picks
    cached = external_search_cache.get_result("user-9", "restaurant_search", "p1")
    assert cached == fake_picks[0]


def test_search_caps_at_five_results_when_ranking_unavailable():
    with patch("backend.app.services.restaurant_search.llm.is_available", return_value=True), \
         patch("backend.app.services.restaurant_search.llm.plan_external_query", return_value=None), \
         patch("backend.app.services.restaurant_search.llm.rank_external_results", return_value=None):
        result = restaurant_search.search_restaurants("user-2", "台北市")
    assert len(result["restaurants"]) == 5
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_restaurant_search.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'backend.app.services.restaurant_search'`

- [ ] **Step 3: Implement restaurant_search.py**

Create `backend/app/services/restaurant_search.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_restaurant_search.py -v`
Expected: 3 passed

- [ ] **Step 5: Add the search endpoint**

In `backend/app/api/reservations.py`, add `restaurant_search` to the existing import line and add the new route right after `list_restaurants`:

```python
from ..services import reservation, restaurant_catalog, restaurant_search
```

```python
@router.post("/api/restaurants/search")
def search_restaurants(payload: dict, user: CurrentUser = Depends(get_current_user)):
    address = str(payload.get("address") or "").strip()
    if not address:
        _raise_api_error(400, "INVALID_FORM_DATA", "請提供地址")
    preference = str(payload.get("preference") or "")
    return restaurant_search.search_restaurants(user.sub, address, preference)
```

- [ ] **Step 6: Write and run an API-level test**

`test_reservations_api.py` already defines a `client` fixture (`TestClient(app)`) and a plain helper function `auth_headers(client)` (not a pytest fixture — it's called directly inside each test, e.g. `headers = auth_headers(client)`). Add, following that exact pattern:

```python
def test_search_restaurants_requires_address(client):
    headers = auth_headers(client)
    response = client.post("/api/restaurants/search", json={}, headers=headers)
    assert response.status_code == 400
    assert response.json()["detail"]["error"]["code"] == "INVALID_FORM_DATA"


def test_search_restaurants_returns_capped_list(client):
    headers = auth_headers(client)
    response = client.post("/api/restaurants/search", json={"address": "台中市"}, headers=headers)
    assert response.status_code == 200
    assert len(response.json()["restaurants"]) <= 5
```

Run: `cd backend && python -m pytest tests/test_reservations_api.py -v`
Expected: all passed

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/restaurant_search.py backend/tests/test_restaurant_search.py backend/app/api/reservations.py backend/tests/test_reservations_api.py
git commit -m "feat: add Google Places restaurant search capped at 5, merged with internal directory"
```

---

### Task 7: Restaurant reservation accepts Google-sourced restaurants as pending cases

**Files:**
- Modify: `backend/app/services/reservation.py`
- Test: `backend/tests/test_reservation_service.py`

**Interfaces:**
- Consumes: `external_search_cache.get_result(actor_id, "restaurant_search", restaurant_id) -> dict | None` (Task 1), `restaurant_search.CACHE_NAMESPACE` (Task 6, value `"restaurant_search"`).
- Produces: `_resolve_restaurant(actor_id: str, restaurant_id: str) -> dict | None` — internal restaurants get `"source": "internal"` and keep `supports_booking_api` as-is; cached Google picks get `"source": "google_places"` and `"supports_booking_api": False` (so they fall through the existing unsupported-restaurant branch unchanged).

- [ ] **Step 1: Write the failing tests**

Add to `backend/tests/test_reservation_service.py` (reuses the file's existing `isolated_store` autouse fixture and `valid_payload` helper):

```python
from backend.app.services import external_search_cache


def test_create_reservation_order_for_cached_google_restaurant_is_pending():
    external_search_cache.store_results(
        "user-1",
        "restaurant_search",
        [{"id": "g-place-1", "name": "路邊小吃店", "address": "台中市西區", "phone": "",
          "source": "google_places", "reason": "評價高"}],
        id_key="id",
    )
    result = reservation.create_reservation_order("user-1", valid_payload(restaurant_id="g-place-1"))

    assert result["success"] is True
    assert result["status"] == "PENDING_PROVIDER"
    assert result["booking_url"] is None

    order = reservation.get_reservation_order("user-1", result["request_id"])
    assert order["order_items"]["restaurant_name"] == "路邊小吃店"
    assert order["order_items"]["source"] == "google_places"


def test_create_reservation_order_unknown_restaurant_not_found():
    result = reservation.create_reservation_order("user-1", valid_payload(restaurant_id="does-not-exist"))
    assert result["success"] is False
    assert result["error"]["code"] == "RESTAURANT_NOT_FOUND"


def test_create_reservation_order_expired_cache_is_not_found():
    result = reservation.create_reservation_order("user-1", valid_payload(restaurant_id="never-cached"))
    assert result["success"] is False
    assert result["error"]["code"] == "RESTAURANT_NOT_FOUND"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_reservation_service.py -v`
Expected: `test_create_reservation_order_for_cached_google_restaurant_is_pending` FAILS with `RESTAURANT_NOT_FOUND` (current code only checks `restaurant_catalog.get_restaurant`); the other two already pass against current behavior.

- [ ] **Step 3: Add `_resolve_restaurant` and wire it in**

In `backend/app/services/reservation.py`, add the import and helper near the top (after the existing imports):

```python
from . import external_search_cache
```

```python
def _resolve_restaurant(actor_id: str, restaurant_id: str) -> dict | None:
    restaurant = restaurant_catalog.get_restaurant(restaurant_id)
    if restaurant:
        return {**restaurant, "source": "internal"}
    cached = external_search_cache.get_result(actor_id, "restaurant_search", restaurant_id)
    if cached and cached.get("source") == "google_places":
        return {
            "id": cached["id"],
            "name": cached["name"],
            "address": cached.get("address", ""),
            "phone": cached.get("phone", ""),
            "supports_booking_api": False,
            "source": "google_places",
        }
    return None
```

Then update `_validate_payload` to take `actor_id` and use the resolver — change:

```python
def _validate_payload(payload: dict) -> dict | None:
```

to:

```python
def _validate_payload(actor_id: str, payload: dict) -> dict | None:
```

and inside it, change:

```python
    restaurant = restaurant_catalog.get_restaurant(payload["restaurant_id"])
    if not restaurant:
        return _error("RESTAURANT_NOT_FOUND", "找不到指定的餐廳。")
```

to:

```python
    restaurant = _resolve_restaurant(actor_id, payload["restaurant_id"])
    if not restaurant:
        return _error("RESTAURANT_NOT_FOUND", "找不到指定的餐廳。")
```

In `create_reservation_order`, update the two call sites:

```python
    validation_error = _validate_payload(payload)
```
→
```python
    validation_error = _validate_payload(actor_id, payload)
```

```python
    restaurant = restaurant_catalog.get_restaurant(payload["restaurant_id"])
```
→
```python
    restaurant = _resolve_restaurant(actor_id, payload["restaurant_id"])
```

Finally, add `"source": restaurant["source"]` to the `order_items` dict literal (right after `"restaurant_address": restaurant["address"],`):

```python
        "restaurant_address": restaurant["address"],
        "source": restaurant["source"],
```

No change is needed to the `if is_premium or not restaurant["supports_booking_api"]:` branch — `_resolve_restaurant` already sets `supports_booking_api: False` for Google-sourced picks, so they fall through the existing unsupported-restaurant path into `PENDING_PROVIDER` unchanged.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_reservation_service.py -v`
Expected: all passed

Also run the full reservation-related suite to check nothing else referenced the old `_validate_payload(payload)` signature:

Run: `cd backend && python -m pytest tests/test_reservation_service.py tests/test_reservations_api.py tests/test_agent_reservation_submit.py -v`
Expected: all passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/reservation.py backend/tests/test_reservation_service.py
git commit -m "feat: reservation accepts Google-sourced restaurants as pending cases via search cache"
```

---

### Task 8: Full-suite verification

**Files:** none (verification only)

- [ ] **Step 1: Run the entire backend test suite**

Run: `cd backend && python -m pytest -q`
Expected: 0 failures, 308 passed (this worktree's verified baseline was 6 failed / 302 passed before Task 3; Task 3 fixes all 6, and Tasks 1-2/4-7 add new passing tests on top — total count will be higher than 308 once those are included, but there must be 0 failures).

- [ ] **Step 2: Grep for any leftover Gemini references**

Run: `cd backend && grep -rn "gemini\|GEMINI\|google.genai" app/ --include=*.py`
Expected: no output (all Gemini code and config removed in Task 4).
