# 多任務統籌與家人協作功能 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let one voice/text message that contains multiple service requests (e.g. "買供品、訂餐廳、約打掃") be decomposed by Bedrock into a task queue, run sequentially through the existing single-service state machine, and end with a one-tap "分享給家人" summary — plus two small standalone additions (calendar aggregation, scam-message check) and a prompt-only dialect tuning pass.

**Architecture:** Everything is additive on top of `backend/app/agent/agent.py`'s existing per-session `state` dict and `backend/app/agent/llm.py`'s Bedrock-Converse wrapper functions. The multi-task queue reuses the *exact same* single-service fields (`service_id`, `service_schema`, `collected_fields`, …) as the "currently active task" slot, so `_chat_response()` in `api/chat.py` needs zero changes to its existing field mapping — only two new optional response fields (`task_cards`, `share_text`) are added. The family-share feature is pure frontend (Web Share API + clipboard fallback), calendar and scam-check are new, fully isolated read-only/stateless endpoints.

**Tech Stack:** FastAPI + Pydantic (backend), Amazon Bedrock Converse API via boto3 (`app/agent/llm.py`), Python's `unittest.mock`/`pytest` for tests, React + TypeScript + Vite + Tailwind (frontend), Vitest for frontend tests.

## Global Constraints

- Backend tests run with `USE_MOCK=true`, `AGENT_TOOL_MODE=embedded` (forced by `backend/tests/conftest.py`) — always mock `agent.llm.*` functions directly in tests rather than relying on live Bedrock calls failing.
- All new backend service functions must return `{"success": True, ...}` or `{"success": False, "error": {"code": ..., "message": ...}}`, matching every existing service module (`shop.py`, `reservation.py`, etc.).
- All new user-facing strings are Traditional Chinese, matching the rest of the codebase.
- Follow DESIGN.md: rounded-2xl/3xl cards, `--color-*` CSS variable tokens only (never raw hex in new components), no `border-left` accent bars, status always paired with text/icon not color alone.
- Run backend tests with `backend\.venv\Scripts\python.exe -m pytest backend/tests/<file> -v` from repo root. Run frontend tests with `npm test -- <file>` from `frontend/`.

---

## Task A1: Quick-purchase product catalog

**Files:**
- Modify: `backend/app/services/shop_catalog.py`
- Create: `backend/app/services/quick_purchase_catalog.py`
- Test: `backend/tests/test_quick_purchase_catalog.py`

**Interfaces:**
- Produces: `quick_purchase_catalog.match_bundle(query: str) -> dict | None` — returns `{"sku_id": str, "name": str, "keywords": list[str]}` or `None`.
- Produces: two new SKUs in `shop_catalog.SHOP_PRODUCTS`: `sku_fruit_offering_set`, `sku_three_sacrifice_set`, resolvable via existing `shop_catalog.get_sku(sku_id) -> tuple[dict, dict] | None`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_quick_purchase_catalog.py
from backend.app.services import quick_purchase_catalog, shop_catalog


def test_match_bundle_finds_fruit_offering_by_keyword():
    bundle = quick_purchase_catalog.match_bundle("幫我買拜拜用的水果")
    assert bundle is not None
    assert bundle["sku_id"] == "sku_fruit_offering_set"


def test_match_bundle_finds_three_sacrifice_by_keyword():
    bundle = quick_purchase_catalog.match_bundle("要準備三牲")
    assert bundle is not None
    assert bundle["sku_id"] == "sku_three_sacrifice_set"


def test_match_bundle_returns_none_for_unrelated_query():
    assert quick_purchase_catalog.match_bundle("我要一台洗衣機") is None


def test_quick_purchase_skus_resolve_in_shop_catalog():
    for sku_id in ("sku_fruit_offering_set", "sku_three_sacrifice_set"):
        resolved = shop_catalog.get_sku(sku_id)
        assert resolved is not None
        product, sku = resolved
        assert product["category_id"] == "cat_offering"
        assert product["product_type"] == "PHYSICAL"
        assert sku["unit_price"] > 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_quick_purchase_catalog.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'backend.app.services.quick_purchase_catalog'` and `get_sku` returns `None` for the new ids.

- [ ] **Step 3: Add the two products to `shop_catalog.py`**

Add to `SHOP_CATEGORIES` (after the last existing entry, `cat_health`):

```python
    {"id": "cat_offering", "name": "祭祀供品"},
```

Add to `SHOP_PRODUCTS` (append at the end of the list, before the closing `]`):

```python
    {
        "id": "prod_fruit_offering_set",
        "store_id": "store_carrefour",
        "category_id": "cat_offering",
        "name": "清明祭祖水果盆",
        "description": "當季水果組合，附提籃包裝，適合掃墓祭祖使用。",
        "product_type": "PHYSICAL",
        "image": None,
        "specs": [],
        "skus": [
            {"sku_id": "sku_fruit_offering_set", "attributes": {}, "unit_price": 599, "unit_points": 59},
        ],
    },
    {
        "id": "prod_three_sacrifice_set",
        "store_id": "store_carrefour",
        "category_id": "cat_offering",
        "name": "三牲祭祀組合",
        "description": "雞、魚、豬肉三牲組合，祭祖拜拜適用，冷藏配送。",
        "product_type": "PHYSICAL",
        "image": None,
        "specs": [],
        "skus": [
            {"sku_id": "sku_three_sacrifice_set", "attributes": {}, "unit_price": 880, "unit_points": 88},
        ],
    },
```

- [ ] **Step 4: Create `quick_purchase_catalog.py`**

```python
# backend/app/services/quick_purchase_catalog.py
"""Keyword-matched bundles for one-shot 'quick purchase' requests.

Used by the multi-task orchestrator (see app/agent/agent.py) so a task like
"買供品跟水果" resolves straight to a single-SKU order instead of the full
shop_purchase cart/browse flow.
"""
from __future__ import annotations

QUICK_PURCHASE_BUNDLES: list[dict] = [
    {
        "sku_id": "sku_fruit_offering_set",
        "name": "清明祭祖水果盆",
        "keywords": ["水果", "供品", "祭拜", "拜拜", "祭祖", "水果盆"],
    },
    {
        "sku_id": "sku_three_sacrifice_set",
        "name": "三牲祭祀組合",
        "keywords": ["三牲", "牲禮", "祭祀"],
    },
]


def match_bundle(query: str) -> dict | None:
    for bundle in QUICK_PURCHASE_BUNDLES:
        if any(keyword in query for keyword in bundle["keywords"]):
            return bundle
    return None
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_quick_purchase_catalog.py -v`
Expected: PASS (4 tests)

- [ ] **Step 6: Seed stock for the new SKUs (local dev only, not a test step)**

Run once from repo root so local/demo runs have stock for the new SKUs (mirrors how every other shop SKU gets its starting stock — `seed_stock()` already iterates `shop_catalog.SHOP_PRODUCTS`, so no script changes are needed):

Run: `backend\.venv\Scripts\python.exe backend\scripts\seed_shop_points.py`

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/shop_catalog.py backend/app/services/quick_purchase_catalog.py backend/tests/test_quick_purchase_catalog.py
git commit -m "feat: add quick-purchase offering bundles (fruit/three-sacrifice sets)"
```

---

## Task A2: `quick_purchase` service — one-shot bundle ordering via the existing generic flow

**Files:**
- Modify: `backend/app/services/catalog.py`
- Create: `backend/app/services/quick_purchase.py`
- Modify: `backend/app/agent/agent.py:1503-1511` (the `_submit` dispatch block) and `_display_service_name`/`SERVICE_DISPLAY_NAMES` (lines 41-47, 191-200)
- Test: `backend/tests/test_quick_purchase_service.py`, `backend/tests/test_agent_quick_purchase_submit.py`

**Interfaces:**
- Consumes: `shop.create_shop_order(actor_id: str, payload: dict) -> dict` (existing, `backend/app/services/shop.py:91`), `quick_purchase_catalog.match_bundle(query: str) -> dict | None` (Task A1).
- Produces: `quick_purchase.create_quick_purchase_order(actor_id: str, query: str, *, contact_name: str, phone: str, address: str) -> dict` returning `{"success": True, "request_id": ..., "status": ..., "bundle_name": ...}` or `{"success": False, "error": {...}}`.
- Produces: catalog service id `"quick_purchase"` with fields `query` (textarea), `address` (text), `phone` (text) — same shape every other generic-flow service uses, so `_continue_generic_collection` handles it with zero changes.

- [ ] **Step 1: Write the failing service-level test**

```python
# backend/tests/test_quick_purchase_service.py
import tempfile
from pathlib import Path

import pytest

from backend.app.services import quick_purchase, shop, store as store_module


@pytest.fixture(autouse=True)
def isolated_store(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        test_store = store_module.MemoryStore(storage_path=Path(tmp) / "store.json")
        monkeypatch.setattr(store_module, "STORE", test_store)
        monkeypatch.setattr(shop, "STORE", test_store)
        test_store.restock_sku("sku_fruit_offering_set", 5)
        yield test_store


def test_create_quick_purchase_order_matches_bundle_and_submits():
    result = quick_purchase.create_quick_purchase_order(
        "user-a",
        "拜拜要用的水果",
        contact_name="王添財",
        phone="0912345678",
        address="台中市西屯區文心路一段1號",
    )
    assert result["success"] is True
    assert result["bundle_name"] == "清明祭祖水果盆"
    assert result["request_id"]


def test_create_quick_purchase_order_unmatched_query_fails():
    result = quick_purchase.create_quick_purchase_order(
        "user-a", "我要買一台冷氣", contact_name="王添財", phone="0912345678", address="台中市"
    )
    assert result["success"] is False
    assert result["error"]["code"] == "BUNDLE_NOT_FOUND"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_quick_purchase_service.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'backend.app.services.quick_purchase'`

- [ ] **Step 3: Create `quick_purchase.py`**

```python
# backend/app/services/quick_purchase.py
"""One-shot 'quick purchase' order: match free text to a curated bundle and submit directly."""
from __future__ import annotations

from . import quick_purchase_catalog, shop


def create_quick_purchase_order(
    actor_id: str, query: str, *, contact_name: str, phone: str, address: str
) -> dict:
    bundle = quick_purchase_catalog.match_bundle(query)
    if not bundle:
        return {
            "success": False,
            "error": {"code": "BUNDLE_NOT_FOUND", "message": f"找不到符合「{query}」的商品組合"},
        }

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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_quick_purchase_service.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Add the `quick_purchase` service to `catalog.py`**

Add to `SERVICES` in `backend/app/services/catalog.py` (after the `home_cleaning` entry, before `health_product_recommendation`):

```python
    {
        "id": "quick_purchase",
        "name": "快速下單",
        "description": "供品、水果等常用組合，說出需求直接下單，不用逛商城",
        "service_vendor_id": None,
        "cms_type": None,
        "enabled": True,
        "keywords": ["供品", "三牲", "水果盆", "祭拜", "祭祖", "牲禮"],
        "schema": {
            "fields": [
                {
                    "id": "query",
                    "label": "想買的東西",
                    "type": "textarea",
                    "required": True,
                    "question": "想買點什麼呢？例如供品或水果。",
                },
                {
                    "id": "address",
                    "label": "收件地址",
                    "type": "text",
                    "required": True,
                    "question": "請提供收件地址。",
                },
                {
                    "id": "phone",
                    "label": "聯絡電話",
                    "type": "text",
                    "required": True,
                    "question": "請提供聯絡電話。",
                },
            ]
        },
    },
```

- [ ] **Step 6: Write the failing agent-level test**

```python
# backend/tests/test_agent_quick_purchase_submit.py
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from backend.app.agent import agent
from backend.app.services import shop, store as store_module


@pytest.fixture(autouse=True)
def isolated_store(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        test_store = store_module.MemoryStore(storage_path=Path(tmp) / "store.json")
        monkeypatch.setattr(store_module, "STORE", test_store)
        monkeypatch.setattr(shop, "STORE", test_store)
        test_store.restock_sku("sku_fruit_offering_set", 5)
        yield test_store


def _run_turn(state, message, actor_id="user-1", session_id="sess-1"):
    return agent.handle_message(actor_id, session_id, state, message)


def test_quick_purchase_chat_flow_creates_order_end_to_end():
    state = agent.new_state()

    with patch(
        "backend.app.agent.agent._available_services",
        return_value=[{"id": "quick_purchase", "name": "快速下單", "description": "供品、水果等常用組合"}],
    ), patch("backend.app.agent.agent.llm.extract_fields", return_value={}), patch(
        "backend.app.agent.agent.llm.plan_form_turn", return_value=None
    ), patch(
        "backend.app.agent.agent.llm.plan_turn", return_value=None
    ):
        result = _run_turn(state, "幫我買拜拜用的水果")
        state = result["state"]
        assert state["service_id"] == "quick_purchase"

        result = _run_turn(state, "台中市西屯區文心路一段1號")
        state = result["state"]
        result = _run_turn(state, "0912345678")
        state = result["state"]
        assert state["awaiting_confirmation"] is True

        result = _run_turn(state, "確認送出")
        assert result["state"]["request_id"]
        assert result["state"]["status"] == "SUBMITTED"
```

- [ ] **Step 7: Run test to verify it fails**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_agent_quick_purchase_submit.py -v`
Expected: FAIL — submit routes into the generic `tools.call("submit_service_request", ...)` path instead of `quick_purchase.create_quick_purchase_order`, so `request_id` comes back `None`/error (`quick_purchase` isn't a registered catalog service in the embedded tool, or the generic submit rejects the free-form fields).

- [ ] **Step 8: Wire `quick_purchase` into `agent.py`**

In `backend/app/agent/agent.py`, add to `SERVICE_DISPLAY_NAMES` (around line 41-47):

```python
SERVICE_DISPLAY_NAMES = {
    "plumbing_repair": "水電修繕",
    "washing_machine_cleaning": "洗衣機清洗",
    "air_conditioner_cleaning": "冷氣清洗",
    "home_cleaning": "居家清潔",
    "food_delivery": "美食外送",
    "quick_purchase": "快速下單",
}
```

Add the same key to the `names` dict inside `_display_service_name` (around line 191-200):

```python
def _display_service_name(service_id: str | None, fallback: str | None = None) -> str:
    names = {
        "plumbing_repair": "水電修繕",
        "washing_machine_cleaning": "洗衣機清洗",
        "air_conditioner_cleaning": "冷氣清洗",
        "home_cleaning": "居家清潔",
        "quick_purchase": "快速下單",
    }
```

Import the new service module at the top of `agent.py` (alongside the existing `from ..services import delivery, delivery_catalog, reservation, shipping` line):

```python
from ..services import delivery, delivery_catalog, quick_purchase, reservation, shipping
```

Add a new submit branch in `_submit()` (around line 1503, alongside the `restaurant_reservation`/`food_delivery`/`package_shipping` branches):

```python
    if state["service_id"] == "quick_purchase":
        return _submit_quick_purchase(actor_id, state, latest_user_message)
```

Add the new `_submit_quick_purchase` function (place it next to `_submit_reservation`, around line 1566):

```python
def _submit_quick_purchase(actor_id: str, state: dict, latest_user_message: str) -> dict:
    collected = state["collected_fields"]
    result = quick_purchase.create_quick_purchase_order(
        actor_id,
        collected.get("query", ""),
        contact_name=state.get("service_name") and "住戶" or "住戶",
        phone=collected.get("phone", ""),
        address=collected.get("address", ""),
    )

    if not result.get("success"):
        message = result.get("error", {}).get("message", "下單失敗")
        return _reply(
            state,
            _model_reply(
                actor_id,
                state,
                "submit_error",
                latest_user_message=latest_user_message,
                error_message=message,
            ),
        )

    state["request_id"] = result["request_id"]
    state["status"] = result["status"]
    state["awaiting_confirmation"] = False
    reply = _model_reply(
        actor_id,
        state,
        "submit_success",
        latest_user_message=latest_user_message,
        request_id=result["request_id"],
    )
    return _reply(state, f"{reply}\n已幫您選購「{result.get('bundle_name', '')}」。")
```

(The `contact_name and "住戶" or "住戶"` is intentionally always `"住戶"` — `quick_purchase`'s schema has no `contact_name` field since the persona scenario never asks for one by voice; simplify to a literal:)

```python
        contact_name="住戶",
```

- [ ] **Step 9: Run test to verify it passes**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_agent_quick_purchase_submit.py -v`
Expected: PASS

- [ ] **Step 10: Run the full backend test suite to check for regressions**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests -v`
Expected: All PASS (no existing test touches `catalog.SERVICES` length/order in a way that would break, but confirm)

- [ ] **Step 11: Commit**

```bash
git add backend/app/services/quick_purchase.py backend/app/services/catalog.py backend/app/agent/agent.py backend/tests/test_quick_purchase_service.py backend/tests/test_agent_quick_purchase_submit.py
git commit -m "feat: add quick_purchase one-shot bundle ordering service"
```

---

## Task A3: Bedrock multi-task planning (`llm.py`)

**Files:**
- Modify: `backend/app/agent/llm.py`
- Test: `backend/tests/test_llm_multi_task.py`

**Interfaces:**
- Produces: `llm.plan_multi_task(*, message: str, services: list[dict], short_term_memory: str = "", long_term_memory: str = "") -> list[dict]`, each item `{"service_id": str, "hint_fields": dict}`.
- Modifies: `llm.plan_turn(...)`'s accepted `mode` values now include `"multi_task"` (existing return shape `{"mode": ..., "reply": ..., "service_id": ...}` unchanged).

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_llm_multi_task.py
from unittest.mock import patch

from backend.app.agent import llm

SERVICES = [
    {"id": "quick_purchase", "name": "快速下單", "description": "供品、水果等常用組合"},
    {"id": "restaurant_reservation", "name": "餐廳訂位", "description": "22世紀風味館 精選餐廳訂位服務"},
    {"id": "home_cleaning", "name": "居家清潔", "description": "日常打掃與深度整理服務"},
]


def test_plan_multi_task_returns_validated_tasks():
    fake_payload = {
        "tasks": [
            {"service_id": "quick_purchase", "hint_fields": {"query": "供品跟水果"}},
            {"service_id": "restaurant_reservation", "hint_fields": {}},
            {"service_id": "not_a_real_service", "hint_fields": {}},
        ]
    }
    with patch("backend.app.agent.llm._converse_json", return_value=fake_payload):
        tasks = llm.plan_multi_task(message="買供品、訂餐廳", services=SERVICES)

    assert tasks == [
        {"service_id": "quick_purchase", "hint_fields": {"query": "供品跟水果"}},
        {"service_id": "restaurant_reservation", "hint_fields": {}},
    ]


def test_plan_multi_task_returns_empty_list_when_client_unavailable():
    with patch("backend.app.agent.llm._converse_json", return_value=None):
        assert llm.plan_multi_task(message="隨便說說", services=SERVICES) == []


def test_plan_turn_accepts_multi_task_mode():
    fake_payload = {"mode": "multi_task", "reply": None, "service_id": None}
    with patch("backend.app.agent.llm._converse_json", return_value=fake_payload):
        plan = llm.plan_turn(message="買供品、訂餐廳、約打掃", services=SERVICES)

    assert plan == {"mode": "multi_task", "reply": None, "service_id": None}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_llm_multi_task.py -v`
Expected: FAIL — `plan_multi_task` doesn't exist yet; `plan_turn` rejects `mode="multi_task"` (returns `None` since it's not in the current allowed set).

- [ ] **Step 3: Extend `_TURN_SYSTEM` and add `_MULTI_TASK_SYSTEM` + `plan_multi_task`**

In `backend/app/agent/llm.py`, replace the `_TURN_SYSTEM` constant (lines 25-38) with:

```python
_TURN_SYSTEM = (
    "You are the first-turn router for a Taiwanese home services assistant speaking Traditional Chinese. "
    "Decide whether the latest user message should be handled as one of: "
    "\"chat\", \"service_request\", \"page_help\", \"memory_query\", \"multi_task\", or \"unknown\". "
    "Use \"chat\" for greetings, identity/capability questions, small talk, or short direct conversational replies. "
    "Use \"service_request\" when the user wants to book/apply/arrange exactly one supported service. "
    "Use \"multi_task\" only when the message clearly asks for two or more distinct, independent services in one "
    "sentence (for example: buying an item AND booking a restaurant AND booking a cleaning service). "
    "Use \"page_help\" when the user is asking where something is in the app, what the current page does, or how to navigate. "
    "Use \"memory_query\" when the user is asking about previously used address/phone/service/order details. "
    "If mode is \"chat\", include a natural direct reply in Traditional Chinese. "
    "If mode is \"service_request\" and a service is clear, include the best matching service_id from the provided list; otherwise use null. "
    "If mode is \"multi_task\", leave service_id null — the tasks themselves are resolved separately. "
    "Do not invent unsupported services. "
    "Return JSON only in the format "
    "{\"mode\":\"chat|service_request|page_help|memory_query|multi_task|unknown\",\"reply\":string|null,\"service_id\":string|null}."
)

_MULTI_TASK_SYSTEM = (
    "You detect whether a Taiwanese home-services user message contains more than one distinct "
    "service request in a single sentence (e.g. buying an item, booking a restaurant, and booking "
    "a cleaning service all in one message). "
    "Only return tasks when there are genuinely two or more independent service requests; otherwise return an empty list. "
    "For each task, choose the best matching service_id from the provided list. "
    "Also extract any field values you can already tell from the message as hint_fields — use only field ids that "
    "make sense for that service (dates, quantities, addresses, etc.); if unsure, leave hint_fields empty. "
    "Do not invent unsupported services. "
    "Return JSON only in the format "
    "{\"tasks\": [{\"service_id\": string, \"hint_fields\": object}]}."
)
```

Update the `mode not in {...}` check inside `plan_turn` (around line 226) to include the new mode:

```python
    mode = payload.get("mode")
    if mode not in {"chat", "service_request", "page_help", "memory_query", "multi_task", "unknown"}:
        return None
```

Add `plan_multi_task` after `plan_turn` (after line 237):

```python
def plan_multi_task(
    *,
    message: str,
    services: list[dict],
    short_term_memory: str = "",
    long_term_memory: str = "",
) -> list[dict]:
    prompt = (
        f"Today is {date.today().isoformat()}.\n"
        f"Short-term memory:\n{short_term_memory or 'None'}\n\n"
        f"Long-term memory:\n{long_term_memory or 'None'}\n\n"
        f"Available services:\n{json.dumps(services, ensure_ascii=False, indent=2)}\n\n"
        f"User message:\n{message}"
    )
    payload = _converse_json(_MULTI_TASK_SYSTEM, prompt, max_tokens=512)
    if not payload or not isinstance(payload.get("tasks"), list):
        return []

    valid_ids = {service["id"] for service in services}
    tasks: list[dict] = []
    for task in payload["tasks"]:
        if not isinstance(task, dict):
            continue
        service_id = task.get("service_id")
        if service_id not in valid_ids:
            continue
        hint_fields = task.get("hint_fields")
        tasks.append({
            "service_id": service_id,
            "hint_fields": hint_fields if isinstance(hint_fields, dict) else {},
        })
    return tasks
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_llm_multi_task.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Run the full backend test suite to check for regressions**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests -v`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/agent/llm.py backend/tests/test_llm_multi_task.py
git commit -m "feat: add Bedrock multi-task planning (plan_multi_task, multi_task turn mode)"
```

---

## Task A4: Multi-task state machine in `agent.py` — detection, task cards, sequential execution

**Files:**
- Modify: `backend/app/agent/agent.py`
- Test: `backend/tests/test_agent_multi_task.py`

**Interfaces:**
- Consumes: `llm.plan_turn(...)` returning `mode="multi_task"` (Task A3), `llm.plan_multi_task(...)` (Task A3).
- Produces: `agent.new_state()` gains keys `is_multi_task: bool`, `pending_tasks: list[dict]`, `awaiting_task_selection: bool`, `completed_task_summaries: list[str]`.
- Produces: `agent._reply(...)` gains optional kwargs `task_cards: list[dict] | None`, `share_text: str | None`; the returned dict from `handle_message` now always includes `"task_cards"` and `"share_text"` keys (both `None` when not applicable) alongside the existing `reply`/`state`/`redirect_path`/`redirect_requires_confirmation`/`debug_trace` keys.

- [ ] **Step 1: Write the failing end-to-end test**

```python
# backend/tests/test_agent_multi_task.py
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from backend.app.agent import agent
from backend.app.services import shop, store as store_module

SERVICES = [
    {"id": "quick_purchase", "name": "快速下單", "description": "供品、水果等常用組合"},
    {"id": "home_cleaning", "name": "居家清潔", "description": "日常打掃與深度整理服務"},
]

TASKS = [
    {"service_id": "quick_purchase", "hint_fields": {}},
    {"service_id": "home_cleaning", "hint_fields": {}},
]


@pytest.fixture(autouse=True)
def isolated_store(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        test_store = store_module.MemoryStore(storage_path=Path(tmp) / "store.json")
        monkeypatch.setattr(store_module, "STORE", test_store)
        monkeypatch.setattr(shop, "STORE", test_store)
        test_store.restock_sku("sku_fruit_offering_set", 5)
        yield test_store


def _run_turn(state, message, actor_id="user-1", session_id="sess-1"):
    return agent.handle_message(actor_id, session_id, state, message)


def test_multi_task_message_returns_task_cards_and_awaits_selection():
    state = agent.new_state()
    with patch("backend.app.agent.agent._available_services", return_value=SERVICES), patch(
        "backend.app.agent.agent.llm.plan_turn",
        return_value={"mode": "multi_task", "reply": None, "service_id": None},
    ), patch("backend.app.agent.agent.llm.plan_multi_task", return_value=TASKS):
        result = _run_turn(state, "幫我買供品，也約一下打掃")

    assert result["task_cards"] == [
        {"service_id": "quick_purchase", "service_name": "快速下單"},
        {"service_id": "home_cleaning", "service_name": "居家清潔"},
    ]
    assert result["state"]["awaiting_task_selection"] is True
    assert result["state"]["pending_tasks"] == TASKS


def test_multi_task_full_flow_runs_both_tasks_and_produces_share_text():
    state = agent.new_state()
    common_patches = [
        patch("backend.app.agent.agent._available_services", return_value=SERVICES),
        patch("backend.app.agent.agent.llm.extract_fields", return_value={}),
        patch("backend.app.agent.agent.llm.plan_form_turn", return_value=None),
    ]
    with patch(
        "backend.app.agent.agent.llm.plan_turn",
        return_value={"mode": "multi_task", "reply": None, "service_id": None},
    ), patch("backend.app.agent.agent.llm.plan_multi_task", return_value=TASKS), \
        common_patches[0], common_patches[1], common_patches[2]:
        result = _run_turn(state, "幫我買供品，也約一下打掃")
        state = result["state"]
        assert state["awaiting_task_selection"] is True

        # Accept both tasks in the given order.
        result = _run_turn(state, "都要")
        state = result["state"]
        assert state["service_id"] == "quick_purchase"

        # quick_purchase fields: query, address, phone.
        result = _run_turn(state, "供品跟水果")
        state = result["state"]
        result = _run_turn(state, "台中市西屯區文心路一段1號")
        state = result["state"]
        result = _run_turn(state, "0912345678")
        state = result["state"]
        assert state["awaiting_confirmation"] is True

        result = _run_turn(state, "確認送出")
        state = result["state"]
        # First task done, should have advanced straight into home_cleaning collection.
        assert state["service_id"] == "home_cleaning"
        assert len(state["completed_task_summaries"]) == 1

        # home_cleaning fields: cleaning_service_option, preferred_date, preferred_time_slot, address, phone.
        result = _run_turn(state, "地板清潔")
        state = result["state"]
        result = _run_turn(state, "明天")
        state = result["state"]
        result = _run_turn(state, "14:00")
        state = result["state"]
        result = _run_turn(state, "台中市西屯區文心路一段1號")
        state = result["state"]
        result = _run_turn(state, "0912345678")
        state = result["state"]
        assert state["awaiting_confirmation"] is True

        result = _run_turn(state, "確認送出")

    assert result["state"]["is_multi_task"] is False
    assert result["share_text"]
    assert "快速下單" in result["share_text"]
    assert "居家清潔" in result["share_text"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_agent_multi_task.py -v`
Expected: FAIL — `result["task_cards"]` raises `KeyError` (key doesn't exist yet); multi-task mode isn't handled by `handle_message`.

- [ ] **Step 3: Add multi-task fields to `new_state()`**

In `backend/app/agent/agent.py`, extend the dict returned by `new_state()` (around line 887-912) — add these four keys anywhere in the dict:

```python
        "is_multi_task": False,
        "pending_tasks": [],
        "awaiting_task_selection": False,
        "completed_task_summaries": [],
```

- [ ] **Step 4: Extend `_reply()` with `task_cards`/`share_text`**

Replace the `_reply` function (around line 1756-1768):

```python
def _reply(
    state: dict,
    reply: str,
    redirect_path: str | None = None,
    redirect_requires_confirmation: bool = False,
    task_cards: list[dict] | None = None,
    share_text: str | None = None,
) -> dict:
    return {
        "reply": reply,
        "state": state,
        "redirect_path": redirect_path,
        "redirect_requires_confirmation": redirect_requires_confirmation,
        "debug_trace": state.get("debug_trace", {}),
        "task_cards": task_cards,
        "share_text": share_text,
    }
```

- [ ] **Step 5: Add task-card building, selection parsing, and sequential execution helpers**

Add these functions near `_continue_collection` (after line 1336's `_continue_collection` definition):

```python
def _task_cards(tasks: list[dict]) -> list[dict]:
    return [
        {"service_id": task["service_id"], "service_name": _display_service_name(task["service_id"])}
        for task in tasks
    ]


def _select_multi_tasks(text: str, pending_tasks: list[dict], services: list[dict]) -> list[dict]:
    if _is_yes(text) or any(word in text for word in ("全部", "都要", "都做", "全都要")):
        return pending_tasks
    name_by_id = {service["id"]: service.get("name", "") for service in services}
    selected = [
        task
        for task in pending_tasks
        if name_by_id.get(task["service_id"]) and name_by_id[task["service_id"]] in text
    ]
    return selected or pending_tasks


def _start_next_multi_task(
    actor_id: str,
    state: dict,
    auth_token: str | None,
    transition_prefix: str | None = None,
) -> dict:
    if not state["pending_tasks"]:
        summary = "\n".join(state["completed_task_summaries"])
        state["is_multi_task"] = False
        reply = f"任務都完成了！\n{summary}" if summary else "目前沒有任務可以彙總。"
        return _reply(state, reply, share_text=summary or None) if not transition_prefix else _prepend_reply(
            _reply(state, reply, share_text=summary or None), transition_prefix
        )

    task = state["pending_tasks"].pop(0)
    schema_result = _service_schema(task["service_id"], auth_token)
    if not schema_result:
        # Broken/unavailable service schema — skip this task and try the next one.
        return _start_next_multi_task(actor_id, state, auth_token, transition_prefix)

    services = _available_services(auth_token) or []
    service = next((item for item in services if item["id"] == task["service_id"]), None)
    state["service_id"] = task["service_id"]
    state["service_name"] = _display_service_name(
        task["service_id"], (service or {}).get("name") or schema_result.get("title")
    )
    state["service_schema"] = {"fields": schema_result["fields"]}
    state["collected_fields"] = {}
    _recompute_missing(state)

    hint_fields = task.get("hint_fields") or {}
    if hint_fields:
        normalized_hints = _normalize_candidate_fields(state, hint_fields, "", source="multi_task_hint")
        state["collected_fields"].update(normalized_hints)
        _recompute_missing(state)

    result = _continue_collection(actor_id, state, latest_user_message="")
    return _prepend_reply(result, transition_prefix)


def _submit_and_continue_multi_task(
    actor_id: str,
    session_id: str,
    state: dict,
    text: str,
    auth_token: str | None,
) -> dict:
    result = _submit(actor_id, session_id, state, latest_user_message=text, auth_token=auth_token)
    if not state.get("is_multi_task") or not state.get("request_id"):
        return result

    completed_name = _display_service_name(state["service_id"], state["service_name"])
    state["completed_task_summaries"].append(f"{completed_name}：{result['reply']}")
    state["service_id"] = None
    state["service_name"] = None
    state["service_schema"] = None
    state["collected_fields"] = {}
    state["missing_fields"] = []
    state["request_id"] = None
    state["status"] = "COLLECTING_INFORMATION"
    return _start_next_multi_task(actor_id, state, auth_token, transition_prefix=result["reply"])


def _handle_task_selection_reply(actor_id: str, state: dict, text: str, auth_token: str | None) -> dict:
    services = _available_services(auth_token) or []
    state["pending_tasks"] = _select_multi_tasks(text, state["pending_tasks"], services)
    state["awaiting_task_selection"] = False
    return _start_next_multi_task(actor_id, state, auth_token)
```

- [ ] **Step 6: Wire detection and dispatch into `handle_message`**

In `handle_message` (`backend/app/agent/agent.py`), add a check for `awaiting_task_selection` near the top, right after the existing `if state.get("pending_pref_field"):` block ends and before `if state["awaiting_confirmation"]:` (around line 1126-1128):

```python
    if state.get("awaiting_task_selection"):
        return _handle_task_selection_reply(actor_id, state, text, auth_token)
```

Replace the direct `_submit(...)` call inside the confirmation-yes branch (around line 1135-1137):

```python
        verdict = _judge_reply("請確認以上內容是否正確，若正確請回覆確認送出。", text)
        if verdict == "yes":
            return _submit(actor_id, session_id, state, latest_user_message=text, auth_token=auth_token)
```

with:

```python
        verdict = _judge_reply("請確認以上內容是否正確，若正確請回覆確認送出。", text)
        if verdict == "yes":
            return _submit_and_continue_multi_task(actor_id, session_id, state, text, auth_token)
```

Inside the `if turn_plan:` dispatch chain in `handle_message` (around line 1174-1196), add a new branch for `"multi_task"` right after the existing `if turn_plan["mode"] == "service_request":` block:

```python
                if turn_plan["mode"] == "service_request":
                    planned_service_id = turn_plan.get("service_id")
                if turn_plan["mode"] == "multi_task":
                    tasks = llm.plan_multi_task(
                        message=text,
                        services=services,
                        short_term_memory=short_term_context,
                        long_term_memory=long_term_context,
                    )
                    if len(tasks) >= 2:
                        state["is_multi_task"] = True
                        state["pending_tasks"] = tasks
                        state["awaiting_task_selection"] = True
                        names = "、".join(_display_service_name(t["service_id"]) for t in tasks)
                        reply = f"收到！我幫您整理了 {len(tasks)} 個任務：{names}。請問要全部進行，還是先從哪幾項開始呢？"
                        return _reply(state, reply, task_cards=_task_cards(tasks))
                    # Fewer than 2 real tasks resolved — fall through to normal single-service handling below.
```

- [ ] **Step 7: Run test to verify it passes**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_agent_multi_task.py -v`
Expected: PASS (2 tests)

- [ ] **Step 8: Run the full backend test suite to check for regressions**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests -v`
Expected: All PASS — pay particular attention to `test_agent_regressions.py` and `test_agent_reservation_submit.py`/`test_agent_delivery_submit.py`, since `_submit` call sites changed.

- [ ] **Step 9: Commit**

```bash
git add backend/app/agent/agent.py backend/tests/test_agent_multi_task.py
git commit -m "feat: add multi-task orchestration state machine to agent.py"
```

---

## Task A5: Expose `task_cards`/`share_text` through the chat API

**Files:**
- Modify: `backend/app/models/chat.py`
- Modify: `backend/app/api/chat.py`
- Test: `backend/tests/test_chat_multi_task_api.py`

**Interfaces:**
- Consumes: `handle_message(...)` result dict now includes `"task_cards"` and `"share_text"` (Task A4).
- Produces: `ChatResponse` gains `task_cards: list[dict] | None = None` and `share_text: str | None = None`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_chat_multi_task_api.py
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.app.main import app


def _login_and_session(client: TestClient):
    accounts = client.get("/api/auth/demo-accounts").json()["accounts"]
    token = accounts[0]["token"]
    headers = {"Authorization": f"Bearer {token}"}
    session = client.post("/api/sessions", headers=headers)
    return headers, session.json()["session_id"]


def test_chat_response_includes_task_cards_field():
    client = TestClient(app)
    headers, session_id = _login_and_session(client)
    fake_tasks = [
        {"service_id": "quick_purchase", "hint_fields": {}},
        {"service_id": "home_cleaning", "hint_fields": {}},
    ]
    with patch(
        "backend.app.agent.agent.llm.plan_turn",
        return_value={"mode": "multi_task", "reply": None, "service_id": None},
    ), patch("backend.app.agent.agent.llm.plan_multi_task", return_value=fake_tasks):
        response = client.post(
            "/api/chat",
            headers=headers,
            json={"session_id": session_id, "message": "幫我買供品，也約一下打掃"},
        )

    body = response.json()
    assert response.status_code == 200
    assert body["task_cards"] == [
        {"service_id": "quick_purchase", "service_name": "快速下單"},
        {"service_id": "home_cleaning", "service_name": "居家清潔"},
    ]
    assert body["share_text"] is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_chat_multi_task_api.py -v`
Expected: FAIL — `KeyError: 'task_cards'` (Pydantic drops unknown dict keys silently unless declared as a field, so the response body has no `task_cards` key)

- [ ] **Step 3: Add the fields to `ChatResponse`**

In `backend/app/models/chat.py`, add to `ChatResponse` (after line 29's `debug_trace: dict = {}`):

```python
    task_cards: list[dict] | None = None
    share_text: str | None = None
```

- [ ] **Step 4: Wire them through `_chat_response()`**

In `backend/app/api/chat.py`, add to the `ChatResponse(...)` construction inside `_chat_response` (after line 50's `debug_trace=...`):

```python
        task_cards=result.get("task_cards"),
        share_text=result.get("share_text"),
```

- [ ] **Step 5: Run test to verify it passes**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_chat_multi_task_api.py -v`
Expected: PASS

- [ ] **Step 6: Run the full backend test suite to check for regressions**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests -v`
Expected: All PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/models/chat.py backend/app/api/chat.py backend/tests/test_chat_multi_task_api.py
git commit -m "feat: expose task_cards and share_text on the chat API response"
```

---

## Task A6: Frontend — render task cards and the family-share button in the chat panel

**Files:**
- Modify: `frontend/src/types/request.ts`
- Modify: `frontend/src/components/ChatMessage.tsx`
- Modify: `frontend/src/components/ButlerPanel.tsx`
- Create: `frontend/src/components/ShareWithFamilyButton.tsx`
- Create: `frontend/src/components/TaskCardList.tsx`
- Test: `frontend/src/components/ShareWithFamilyButton.test.tsx`, `frontend/src/components/TaskCardList.test.tsx`

**Interfaces:**
- Consumes: `ChatResponse.task_cards: {service_id: string, service_name: string}[] | null`, `ChatResponse.share_text: string | null` (Task A5).
- Produces: `<ShareWithFamilyButton text={string} />` — self-contained, no props beyond the text to share.
- Produces: `<TaskCardList cards={{service_id: string, service_name: string}[]} />` — pure display, no callbacks (selection happens via the normal chat text input, matching the "一次一問" conversational pattern already used everywhere else in this panel).

- [ ] **Step 1: Write the failing component tests**

```tsx
// frontend/src/components/ShareWithFamilyButton.test.tsx
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi, afterEach } from "vitest";
import { ShareWithFamilyButton } from "./ShareWithFamilyButton";

describe("ShareWithFamilyButton", () => {
  afterEach(() => {
    // @ts-expect-error test cleanup of a browser API that may not exist by default
    delete navigator.share;
    // @ts-expect-error test cleanup
    delete navigator.clipboard;
  });

  it("calls navigator.share when available", () => {
    const shareMock = vi.fn().mockResolvedValue(undefined);
    // @ts-expect-error jsdom has no navigator.share by default
    navigator.share = shareMock;

    render(<ShareWithFamilyButton text="水果訂好了，餐廳也訂好了。" />);
    fireEvent.click(screen.getByRole("button", { name: "分享給家人" }));

    expect(shareMock).toHaveBeenCalledWith({
      title: "AI 管家任務完成通知",
      text: "水果訂好了，餐廳也訂好了。",
    });
  });

  it("falls back to clipboard copy when navigator.share is unavailable", async () => {
    const writeTextMock = vi.fn().mockResolvedValue(undefined);
    // @ts-expect-error jsdom has no navigator.clipboard by default
    navigator.clipboard = { writeText: writeTextMock };

    render(<ShareWithFamilyButton text="水果訂好了。" />);
    fireEvent.click(screen.getByRole("button", { name: "分享給家人" }));

    expect(writeTextMock).toHaveBeenCalledWith("水果訂好了。");
    expect(await screen.findByText(/已複製訊息/)).toBeInTheDocument();
  });
});
```

```tsx
// frontend/src/components/TaskCardList.test.tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { TaskCardList } from "./TaskCardList";

describe("TaskCardList", () => {
  it("renders one card per task with its service name", () => {
    render(
      <TaskCardList
        cards={[
          { service_id: "quick_purchase", service_name: "快速下單" },
          { service_id: "home_cleaning", service_name: "居家清潔" },
        ]}
      />,
    );

    expect(screen.getByText("快速下單")).toBeInTheDocument();
    expect(screen.getByText("居家清潔")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run (from `frontend/`): `npm test -- ShareWithFamilyButton TaskCardList`
Expected: FAIL — modules don't exist yet.

- [ ] **Step 3: Create `ShareWithFamilyButton.tsx`**

```tsx
// frontend/src/components/ShareWithFamilyButton.tsx
import { useState } from "react";
import { ServiceIcon } from "./ServiceIcon";
import { Toast } from "./Toast";

interface Props {
  text: string;
}

export function ShareWithFamilyButton({ text }: Props) {
  const [toastText, setToastText] = useState<string | null>(null);

  async function handleShare() {
    if (typeof navigator.share === "function") {
      try {
        await navigator.share({ title: "AI 管家任務完成通知", text });
      } catch {
        // 使用者取消分享選單不是錯誤，不用顯示任何提示。
      }
      return;
    }

    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      setToastText("已複製訊息，請貼到 LINE 傳給家人");
    }
  }

  return (
    <>
      <button
        type="button"
        onClick={() => void handleShare()}
        className="mt-3 inline-flex min-h-[44px] w-full items-center justify-center gap-2 rounded-2xl bg-[var(--color-primary)] px-4 py-2.5 text-base font-bold text-[var(--color-on-primary)]"
      >
        <ServiceIcon type="chat" size={18} />
        分享給家人
      </button>
      <Toast text={toastText} onHide={() => setToastText(null)} />
    </>
  );
}
```

- [ ] **Step 4: Create `TaskCardList.tsx`**

```tsx
// frontend/src/components/TaskCardList.tsx
import { GlassPanel } from "./GlassPanel";
import { ServiceIcon } from "./ServiceIcon";

interface TaskCard {
  service_id: string;
  service_name: string;
}

export function TaskCardList({ cards }: { cards: TaskCard[] }) {
  return (
    <div className="mt-3 flex flex-col gap-2.5">
      {cards.map((card) => (
        <GlassPanel
          key={card.service_id}
          className="flex items-center gap-3 rounded-2xl p-3.5 shadow-sm"
        >
          <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-[var(--color-primary-soft)] text-[var(--color-primary)]">
            <ServiceIcon type="chat" size={18} />
          </span>
          <span className="text-base font-bold text-[var(--color-foreground)]">{card.service_name}</span>
        </GlassPanel>
      ))}
    </div>
  );
}
```

- [ ] **Step 5: Run tests to verify they pass**

Run (from `frontend/`): `npm test -- ShareWithFamilyButton TaskCardList`
Expected: PASS (3 tests)

- [ ] **Step 6: Wire both into the chat flow**

In `frontend/src/types/request.ts`, extend `ChatEvent` and `ChatResponse`:

```typescript
export interface ChatEvent {
  role: "USER" | "ASSISTANT";
  content: string;
  redirectPath?: string;
  taskCards?: { service_id: string; service_name: string }[];
  shareText?: string;
}
```

```typescript
export interface ChatResponse {
  session_id: string;
  reply: string;
  service_id: string | null;
  service_name: string | null;
  collected_fields: Record<string, CollectedFieldValue>;
  missing_fields: string[];
  request_id: string | null;
  status: string;
  redirect_path: string | null;
  redirect_requires_confirmation: boolean;
  task_cards: { service_id: string; service_name: string }[] | null;
  share_text: string | null;
}
```

In `frontend/src/components/ChatMessage.tsx`, import and render the new pieces (add imports at the top, and render below `{event.redirectPath && (...)}` inside the message bubble, around line 39-47):

```tsx
import type { ChatEvent } from "../types/request";
import { Mascot } from "./Mascot";
import { ShareWithFamilyButton } from "./ShareWithFamilyButton";
import { TaskCardList } from "./TaskCardList";
```

```tsx
        {event.content}
        {event.taskCards && event.taskCards.length > 0 && <TaskCardList cards={event.taskCards} />}
        {event.shareText && <ShareWithFamilyButton text={event.shareText} />}
        {event.redirectPath && (
```

In `frontend/src/components/ButlerPanel.tsx`, thread the two new response fields into the pushed `ChatEvent` (replace the `setEvents` call inside `send`, around line 72-79):

```tsx
      setEvents((prev) => [
        ...prev,
        {
          role: "ASSISTANT",
          content: r.reply,
          redirectPath: showsRedirectButton ? r.redirect_path! : undefined,
          taskCards: r.task_cards ?? undefined,
          shareText: r.share_text ?? undefined,
        },
      ]);
```

- [ ] **Step 7: Run the full frontend test suite to check for regressions**

Run (from `frontend/`): `npm test`
Expected: All PASS

- [ ] **Step 8: Commit**

```bash
git add frontend/src/types/request.ts frontend/src/components/ChatMessage.tsx frontend/src/components/ButlerPanel.tsx frontend/src/components/ShareWithFamilyButton.tsx frontend/src/components/TaskCardList.tsx frontend/src/components/ShareWithFamilyButton.test.tsx frontend/src/components/TaskCardList.test.tsx
git commit -m "feat: render multi-task cards and family-share button in the chat panel"
```

---

## Task B1: Calendar aggregation endpoint (backend)

**Files:**
- Modify: `backend/app/services/store.py` — no changes needed, reuses existing `list_requests`
- Create: `backend/app/api/calendar.py`
- Modify: `backend/app/main.py:22-32` (router registration — this file registers every router with a plain `app.include_router(<module>.router)`, no prefix/tags; add `app.include_router(calendar.router)` in the same list, alongside the matching `from .api import calendar` import)
- Test: `backend/tests/test_calendar_api.py`

**Interfaces:**
- Consumes: `STORE.list_requests(actor_id: str) -> list[dict]` (existing, `backend/app/services/store.py:161`), each item's `form_data` dict (decrypted) may contain `preferred_date`, `reserved_date`, or other date-like keys.
- Produces: `GET /api/calendar` → `{"days": [{"date": "2026-08-02", "items": [{"request_id": ..., "service_name": ..., "status": ...}]}]}`, sorted by date ascending, only requests that have a resolvable date.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_calendar_api.py
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services import store as store_module


@pytest.fixture(autouse=True)
def isolated_store(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        test_store = store_module.MemoryStore(storage_path=Path(tmp) / "store.json")
        monkeypatch.setattr(store_module, "STORE", test_store)
        yield test_store


def _auth_headers(client: TestClient) -> dict:
    accounts = client.get("/api/auth/demo-accounts").json()["accounts"]
    token = accounts[0]["token"]
    return {"Authorization": f"Bearer {token}"}


def test_calendar_groups_requests_by_date(isolated_store):
    client = TestClient(app)
    headers = _auth_headers(client)
    # Directly seed two requests with different date-bearing fields, mimicking
    # what home_cleaning (preferred_date) and restaurant_reservation (reserved_date) store.
    isolated_store.save_request(
        "user-vincent",
        {
            "request_id": "REQ-1",
            "service_id": "home_cleaning",
            "service_name": "居家清潔",
            "status": "SUBMITTED",
            "form_data": {"preferred_date": "2026-08-02", "preferred_time_slot": "14:00"},
            "created_at": "2026-08-01T10:00:00+08:00",
        },
    )
    isolated_store.save_request(
        "user-vincent",
        {
            "request_id": "REQ-2",
            "service_id": "restaurant_reservation",
            "service_name": "餐廳訂位",
            "status": "CONFIRMED",
            "form_data": {"reserved_date": "2026-08-02", "time_slot": "LUNCH"},
            "created_at": "2026-08-01T10:05:00+08:00",
        },
    )

    response = client.get("/api/calendar", headers=headers)
    body = response.json()

    assert response.status_code == 200
    assert body["days"] == [
        {
            "date": "2026-08-02",
            "items": [
                {
                    "request_id": "REQ-1",
                    "service_name": "居家清潔",
                    "status": "SUBMITTED",
                    "status_label": "等待廠商確認",
                },
                {
                    "request_id": "REQ-2",
                    "service_name": "餐廳訂位",
                    "status": "CONFIRMED",
                    "status_label": "已確認",
                },
            ],
        }
    ]
```

`/api/auth/demo-accounts` returns accounts in `Settings.demo_users` insertion order (`backend/app/config.py:142-147`), so `accounts[0]` is always `demo-token-vincent` → `sub="user-vincent"`, matching the `"user-vincent"` actor id seeded above.

- [ ] **Step 2: Run test to verify it fails**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_calendar_api.py -v`
Expected: FAIL — `404 Not Found`, `/api/calendar` doesn't exist.

- [ ] **Step 3: Create `calendar.py`**

```python
# backend/app/api/calendar.py
"""Read-only calendar view: groups the actor's own service requests by date."""
from fastapi import APIRouter, Depends

from ..auth.cognito import CurrentUser, get_current_user
from ..services import statuses
from ..services.store import STORE

router = APIRouter()

_DATE_FIELDS = ("preferred_date", "reserved_date", "pickup_time_slot", "sender_date")


def _request_date(form_data: dict) -> str | None:
    for field_id in _DATE_FIELDS:
        value = form_data.get(field_id)
        if isinstance(value, str) and len(value) == 10 and value[4] == "-" and value[7] == "-":
            return value
    return None


@router.get("/api/calendar")
def get_calendar(user: CurrentUser = Depends(get_current_user)):
    requests = STORE.list_requests(user.sub)
    by_date: dict[str, list[dict]] = {}
    for request in requests:
        form_data = request.get("form_data") or {}
        request_date = _request_date(form_data)
        if not request_date:
            continue
        status = request.get("status", "")
        by_date.setdefault(request_date, []).append(
            {
                "request_id": request["request_id"],
                "service_name": request.get("service_name", ""),
                "status": status,
                "status_label": statuses.status_label(status),
            }
        )

    days = [
        {"date": request_date, "items": items}
        for request_date, items in sorted(by_date.items())
    ]
    return {"days": days}
```

- [ ] **Step 4: Register the router in `main.py`**

In `backend/app/main.py`, add `from .api import calendar` to the import block and `app.include_router(calendar.router)` to the `app.include_router(...)` list (`backend/app/main.py:22-32`), same plain style as every other router there (no prefix/tags).

- [ ] **Step 5: Run test to verify it passes**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_calendar_api.py -v`
Expected: PASS

- [ ] **Step 6: Run the full backend test suite to check for regressions**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests -v`
Expected: All PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/api/calendar.py backend/app/main.py backend/tests/test_calendar_api.py
git commit -m "feat: add GET /api/calendar aggregation endpoint"
```

---

## Task B2: Calendar page (frontend)

**Files:**
- Create: `frontend/src/api/calendar.ts`
- Create: `frontend/src/pages/CalendarPage.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/pages/HomePage.tsx`
- Test: `frontend/src/pages/CalendarPage.test.tsx`

**Interfaces:**
- Consumes: `GET /api/calendar` → `{"days": [{"date": string, "items": [{"request_id": string, "service_name": string, "status": string}]}]}` (Task B1).
- Produces: route `/calendar`.

- [ ] **Step 1: Write the failing test**

```tsx
// frontend/src/pages/CalendarPage.test.tsx
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { CalendarPage } from "./CalendarPage";
import * as calendarApi from "../api/calendar";

describe("CalendarPage", () => {
  it("renders requests grouped by date", async () => {
    vi.spyOn(calendarApi, "getCalendar").mockResolvedValue({
      days: [
        {
          date: "2026-08-02",
          items: [
            {
              request_id: "REQ-1",
              service_name: "居家清潔",
              status: "SUBMITTED",
              status_label: "等待廠商確認",
            },
          ],
        },
      ],
    });

    render(
      <MemoryRouter>
        <CalendarPage />
      </MemoryRouter>,
    );

    await waitFor(() => expect(screen.getByText("2026-08-02")).toBeInTheDocument());
    expect(screen.getByText("居家清潔")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run (from `frontend/`): `npm test -- CalendarPage`
Expected: FAIL — module doesn't exist.

- [ ] **Step 3: Create `api/calendar.ts`**

```typescript
// frontend/src/api/calendar.ts
import { api } from "./client";

export interface CalendarDay {
  date: string;
  items: { request_id: string; service_name: string; status: string; status_label: string }[];
}

export function getCalendar() {
  return api<{ days: CalendarDay[] }>("/api/calendar");
}
```

- [ ] **Step 4: Create `pages/CalendarPage.tsx`**

```tsx
// frontend/src/pages/CalendarPage.tsx
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getCalendar, type CalendarDay } from "../api/calendar";
import { BottomNav } from "../components/BottomNav";
import { ServiceIcon } from "../components/ServiceIcon";
import { StatusBadge } from "../components/StatusBadge";

export function CalendarPage() {
  const navigate = useNavigate();
  const [days, setDays] = useState<CalendarDay[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getCalendar()
      .then((r) => setDays(r.days))
      .finally(() => setLoading(false));
  }, []);

  return (
    <main className="mx-auto min-h-dvh max-w-md bg-[var(--color-canvas)] px-5 pb-32 pt-8">
      <div className="mb-6 flex items-center gap-3">
        <button
          type="button"
          onClick={() => navigate(-1)}
          aria-label="返回"
          className="flex h-11 w-11 items-center justify-center rounded-full bg-[var(--color-surface)] text-[var(--color-foreground)] shadow-sm"
        >
          <ServiceIcon type="back" size={20} />
        </button>
        <h1 className="text-2xl font-black text-[var(--color-foreground)]">行事曆</h1>
      </div>

      {loading && <p className="text-[var(--color-muted-foreground)]">載入中…</p>}
      {!loading && days.length === 0 && (
        <p className="text-[var(--color-muted-foreground)]">目前沒有已排定日期的服務。</p>
      )}

      <div className="flex flex-col gap-5">
        {days.map((day) => (
          <section key={day.date}>
            <h2 className="mb-2.5 text-base font-extrabold text-[var(--color-foreground)]">{day.date}</h2>
            <div className="flex flex-col gap-2.5">
              {day.items.map((item) => (
                <button
                  key={item.request_id}
                  type="button"
                  onClick={() => navigate(`/requests/${item.request_id}`)}
                  className="flex items-center justify-between rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4 text-left shadow-sm"
                >
                  <span className="font-bold text-[var(--color-foreground)]">{item.service_name}</span>
                  <StatusBadge status={item.status} label={item.status_label} />
                </button>
              ))}
            </div>
          </section>
        ))}
      </div>

      <BottomNav />
    </main>
  );
}
```

`StatusBadge` requires both `status` and `label` props (`frontend/src/components/StatusBadge.tsx:30-36`) — `status_label` from the API (Task B1) supplies `label` directly, matching how every other page using `StatusBadge` already sources its label from the backend.

- [ ] **Step 5: Run test to verify it passes**

Run (from `frontend/`): `npm test -- CalendarPage`
Expected: PASS

- [ ] **Step 6: Add the route and a HomePage entry point**

In `frontend/src/App.tsx`, add the import and route:

```tsx
import { CalendarPage } from "./pages/CalendarPage";
```

```tsx
        <Route path="/calendar" element={<Protected><CalendarPage /></Protected>} />
```

In `frontend/src/pages/HomePage.tsx`, add a compact two-button quick-link row right after the "服務捷徑列" `<section>` closes (after line 218, before the "「我的服務」／「客服中心」" section comment on line 220):

```tsx
        <section className="mt-6 grid grid-cols-2 gap-3">
          <button
            type="button"
            onClick={() => navigate("/calendar")}
            className="flex flex-col items-start gap-2 rounded-[22px] bg-[var(--color-surface)] p-4 text-left shadow-sm transition hover:-translate-y-0.5 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand"
          >
            <span className="flex h-10 w-10 items-center justify-center rounded-full bg-[var(--color-info-soft)] text-[var(--color-info)]">
              <ServiceIcon type="calendar" size={20} />
            </span>
            <span className="text-sm font-extrabold text-[var(--color-foreground)]">行事曆</span>
          </button>
          <button
            type="button"
            onClick={() => navigate("/scam-check")}
            className="flex flex-col items-start gap-2 rounded-[22px] bg-[var(--color-surface)] p-4 text-left shadow-sm transition hover:-translate-y-0.5 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand"
          >
            <span className="flex h-10 w-10 items-center justify-center rounded-full bg-[var(--color-danger-soft)] text-[var(--color-danger)]">
              <ServiceIcon type="warning" size={20} />
            </span>
            <span className="text-sm font-extrabold text-[var(--color-foreground)]">詐騙訊息辨識</span>
          </button>
        </section>
```

`--color-danger` / `--color-danger-soft` are already defined in `frontend/src/index.css` (light: `#B91C1C` / `#FEE2E2`; dark: `#F87171` / `rgba(248,113,113,0.16)`) and used the same way elsewhere (e.g. `ConfirmModal.tsx`, `StatusBadge.tsx`), so no new tokens are needed here.

- [ ] **Step 7: Run the full frontend test suite to check for regressions**

Run (from `frontend/`): `npm test`
Expected: All PASS

- [ ] **Step 8: Commit**

```bash
git add frontend/src/api/calendar.ts frontend/src/pages/CalendarPage.tsx frontend/src/pages/CalendarPage.test.tsx frontend/src/App.tsx frontend/src/pages/HomePage.tsx
git commit -m "feat: add calendar aggregation page and home-screen entry points"
```

---

## Task C1: Scam-message check (backend)

**Files:**
- Modify: `backend/app/agent/llm.py`
- Create: `backend/app/api/scam_check.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_llm_scam_check.py`, `backend/tests/test_scam_check_api.py`

**Interfaces:**
- Produces: `llm.check_scam_message(text: str) -> dict | None` returning `{"category": "投資詐騙"|"假冒親友"|"釣魚連結"|"正常訊息", "explanation": str}` or `None` when Bedrock is unavailable/fails.
- Produces: `POST /api/scam-check` with body `{"message": str}` → `{"category": str, "explanation": str}` on success, or `503` with a friendly error when Bedrock is unavailable.

- [ ] **Step 1: Write the failing `llm.py` test**

```python
# backend/tests/test_llm_scam_check.py
from unittest.mock import patch

from backend.app.agent import llm


def test_check_scam_message_returns_validated_category():
    fake_payload = {"category": "投資詐騙", "explanation": "這類訊息常以保證獲利吸引匯款，請勿點擊連結或提供帳戶資料。"}
    with patch("backend.app.agent.llm._converse_json", return_value=fake_payload):
        result = llm.check_scam_message("老師說穩賺不賠，加LINE了解")

    assert result == fake_payload


def test_check_scam_message_returns_none_when_category_invalid():
    with patch("backend.app.agent.llm._converse_json", return_value={"category": "不明分類", "explanation": "x"}):
        assert llm.check_scam_message("隨便的訊息") is None


def test_check_scam_message_returns_none_when_client_unavailable():
    with patch("backend.app.agent.llm._converse_json", return_value=None):
        assert llm.check_scam_message("隨便的訊息") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_llm_scam_check.py -v`
Expected: FAIL — `AttributeError: module 'llm' has no attribute 'check_scam_message'`

- [ ] **Step 3: Add `_SCAM_CHECK_SYSTEM` and `check_scam_message` to `llm.py`**

Add near the other system prompt constants in `backend/app/agent/llm.py` (after `_REPLY_SYSTEM`, around line 76):

```python
_SCAM_CHECK_SYSTEM = (
    "You help an elderly Traditional-Chinese-speaking user in Taiwan judge whether a message they "
    "received might be a scam. "
    "Classify it into exactly one category: \"投資詐騙\" (investment/fake-profit scams), "
    "\"假冒親友\" (impersonating a family member or friend asking for money/help), "
    "\"釣魚連結\" (phishing links or fake official notices), or \"正常訊息\" (a normal, safe message). "
    "Write a short, warm, plain-language explanation in Traditional Chinese a non-technical elderly "
    "reader can understand, including one concrete next step (e.g. do not click the link, call your "
    "child to confirm, do not transfer money). "
    "Return JSON only in the format {\"category\": string, \"explanation\": string}."
)


def check_scam_message(text: str) -> dict | None:
    payload = _converse_json(_SCAM_CHECK_SYSTEM, text, max_tokens=320)
    if not payload:
        return None
    category = payload.get("category")
    explanation = payload.get("explanation")
    valid_categories = {"投資詐騙", "假冒親友", "釣魚連結", "正常訊息"}
    if category not in valid_categories or not isinstance(explanation, str) or not explanation.strip():
        return None
    return {"category": category, "explanation": explanation.strip()}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_llm_scam_check.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Write the failing API test**

```python
# backend/tests/test_scam_check_api.py
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.app.main import app


def _auth_headers(client: TestClient) -> dict:
    accounts = client.get("/api/auth/demo-accounts").json()["accounts"]
    token = accounts[0]["token"]
    return {"Authorization": f"Bearer {token}"}


def test_scam_check_returns_classification():
    client = TestClient(app)
    headers = _auth_headers(client)
    with patch(
        "backend.app.api.scam_check.llm.check_scam_message",
        return_value={"category": "投資詐騙", "explanation": "請勿匯款，先跟家人確認。"},
    ):
        response = client.post("/api/scam-check", headers=headers, json={"message": "老師說穩賺不賠"})

    assert response.status_code == 200
    assert response.json() == {"category": "投資詐騙", "explanation": "請勿匯款，先跟家人確認。"}


def test_scam_check_returns_503_when_llm_unavailable():
    client = TestClient(app)
    headers = _auth_headers(client)
    with patch("backend.app.api.scam_check.llm.check_scam_message", return_value=None):
        response = client.post("/api/scam-check", headers=headers, json={"message": "隨便的訊息"})

    assert response.status_code == 503
```

- [ ] **Step 6: Run test to verify it fails**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_scam_check_api.py -v`
Expected: FAIL — `404 Not Found`

- [ ] **Step 7: Create `scam_check.py`**

```python
# backend/app/api/scam_check.py
"""Standalone scam-message classification, independent of the booking chat flow."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..agent import llm
from ..auth.cognito import CurrentUser, get_current_user

router = APIRouter()


class ScamCheckRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)


class ScamCheckResponse(BaseModel):
    category: str
    explanation: str


@router.post("/api/scam-check", response_model=ScamCheckResponse)
def scam_check(body: ScamCheckRequest, _user: CurrentUser = Depends(get_current_user)):
    result = llm.check_scam_message(body.message)
    if not result:
        raise HTTPException(
            status_code=503,
            detail={
                "success": False,
                "error": {"code": "SCAM_CHECK_UNAVAILABLE", "message": "目前無法判斷這則訊息，請稍後再試。"},
            },
        )
    return ScamCheckResponse(**result)
```

- [ ] **Step 8: Register the router in `main.py`**

Same pattern as Task B1 Step 4 — add `from .api import scam_check` to the import block and `app.include_router(scam_check.router)` to the list in `backend/app/main.py:22-32`.

- [ ] **Step 9: Run test to verify it passes**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_scam_check_api.py -v`
Expected: PASS

- [ ] **Step 10: Run the full backend test suite to check for regressions**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests -v`
Expected: All PASS

- [ ] **Step 11: Commit**

```bash
git add backend/app/agent/llm.py backend/app/api/scam_check.py backend/app/main.py backend/tests/test_llm_scam_check.py backend/tests/test_scam_check_api.py
git commit -m "feat: add scam-message check (llm classification + POST /api/scam-check)"
```

---

## Task C2: Scam-message check page (frontend)

**Files:**
- Create: `frontend/src/api/scamCheck.ts`
- Create: `frontend/src/pages/ScamCheckPage.tsx`
- Modify: `frontend/src/App.tsx`
- Test: `frontend/src/pages/ScamCheckPage.test.tsx`

**Interfaces:**
- Consumes: `POST /api/scam-check` (Task C1).
- Produces: route `/scam-check` (already linked from `HomePage.tsx` in Task B2 Step 6).

- [ ] **Step 1: Write the failing test**

```tsx
// frontend/src/pages/ScamCheckPage.test.tsx
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { ScamCheckPage } from "./ScamCheckPage";
import * as scamApi from "../api/scamCheck";

describe("ScamCheckPage", () => {
  it("submits the pasted message and shows the classification result", async () => {
    vi.spyOn(scamApi, "checkScamMessage").mockResolvedValue({
      category: "投資詐騙",
      explanation: "請勿匯款，先跟家人確認。",
    });

    render(
      <MemoryRouter>
        <ScamCheckPage />
      </MemoryRouter>,
    );

    fireEvent.change(screen.getByLabelText("貼上可疑訊息"), { target: { value: "老師說穩賺不賠" } });
    fireEvent.click(screen.getByRole("button", { name: "幫我看看" }));

    await waitFor(() => expect(screen.getByText("投資詐騙")).toBeInTheDocument());
    expect(screen.getByText("請勿匯款，先跟家人確認。")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run (from `frontend/`): `npm test -- ScamCheckPage`
Expected: FAIL — module doesn't exist.

- [ ] **Step 3: Create `api/scamCheck.ts`**

```typescript
// frontend/src/api/scamCheck.ts
import { api } from "./client";

export interface ScamCheckResult {
  category: string;
  explanation: string;
}

export function checkScamMessage(message: string) {
  return api<ScamCheckResult>("/api/scam-check", {
    method: "POST",
    body: JSON.stringify({ message }),
  });
}
```

- [ ] **Step 4: Create `pages/ScamCheckPage.tsx`**

```tsx
// frontend/src/pages/ScamCheckPage.tsx
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { checkScamMessage, type ScamCheckResult } from "../api/scamCheck";
import { BottomNav } from "../components/BottomNav";
import { ServiceIcon } from "../components/ServiceIcon";

export function ScamCheckPage() {
  const navigate = useNavigate();
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ScamCheckResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit() {
    if (!message.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const r = await checkScamMessage(message.trim());
      setResult(r);
    } catch {
      setError("目前無法判斷這則訊息，請稍後再試。");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto min-h-dvh max-w-md bg-[var(--color-canvas)] px-5 pb-32 pt-8">
      <div className="mb-6 flex items-center gap-3">
        <button
          type="button"
          onClick={() => navigate(-1)}
          aria-label="返回"
          className="flex h-11 w-11 items-center justify-center rounded-full bg-[var(--color-surface)] text-[var(--color-foreground)] shadow-sm"
        >
          <ServiceIcon type="back" size={20} />
        </button>
        <h1 className="text-2xl font-black text-[var(--color-foreground)]">詐騙訊息辨識</h1>
      </div>

      <p className="mb-4 text-[var(--color-muted-foreground)]">
        收到看起來怪怪的簡訊或訊息嗎？貼上來，我幫你看看安不安全。
      </p>

      <label htmlFor="scam-message-input" className="mb-2 block text-sm font-bold text-[var(--color-foreground)]">
        貼上可疑訊息
      </label>
      <textarea
        id="scam-message-input"
        aria-label="貼上可疑訊息"
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        rows={5}
        className="w-full rounded-2xl border-2 border-[var(--color-border)] bg-[var(--color-surface)] p-4 text-[var(--color-foreground)] outline-none focus:border-[var(--color-primary)]"
      />

      <button
        type="button"
        onClick={() => void handleSubmit()}
        disabled={loading || !message.trim()}
        className="mt-4 w-full rounded-2xl bg-[var(--color-primary)] py-4.5 text-lg font-bold text-[var(--color-on-primary)] disabled:opacity-40"
      >
        幫我看看
      </button>

      {error && <p className="mt-4 text-[var(--color-danger)]">{error}</p>}

      {result && (
        <div className="mt-6 rounded-3xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5 shadow-sm">
          <p className="text-lg font-black text-[var(--color-foreground)]">{result.category}</p>
          <p className="mt-2 leading-relaxed text-[var(--color-foreground)]">{result.explanation}</p>
        </div>
      )}

      <BottomNav />
    </main>
  );
}
```

Uses the existing `--color-danger` token, same as Task B2 — no new CSS variables needed.

- [ ] **Step 5: Run test to verify it passes**

Run (from `frontend/`): `npm test -- ScamCheckPage`
Expected: PASS

- [ ] **Step 6: Add the route**

In `frontend/src/App.tsx`:

```tsx
import { ScamCheckPage } from "./pages/ScamCheckPage";
```

```tsx
        <Route path="/scam-check" element={<Protected><ScamCheckPage /></Protected>} />
```

- [ ] **Step 7: Run the full frontend test suite to check for regressions**

Run (from `frontend/`): `npm test`
Expected: All PASS

- [ ] **Step 8: Commit**

```bash
git add frontend/src/api/scamCheck.ts frontend/src/pages/ScamCheckPage.tsx frontend/src/pages/ScamCheckPage.test.tsx frontend/src/App.tsx
git commit -m "feat: add scam-message check page"
```

---

## Task D1: Dialect-aware prompt tuning (prompt-only, no architecture change)

**Files:**
- Modify: `backend/app/agent/llm.py`

**Interfaces:** None — this task only edits string constants, no function signatures change.

This task has no automated test: it edits natural-language system prompts consumed by a live Bedrock model, which is not something a deterministic unit test can verify. Verification is manual, via Step 3 below.

- [ ] **Step 1: Add a shared glossary block**

Add a new constant near the top of `backend/app/agent/llm.py`, right after the existing system-prompt constants (after `_PAGE_HELP_SYSTEM`, around line 89):

```python
_DIALECT_GLOSSARY = (
    "The user may speak Taiwanese-Hokkien-influenced Mandarin (台語腔國語), transcribed by a "
    "Mandarin speech recognizer that may render it imperfectly. Recognize these common patterns: "
    "\"三牲\" (three-sacrifice ritual offering), \"透天厝\" (a multi-floor townhouse), "
    "\"逗陣\" (together/along), \"愛\" used to mean \"want/need\" (e.g. \"我愛買\" = \"我要買\"), "
    "\"甲意\" (like/prefer), \"呷飯\" (to eat a meal), \"歹勢\" (sorry/excuse me), "
    "and looser word order than standard Mandarin. Interpret the intended meaning, not the literal "
    "transcription."
)
```

- [ ] **Step 2: Append the glossary to the relevant system prompts**

Modify `_FIELD_SYSTEM`, `_SERVICE_SYSTEM`, `_TURN_SYSTEM`, and `_MULTI_TASK_SYSTEM` so each ends with `+ "\n\n" + _DIALECT_GLOSSARY` instead of being a bare string. For example, change:

```python
_FIELD_SYSTEM = (
    "You fill a JSON booking form for a Taiwanese home services assistant. "
    ...
    "Return JSON only in the format {\"fields\": { ... }}."
)
```

to:

```python
_FIELD_SYSTEM = (
    "You fill a JSON booking form for a Taiwanese home services assistant. "
    ...
    "Return JSON only in the format {\"fields\": { ... }}."
    "\n\n" + _DIALECT_GLOSSARY
)
```

Apply the same `"\n\n" + _DIALECT_GLOSSARY` suffix to `_SERVICE_SYSTEM`, `_TURN_SYSTEM`, and `_MULTI_TASK_SYSTEM` (the latter was added in Task A3 — if Task A3 already landed, this is a small follow-up edit to that same constant).

- [ ] **Step 3: Manual verification (only if AWS Bedrock credentials are configured and reachable)**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests -v` first to confirm no regressions (the glossary text doesn't change any mocked test behavior).

Then, only if you want to sanity-check the live model's behavior before the demo: start the backend (`uvicorn app.main:app --reload` from `backend/`) with real credentials in `.env`, and send a message like "阿伯愛買三牲跟水果" through `/api/chat` — confirm the reply treats "愛" as "要/need" and recognizes "三牲" instead of asking a confused clarifying question. This step is exploratory, not a pass/fail gate — skip it if there's no time before the demo.

- [ ] **Step 4: Commit**

```bash
git add backend/app/agent/llm.py
git commit -m "feat: add Taiwanese-dialect glossary to Bedrock system prompts"
```

---

## Self-Review Notes

- **Spec coverage:** 功能一 (multi-task orchestrator) → Tasks A1-A6. 功能二 (family share) → Task A6 (`ShareWithFamilyButton`, triggered by `share_text`). 功能三 (calendar) → Tasks B1-B2. 功能四 (scam check) → Tasks C1-C2. 功能五 (dialect prompts) → Task D1. All five spec sections have at least one task.
- **Known gap intentionally left out of this plan:** the spec's "任務之間沒有互相依賴" note and per-task failure handling (a failed task shouldn't block the rest) is implicitly satisfied by `_submit_and_continue_multi_task` only advancing the queue after a *successful* submit — a failed submit leaves the state exactly where the existing single-service error-handling already puts it (retry-in-place), which is consistent with every other service's existing failure behavior. No extra task needed.
- **Type consistency check:** `task_cards` is `list[dict] | None` end-to-end (Python dict → Pydantic `list[dict] | None` → TS `{service_id, service_name}[] | null` → `ChatEvent.taskCards?: {...}[]`) — verified consistent across Tasks A4/A5/A6. `share_text` is `str | None` end-to-end, same chain, also verified consistent.
- **Placeholder scan:** none found — the initial draft had two guessed spots (`main.py`'s router-registration pattern, and the danger/warning CSS variable name) that were resolved against the actual source during self-review and replaced with the real values (`app.include_router(...)` list at `backend/app/main.py:22-32`; `--color-danger`/`--color-danger-soft` from `frontend/src/index.css`). The initial draft also called `StatusBadge` with only a `status` prop; `StatusBadge` actually requires both `status` and `label` (`frontend/src/components/StatusBadge.tsx:30-36`), so Task B1's `/api/calendar` response and Task B2's `CalendarDay` type were both corrected to include `status_label` (sourced from the existing `app/services/statuses.py:status_label()` helper, the same one every other status-displaying page already uses) rather than inventing a second status-label mapping. The test fixtures across A5/B1/C1 originally assumed an `/api/auth/login` email+password flow that doesn't exist in this codebase — corrected to the real `/api/auth/demo-accounts` bearer-token flow used by every existing API test (e.g. `backend/tests/test_delivery_api.py`).
