# 美食外送 × 語音/聊天機器人整合 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 讓使用者可以在 ButlerPanel 聊天/語音介面用一次一問的對話完成美食外送下單（選店家→加點→地址→收件人→備註→確認摘要→送出），送出的訂單與現有 `DeliveryFlowPage` 精靈頁下的單完全同構，存進同一個 `STORE`、能在「我的服務」外送追蹤頁看到；順便在追蹤頁加一顆比照「餐廳訂位」案件明細頁的 Demo 模擬按鈕，讓外送狀態可以手動往前推進以便展示。

**Architecture:** 沿用「餐廳訂位」（`restaurant_reservation`）已驗證過的整合模式：`backend/app/services/catalog.py` 裡的 `food_delivery` schema 驅動聊天欄位收集，`backend/app/agent/agent.py` 新增專屬的購物車收集子流程（因為 `goods` 是會累積的清單，不能套用現有「一個欄位一個問題」的固定引擎）與 `_submit_delivery`，最終呼叫既有 `backend/app/services/delivery.py` 的 `create_delivery_order()`，讓聊天下單與精靈頁下單走同一條訂單建立路徑。店家/菜單資料從 `backend/app/api/delivery.py` 抽成獨立的 `delivery_catalog.py` 模組，讓 API 層與 Agent/NLU 層共用同一份資料。

**Tech Stack:** FastAPI + Python 3.12（後端）、pytest（後端測試，不含 hypothesis）、React + TypeScript + Vite（前端，本次不新增前端測試，沿用 `DeliveryFlowPage` 目前也沒有測試檔的現況）。

## Global Constraints

- 聊天下單不處理加購選項（甜度/冰量/加蛋等 `modifier_group`）的結構化選擇，只收一段自由文字備註（`note`），不影響金額計算。
- 聊天下單一律使用示範中心點座標 `lat 25.033 / lng 121.565`（與 `DeliveryFlowPage` 現有預設值相同），不做真實地理編碼。
- 點餐時一次只接受單一品項＋數量，要加點需再次詢問（不做一句話解析多品項）。
- 不修改 `lambda_tools/shared_lambda/catalog.py`（AWS Lambda 工具版本的服務目錄）；維持與 `restaurant_reservation` 相同的現況，本次僅針對 embedded/mock 模式（`USE_MOCK=true`）。
- 聊天機器人不回答「外送到哪了」之類的進度查詢，進度只透過精靈頁追蹤畫面查看。
- 不新增品項下架重新檢核邏輯（店家/菜單資料目前是寫死的靜態清單）。
- 所有新增/修改的 Python 檔案沿用現有專案的 type hint 風格（`from __future__ import annotations` + `dict | None`），不引入新的第三方依賴。

---

## File Structure

### Backend — new files

| File | Responsibility |
|---|---|
| `backend/app/services/delivery_catalog.py` | 外送店家/菜單靜態資料與查詢函式（`list_stores()` / `get_store(store_id)`） |
| `backend/tests/test_delivery_catalog.py` | 店家目錄測試 |
| `backend/tests/test_nlu_delivery.py` | `parse_delivery_store` / `parse_menu_item` 測試 |
| `backend/tests/test_catalog_delivery.py` | `food_delivery` schema（含新增 `note` 欄位、動態店家清單）測試 |
| `backend/tests/test_agent_delivery_submit.py` | 聊天下單端到端流程測試（比照 `test_agent_reservation_submit.py`） |
| `backend/tests/test_delivery_api.py` | 外送 Demo 模擬狀態端點測試（比照 `test_requests_simulate_reservation.py`） |

### Backend — modified files

| File | Change |
|---|---|
| `backend/app/api/delivery.py` | `DELIVERY_STORES` 改成從 `delivery_catalog` import；新增 `POST /api/delivery/orders/{request_id}/simulate` Demo 模擬端點 |
| `backend/app/agent/nlu.py` | 新增 `parse_delivery_store()` / `parse_menu_item()` |
| `backend/app/services/catalog.py` | `food_delivery` schema 的 `store_id.question` 改成動態列出店家名稱；新增 `note` 欄位 |
| `backend/app/agent/agent.py` | 新增購物車收集子流程（`_continue_delivery_collection` / `_handle_delivery_pending_reply`）、`_submit_delivery`、`SERVICE_DISPLAY_NAMES`/`FIELD_DISPLAY_NAMES` 補上 `food_delivery` 相關項目、`_build_summary_text` 特殊處理 `store_id`/`goods` 顯示、`_extract_fields` 排除 LLM 猜測 `store_id`/`goods` |

### Frontend — modified files

| File | Change |
|---|---|
| `frontend/src/api/delivery.ts` | 新增 `simulateDeliveryStatus()` |
| `frontend/src/pages/DeliveryFlowPage.tsx` | tracking 步驟新增「Demo：模擬下一個外送狀態」按鈕 |

---

## Task 1: 外送店家目錄拆成共用模組

**Files:**
- Create: `backend/app/services/delivery_catalog.py`
- Modify: `backend/app/api/delivery.py`
- Test: `backend/tests/test_delivery_catalog.py`

**Interfaces:**
- Produces: `DELIVERY_STORES: list[dict]`, `list_stores() -> list[dict]`, `get_store(store_id: str) -> dict | None`
- Consumed by: Task 2（`nlu.py`）、Task 4/5（`agent.py`）

- [ ] **Step 1: 寫失敗測試**

```python
# backend/tests/test_delivery_catalog.py
from backend.app.services import delivery_catalog


def test_list_stores_returns_three_seed_stores():
    stores = delivery_catalog.list_stores()
    assert len(stores) == 3
    assert {s["id"] for s in stores} == {"store-001", "store-002", "store-003"}


def test_get_store_found_includes_menu():
    store = delivery_catalog.get_store("store-001")
    assert store is not None
    assert store["name"] == "好味道便當"
    assert any(item["title"] == "招牌雞腿便當" for item in store["menu"])


def test_get_store_not_found_returns_none():
    assert delivery_catalog.get_store("does-not-exist") is None
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_delivery_catalog.py -v`
Expected: FAIL，`ModuleNotFoundError: No module named 'backend.app.services.delivery_catalog'`

- [ ] **Step 3: 建立 `delivery_catalog.py`**

把 `backend/app/api/delivery.py` 目前寫死的 `DELIVERY_STORES` 資料原封不動搬過來（品項與加購選項內容完全不變），並新增查詢函式：

```python
# backend/app/services/delivery_catalog.py
"""Static delivery store directory for the food delivery feature."""

DELIVERY_STORES: list[dict] = [
    {
        "id": "store-001",
        "name": "好味道便當",
        "address": "台北市大安區忠孝東路四段100號",
        "cuisine": "便當",
        "image": None,
        "url": "",
        "menu": [
            {"id": "item-001", "title": "招牌雞腿便當", "price": 110, "modifier_group": [
                {"name": "加購", "options": [{"label": "加蛋", "price": 15}, {"label": "加滷肉", "price": 20}]}
            ]},
            {"id": "item-002", "title": "排骨便當", "price": 100, "modifier_group": [
                {"name": "加購", "options": [{"label": "加蛋", "price": 15}]}
            ]},
            {"id": "item-003", "title": "素食便當", "price": 90, "modifier_group": []},
        ],
    },
    {
        "id": "store-002",
        "name": "鮮茶道",
        "address": "台北市信義區松仁路28號",
        "cuisine": "飲料",
        "image": None,
        "url": "",
        "menu": [
            {"id": "item-010", "title": "珍珠奶茶（大）", "price": 65, "modifier_group": [
                {"name": "甜度", "options": [{"label": "全糖", "price": 0}, {"label": "半糖", "price": 0}, {"label": "無糖", "price": 0}]},
                {"name": "冰量", "options": [{"label": "正常冰", "price": 0}, {"label": "少冰", "price": 0}, {"label": "去冰", "price": 0}]},
            ]},
            {"id": "item-011", "title": "四季春茶（大）", "price": 40, "modifier_group": [
                {"name": "甜度", "options": [{"label": "全糖", "price": 0}, {"label": "半糖", "price": 0}, {"label": "無糖", "price": 0}]},
            ]},
            {"id": "item-012", "title": "冬瓜檸檬", "price": 55, "modifier_group": []},
        ],
    },
    {
        "id": "store-003",
        "name": "義式小館",
        "address": "台北市中山區南京東路二段50號",
        "cuisine": "義式料理",
        "image": None,
        "url": "",
        "menu": [
            {"id": "item-020", "title": "奶油培根義大利麵", "price": 180, "modifier_group": [
                {"name": "加購", "options": [{"label": "升級套餐（含湯＋飲料）", "price": 69}]}
            ]},
            {"id": "item-021", "title": "瑪格麗特披薩", "price": 220, "modifier_group": []},
            {"id": "item-022", "title": "凱薩沙拉", "price": 120, "modifier_group": []},
        ],
    },
]


def list_stores() -> list[dict]:
    return DELIVERY_STORES


def get_store(store_id: str) -> dict | None:
    return next((s for s in DELIVERY_STORES if s["id"] == store_id), None)
```

- [ ] **Step 4: 執行測試確認通過**

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_delivery_catalog.py -v`
Expected: PASS（3 passed）

- [ ] **Step 5: 改用共用模組（`backend/app/api/delivery.py`）**

刪除 `backend/app/api/delivery.py` 裡原本的 `DELIVERY_STORES` 清單定義（第 14-66 行），改成 import；`list_delivery_stores` / `get_delivery_store` 改用 `delivery_catalog.list_stores()` / `delivery_catalog.get_store()`：

```python
"""Delivery ordering API endpoints."""
from fastapi import APIRouter, Depends, HTTPException

from ..auth.cognito import CurrentUser, get_current_user
from ..services import delivery, delivery_catalog

router = APIRouter()


def _raise_api_error(status_code: int, code: str, message: str):
    raise HTTPException(status_code=status_code, detail={"success": False, "error": {"code": code, "message": message}})


@router.get("/api/delivery/stores")
def list_delivery_stores(user: CurrentUser = Depends(get_current_user)):
    """列出可外送的店家（不含完整菜單）。"""
    stores = [
        {"id": s["id"], "name": s["name"], "address": s["address"], "cuisine": s["cuisine"], "image": s["image"]}
        for s in delivery_catalog.list_stores()
    ]
    return {"stores": stores}


@router.get("/api/delivery/stores/{store_id}")
def get_delivery_store(store_id: str, user: CurrentUser = Depends(get_current_user)):
    """取得單一店家含菜單。"""
    store = delivery_catalog.get_store(store_id)
    if not store:
        _raise_api_error(404, "STORE_NOT_FOUND", "找不到指定的外送店家。")
    return store
```

（`submit_delivery_order` / `get_delivery_order` / `cancel_delivery_order` / `delivery_webhook` 四支端點內容不變，保留在檔案原本位置；下面 import 行從 `from ..services import delivery` 改成 `from ..services import delivery, delivery_catalog`。）

- [ ] **Step 6: 重新執行測試確認沒有回歸**

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_delivery_catalog.py -v`
Expected: PASS（3 passed，確認搬移後模組本身沒壞；`api/delivery.py` 的行為由 Task 5 的 API 測試把關）

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/delivery_catalog.py backend/app/api/delivery.py backend/tests/test_delivery_catalog.py
git commit -m "refactor: extract delivery store catalog into shared module"
```

---

## Task 2: NLU 新增店家與品項解析函式

**Files:**
- Modify: `backend/app/agent/nlu.py`
- Test: `backend/tests/test_nlu_delivery.py`

**Interfaces:**
- Consumes: `delivery_catalog.list_stores()` / `delivery_catalog.get_store()`（Task 1）、既有 `parse_quantity()`
- Produces: `parse_delivery_store(text: str) -> str | None`、`parse_menu_item(text: str, store_id: str) -> dict | None`（回傳 `{"id", "title", "price", "quantity"}` 或 `None`）
- Consumed by: Task 4（`agent.py`）

- [ ] **Step 1: 寫失敗測試**

```python
# backend/tests/test_nlu_delivery.py
from backend.app.agent import nlu


def test_parse_delivery_store_matches_full_name():
    assert nlu.parse_delivery_store("我想跟好味道便當訂餐") == "store-001"


def test_parse_delivery_store_matches_drink_shop():
    assert nlu.parse_delivery_store("鮮茶道有開嗎") == "store-002"


def test_parse_delivery_store_returns_none_when_no_match():
    assert nlu.parse_delivery_store("我想吃拉麵") is None


def test_parse_menu_item_matches_title_with_explicit_quantity():
    item = nlu.parse_menu_item("我要兩個招牌雞腿便當", "store-001")
    assert item == {"id": "item-001", "title": "招牌雞腿便當", "price": 110, "quantity": 2}


def test_parse_menu_item_defaults_quantity_to_one():
    item = nlu.parse_menu_item("排骨便當", "store-001")
    assert item == {"id": "item-002", "title": "排骨便當", "price": 100, "quantity": 1}


def test_parse_menu_item_returns_none_for_unknown_item():
    assert nlu.parse_menu_item("我要牛肉麵", "store-001") is None


def test_parse_menu_item_returns_none_for_unknown_store():
    assert nlu.parse_menu_item("排骨便當", "does-not-exist") is None
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_nlu_delivery.py -v`
Expected: FAIL，`AttributeError: module 'backend.app.agent.nlu' has no attribute 'parse_delivery_store'`

- [ ] **Step 3: 實作**

在 `backend/app/agent/nlu.py` 頂部 import 區塊（緊接 `from ..services.restaurant_catalog import RESTAURANTS` 之後）新增：

```python
from ..services import delivery_catalog
```

在 `parse_restaurant()` 函式之後新增兩個函式：

```python
def parse_delivery_store(text: str) -> str | None:
    """依店家名稱比對文字，回傳 store_id。"""
    for store in delivery_catalog.list_stores():
        if store["name"] in text:
            return store["id"]
    return None


def parse_menu_item(text: str, store_id: str) -> dict | None:
    """依指定店家菜單比對品項名稱，並擷取數量（找不到數量時預設 1 份）。"""
    store = delivery_catalog.get_store(store_id)
    if not store:
        return None
    for item in store["menu"]:
        if item["title"] in text:
            quantity = parse_quantity(text, unit_chars="份個杯碗") or 1
            return {
                "id": item["id"],
                "title": item["title"],
                "price": item["price"],
                "quantity": quantity,
            }
    return None
```

- [ ] **Step 4: 執行測試確認通過**

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_nlu_delivery.py -v`
Expected: PASS（7 passed）

- [ ] **Step 5: Commit**

```bash
git add backend/app/agent/nlu.py backend/tests/test_nlu_delivery.py
git commit -m "feat: add delivery store and menu item NLU parsers"
```

---

## Task 3: `food_delivery` schema 補上 `note` 欄位與動態店家清單

**Files:**
- Modify: `backend/app/services/catalog.py`
- Test: `backend/tests/test_catalog_delivery.py`

**Interfaces:**
- Consumes: `delivery_catalog.list_stores()`（Task 1）
- Produces: `catalog.get_service_schema("food_delivery")["fields"]` 新增 `note` 欄位；`store_id` 欄位的 `question` 動態列出店家名稱
- Consumed by: Task 4（`agent.py` 的欄位收集會依這份 schema 驅動）

- [ ] **Step 1: 寫失敗測試**

```python
# backend/tests/test_catalog_delivery.py
from backend.app.services import catalog


def test_food_delivery_schema_includes_note_field():
    schema = catalog.get_service_schema("food_delivery")
    field_ids = [f["id"] for f in schema["fields"]]
    assert field_ids == ["address", "store_id", "goods", "contact_name", "note"]


def test_food_delivery_store_question_lists_store_names():
    schema = catalog.get_service_schema("food_delivery")
    store_field = next(f for f in schema["fields"] if f["id"] == "store_id")
    assert "好味道便當" in store_field["question"]
    assert "鮮茶道" in store_field["question"]
    assert "義式小館" in store_field["question"]
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_catalog_delivery.py -v`
Expected: FAIL，`AssertionError`（目前 `field_ids` 沒有 `"note"`，`store_field["question"]` 是固定文字「請選擇想要外送的店家。」不含店名）

- [ ] **Step 3: 實作**

在 `backend/app/services/catalog.py` 頂部 import 新增：

```python
from .delivery_catalog import list_stores
```

把 `food_delivery` 服務的 `schema.fields` 區塊（原本第 286-315 行）換成：

```python
        "schema": {
            "fields": [
                {
                    "id": "address",
                    "label": "外送地址",
                    "type": "address",
                    "required": True,
                    "question": "請提供外送地址（含樓層備註）。",
                },
                {
                    "id": "store_id",
                    "label": "選擇店家",
                    "type": "select",
                    "required": True,
                    "question": "請問想點哪一間店家？目前提供："
                    + "、".join(s["name"] for s in list_stores())
                    + "。",
                },
                {
                    "id": "goods",
                    "label": "餐點品項",
                    "type": "cart",
                    "required": True,
                    "question": "請選擇要訂購的餐點與數量。",
                },
                {
                    "id": "contact_name",
                    "label": "收件人姓名",
                    "type": "text",
                    "required": True,
                    "question": "請填寫收件人姓名。",
                },
                {
                    "id": "note",
                    "label": "備註需求",
                    "type": "text",
                    "required": True,
                    "question": "有沒有其他需求呢？例如全糖去冰、不辣等，沒有的話可以直接說「沒有」。",
                },
            ],
        },
```

- [ ] **Step 4: 執行測試確認通過**

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_catalog_delivery.py -v`
Expected: PASS（2 passed）

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/catalog.py backend/tests/test_catalog_delivery.py
git commit -m "feat: add note field and dynamic store list to food_delivery schema"
```

---

## Task 4: Agent 購物車收集子流程

**Files:**
- Modify: `backend/app/agent/agent.py`
- Test: `backend/tests/test_agent_delivery_submit.py`（本任務先寫涵蓋「收集」階段的測試；Task 5 會在同一個檔案補上「送出」階段的測試）

**Interfaces:**
- Consumes: `nlu.parse_delivery_store()` / `nlu.parse_menu_item()`（Task 2）、`delivery_catalog.list_stores()` / `get_store()`（Task 1）
- Produces: `state["pending_delivery_field"]`（`"store" | "item" | "more_items" | None`）、`_continue_delivery_collection(actor_id, state, latest_user_message="", events=None) -> dict`、`_handle_delivery_pending_reply(actor_id, state, text, events) -> dict`
- Consumed by: Task 5（`_submit_delivery` 會讀取 `state["collected_fields"]["goods"]` / `["store_id"]`）

**背景（為什麼需要這個任務）：** `goods` 是使用者一項一項加點累積出來的清單，現有的「一個 `field_id` 對一個問題」引擎（`_continue_collection` 目前的實作）沒辦法處理「同一欄位要反覆詢問多次」的情境，所以需要一個獨立的子流程，在 `store_id`／`goods` 都收集完成之後，才交還給既有引擎繼續問 `address`／`contact_name`／`note`。

- [ ] **Step 1: 寫失敗測試**

```python
# backend/tests/test_agent_delivery_submit.py
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from backend.app.agent import agent, nlu
from backend.app.services import delivery, store as store_module


@pytest.fixture(autouse=True)
def isolated_store(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        test_store = store_module.MemoryStore(storage_path=Path(tmp) / "store.json")
        monkeypatch.setattr(store_module, "STORE", test_store)
        monkeypatch.setattr(delivery, "STORE", test_store)
        yield test_store


def _run_turn(state, message, actor_id="user-1", session_id="sess-1"):
    return agent.handle_message(actor_id, session_id, state, message)


def _fake_extract_fields(*, message, fields, collected_fields, **_kwargs):
    """Deterministic stand-in for the live Bedrock-backed llm.extract_fields
    (unreachable in this environment — same rationale as
    test_agent_reservation_submit.py). store_id/goods never flow through this
    path: agent.py excludes them via _LLM_EXCLUDED_FIELDS and collects them
    through the dedicated cart-building loop instead, so this fake only needs
    to cover the plain text fields: address, contact_name, note.
    """
    found = {}
    field_ids = {field["id"] for field in fields}

    if "address" in field_ids and "address" not in collected_fields:
        parsed = nlu.parse_address(message)
        if parsed:
            found["address"] = parsed

    if "contact_name" in field_ids and "contact_name" not in collected_fields:
        stripped = message.strip()
        if 2 <= len(stripped) <= 4 and all("一" <= ch <= "鿿" for ch in stripped):
            found["contact_name"] = stripped

    if "note" in field_ids and "note" not in collected_fields:
        found["note"] = message.strip()

    return found


def test_delivery_chat_flow_collects_store_then_cart_then_hands_off():
    state = agent.new_state()

    with patch("backend.app.agent.agent._available_services", return_value=[
        {"id": "food_delivery", "name": "美食外送", "description": "附近店家美食外送到府服務"},
    ]), patch("backend.app.agent.agent.llm.extract_fields", side_effect=_fake_extract_fields):
        result = _run_turn(state, "我想叫外送")
        state = result["state"]
        assert state["service_id"] == "food_delivery"
        assert state["pending_delivery_field"] == "store"

        result = _run_turn(state, "好味道便當")
        state = result["state"]
        assert state["collected_fields"]["store_id"] == "store-001"
        assert state["pending_delivery_field"] == "item"

        result = _run_turn(state, "招牌雞腿便當一個")
        state = result["state"]
        assert state["collected_fields"]["goods"] == [
            {"id": "item-001", "title": "招牌雞腿便當", "price": 110, "quantity": 1}
        ]
        assert state["pending_delivery_field"] == "more_items"

        result = _run_turn(state, "不用了")
        state = result["state"]

    assert state["pending_delivery_field"] is None
    assert "store_id" not in state["missing_fields"]
    assert "goods" not in state["missing_fields"]


def test_delivery_chat_flow_reprompts_on_unknown_store_name():
    state = agent.new_state()

    with patch("backend.app.agent.agent._available_services", return_value=[
        {"id": "food_delivery", "name": "美食外送", "description": "附近店家美食外送到府服務"},
    ]), patch("backend.app.agent.agent.llm.extract_fields", side_effect=_fake_extract_fields):
        result = _run_turn(state, "我想叫外送")
        state = result["state"]
        result = _run_turn(state, "麥當勞")
        state = result["state"]

    assert state["pending_delivery_field"] == "store"
    assert "store_id" not in state["collected_fields"]


def test_delivery_chat_flow_reprompts_on_unknown_menu_item():
    state = agent.new_state()

    with patch("backend.app.agent.agent._available_services", return_value=[
        {"id": "food_delivery", "name": "美食外送", "description": "附近店家美食外送到府服務"},
    ]), patch("backend.app.agent.agent.llm.extract_fields", side_effect=_fake_extract_fields):
        result = _run_turn(state, "我想叫外送")
        state = result["state"]
        result = _run_turn(state, "好味道便當")
        state = result["state"]
        result = _run_turn(state, "我要牛肉麵")
        state = result["state"]

    assert state["pending_delivery_field"] == "item"
    assert state["collected_fields"].get("goods") in (None, [])
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_agent_delivery_submit.py -v`
Expected: FAIL——`state["pending_delivery_field"]` 這個 key 不存在（`new_state()` 還沒定義），或第一則訊息後直接被當成一般文字欄位收集卡住

- [ ] **Step 3: 實作**

在 `backend/app/agent/agent.py` 的 import 區塊，把：

```python
from ..services import reservation
```

改成：

```python
from ..services import delivery, delivery_catalog, reservation
```

在 `SERVICE_DISPLAY_NAMES` 裡新增一行：

```python
    "food_delivery": "美食外送",
```

在 `FIELD_DISPLAY_NAMES` 裡新增：

```python
    "store_id": "店家",
    "goods": "餐點",
    "note": "備註需求",
```

在檔案裡任一模組層級位置（建議放在 `RULE_SERVICE_KEYWORDS` 定義之後）新增：

```python
# goods/store_id 一律透過下方的購物車收集子流程取得，不透過 LLM 猜測
# （store_id 沒有靜態 options 所以本來就猜不中；goods 是清單型別，讓 LLM
#  猜測容易產生格式不符的字串，直接排除避免污染 collected_fields）。
_LLM_EXCLUDED_FIELDS = {"store_id", "goods"}
```

把 `_extract_fields()` 裡的 `for field in fields:` 迴圈開頭加一行排除：

```python
    for field in fields:
        field_id = field["id"]
        if field_id in _LLM_EXCLUDED_FIELDS:
            continue
        if field_id in state["collected_fields"] or field_id not in llm_fields:
            continue
```

在 `new_state()` 回傳的 dict 裡新增一個 key（放在 `"pending_pref_question": None,` 之後）：

```python
        "pending_delivery_field": None,
```

修改 `_build_summary_text()`，讓 `store_id`／`goods` 顯示成可讀文字而不是原始資料結構：

```python
def _build_summary_text(state: dict) -> str:
    fields = state["service_schema"]["fields"]
    lines = ["請確認以下申請內容：", f"服務：{_display_service_name(state['service_id'], state['service_name'])}"]
    for field in fields:
        field_id = field["id"]
        if field_id not in state["collected_fields"]:
            continue
        if field_id == "store_id":
            store = delivery_catalog.get_store(state["collected_fields"]["store_id"])
            lines.append(f"店家：{store['name'] if store else state['collected_fields']['store_id']}")
            continue
        if field_id == "goods":
            lines.append("餐點：")
            for item in state["collected_fields"]["goods"]:
                lines.append(f"　{item['title']} x{item['quantity']}")
            continue
        lines.append(_display_value(field_id, state["collected_fields"][field_id], fields))
    lines.append("")
    lines.append("如果資料正確請直接回覆「確認送出」，如果要修改請直接告訴我要改哪一項。")
    return "\n".join(lines)
```

把既有的 `_continue_collection()` 函式整個改名為 `_continue_generic_collection()`（函式簽名與內部邏輯完全不變，只改名字），然後在原本 `_continue_collection` 的位置新增一個 dispatcher 與外送專屬的收集函式：

```python
def _continue_collection(actor_id: str, state: dict, latest_user_message: str = "", events: list[dict] | None = None) -> dict:
    if state.get("service_id") == "food_delivery":
        return _continue_delivery_collection(actor_id, state, latest_user_message, events)
    return _continue_generic_collection(actor_id, state, latest_user_message, events)


def _continue_delivery_collection(actor_id: str, state: dict, latest_user_message: str = "", events: list[dict] | None = None) -> dict:
    collected = state["collected_fields"]

    if "store_id" not in collected:
        state["pending_delivery_field"] = "store"
        names = "、".join(s["name"] for s in delivery_catalog.list_stores())
        return _reply(state, f"請問想點哪一間店家？目前提供：{names}。")

    if not collected.get("goods"):
        state["pending_delivery_field"] = "item"
        return _reply(state, "想點餐點裡的哪一項？可以先說一項，要加點我再問。")

    _recompute_missing(state)
    return _continue_generic_collection(actor_id, state, latest_user_message, events)


def _handle_delivery_pending_reply(actor_id: str, state: dict, text: str, events: list[dict] | None) -> dict:
    pending = state["pending_delivery_field"]

    if pending == "store":
        store_id = nlu.parse_delivery_store(text)
        if not store_id:
            names = "、".join(s["name"] for s in delivery_catalog.list_stores())
            return _reply(state, f"不好意思，目前沒有找到這間店家，請問想點：{names} 哪一間呢？")
        state["collected_fields"]["store_id"] = store_id
        state["pending_delivery_field"] = None
        return _continue_delivery_collection(actor_id, state, text, events)

    if pending == "item":
        item = nlu.parse_menu_item(text, state["collected_fields"]["store_id"])
        if not item:
            return _reply(state, "這個品項目前菜單上沒有找到，要不要換一個？")
        state["collected_fields"].setdefault("goods", []).append(item)
        state["pending_delivery_field"] = "more_items"
        return _reply(state, f"已加入 {item['title']} x{item['quantity']}。還要加點別的嗎？")

    if pending == "more_items":
        verdict = _judge_reply("還要加點別的嗎？", text)
        if verdict == "yes":
            state["pending_delivery_field"] = "item"
            return _reply(state, "想點餐點裡的哪一項？")
        state["pending_delivery_field"] = None
        _recompute_missing(state)
        return _continue_delivery_collection(actor_id, state, text, events)

    state["pending_delivery_field"] = None
    return _continue_delivery_collection(actor_id, state, text, events)
```

在 `handle_message()` 裡，緊接在 `if state.get("request_id"):` 這一整塊處理完之後、`if state.get("pending_pref_field"):` 之前，插入：

```python
    if state.get("pending_delivery_field"):
        return _handle_delivery_pending_reply(actor_id, state, text, events)
```

- [ ] **Step 4: 執行測試確認通過**

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_agent_delivery_submit.py -v`
Expected: PASS（3 passed）

- [ ] **Step 5: 執行既有 Agent 測試確認沒有回歸**

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_agent_regressions.py backend/tests/test_agent_reservation_submit.py -v`
Expected: PASS（全部通過——確認 `_continue_collection` 改名/新增 dispatcher 沒有影響其他服務的既有流程）

- [ ] **Step 6: Commit**

```bash
git add backend/app/agent/agent.py backend/tests/test_agent_delivery_submit.py
git commit -m "feat: add delivery cart collection sub-flow to chat agent"
```

---

## Task 5: Agent 送出外送訂單

**Files:**
- Modify: `backend/app/agent/agent.py`
- Test: `backend/tests/test_agent_delivery_submit.py`（延續 Task 4 的檔案，新增送出階段的測試）

**Interfaces:**
- Consumes: `delivery.create_delivery_order(actor_id, payload) -> dict`（既有函式，不變）、`delivery_catalog.get_store()`（Task 1）
- Produces: `_submit_delivery(actor_id: str, state: dict, latest_user_message: str) -> dict`
- 供 `_submit()` 呼叫

- [ ] **Step 1: 寫失敗測試（追加進同一個測試檔）**

在 `backend/tests/test_agent_delivery_submit.py` 檔案最後追加：

```python
def test_delivery_chat_flow_creates_order_end_to_end():
    state = agent.new_state()

    with patch("backend.app.agent.agent._available_services", return_value=[
        {"id": "food_delivery", "name": "美食外送", "description": "附近店家美食外送到府服務"},
    ]), patch("backend.app.agent.agent.llm.extract_fields", side_effect=_fake_extract_fields):
        result = _run_turn(state, "我想叫外送")
        state = result["state"]
        result = _run_turn(state, "好味道便當")
        state = result["state"]
        result = _run_turn(state, "招牌雞腿便當一個")
        state = result["state"]
        result = _run_turn(state, "不用了")
        state = result["state"]
        result = _run_turn(state, "台北市大安區忠孝東路四段100號")
        state = result["state"]
        result = _run_turn(state, "王小明")
        state = result["state"]
        result = _run_turn(state, "不辣")
        state = result["state"]
        assert state["awaiting_confirmation"] is True

        result = _run_turn(state, "確認送出")
        state = result["state"]

    assert state["request_id"] is not None
    order = delivery.get_delivery_order("user-1", state["request_id"])
    assert order["order_items"]["store"]["id"] == "store-001"
    assert order["order_items"]["goods"] == [
        {"id": "item-001", "title": "招牌雞腿便當", "price": 110, "quantity": 1}
    ]
    assert order["order_type"] == "06"
    assert order["order_status"] == "01"


def test_delivery_chat_flow_reports_error_without_crashing_when_cart_empty():
    state = agent.new_state()
    state["service_id"] = "food_delivery"
    state["service_name"] = "美食外送"
    state["service_schema"] = {"fields": [
        {"id": "store_id", "type": "select", "required": True},
        {"id": "goods", "type": "cart", "required": True},
    ]}
    state["collected_fields"] = {"store_id": "store-001", "goods": []}
    state["missing_fields"] = []
    state["awaiting_confirmation"] = True

    result = _run_turn(state, "確認送出")

    assert result["state"]["request_id"] is None
    assert "reply" in result
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_agent_delivery_submit.py -v`
Expected: FAIL——`_submit()` 目前對 `food_delivery` 會走一般 `tools.call("submit_service_request", ...)` 路徑，存出來的案件沒有 `order_items`/`order_type` 等外送專屬欄位，`delivery.get_delivery_order()` 找不到對應資料或欄位對不上

- [ ] **Step 3: 實作**

在 `_submit()` 函式裡，找到：

```python
    if state["service_id"] == "restaurant_reservation":
        return _submit_reservation(actor_id, state, latest_user_message)
```

在它之後新增：

```python
    if state["service_id"] == "food_delivery":
        return _submit_delivery(actor_id, state, latest_user_message)
```

在 `_submit_reservation()` 函式之後新增 `_submit_delivery()`：

```python
def _submit_delivery(actor_id: str, state: dict, latest_user_message: str) -> dict:
    collected = state["collected_fields"]
    store_id = collected.get("store_id")
    store = delivery_catalog.get_store(store_id) or {}
    payload = {
        "address": {
            "lat": 25.033,
            "lng": 121.565,
            "area": "",
            "city": "台北市",
            "street": collected.get("address", ""),
            "remark": "",
            "contact_name": collected.get("contact_name", ""),
        },
        "goods": collected.get("goods", []),
        "store_id": store_id,
        "store_name": store.get("name", ""),
        "store_address": store.get("address", ""),
        "note": collected.get("note", ""),
        "shipping_fee": 60,
    }
    result = delivery.create_delivery_order(actor_id, payload)

    if not result.get("success"):
        message = result.get("error", {}).get("message", "外送訂單建立失敗")
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
    state["status"] = "SUBMITTED"
    state["awaiting_confirmation"] = False
    return _reply(
        state,
        _model_reply(
            actor_id,
            state,
            "submit_success",
            latest_user_message=latest_user_message,
            request_id=result["request_id"],
        ),
    )
```

- [ ] **Step 4: 執行測試確認通過**

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_agent_delivery_submit.py -v`
Expected: PASS（5 passed）

- [ ] **Step 5: 執行完整後端測試套件確認沒有回歸**

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests -v`
Expected: 全部通過（沒有既有測試因為 `_continue_collection` 改名或 `_extract_fields` 排除清單而壞掉）

- [ ] **Step 6: Commit**

```bash
git add backend/app/agent/agent.py backend/tests/test_agent_delivery_submit.py
git commit -m "feat: submit delivery orders created through the chat agent"
```

---

## Task 6: 外送進度 Demo 模擬端點

**Files:**
- Modify: `backend/app/api/delivery.py`
- Test: `backend/tests/test_delivery_api.py`

**Interfaces:**
- Consumes: `delivery.update_delivery_status_from_vendor(actor_id, request_id, vendor_status, delivery_info) -> dict`（既有函式，不變）
- Produces: `POST /api/delivery/orders/{request_id}/simulate`（body: `{"vendor_status": int, "delivery": {...} | None}`，回傳 `{"success", "request_id", "order_status", "order_status_label"}`）

- [ ] **Step 1: 寫失敗測試**

```python
# backend/tests/test_delivery_api.py
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services import delivery, store as store_module


@pytest.fixture(autouse=True)
def isolated_store(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        test_store = store_module.MemoryStore(storage_path=Path(tmp) / "store.json")
        monkeypatch.setattr(store_module, "STORE", test_store)
        monkeypatch.setattr(delivery, "STORE", test_store)
        yield test_store


def _auth_headers(client: TestClient) -> dict:
    accounts = client.get("/api/auth/demo-accounts").json()["accounts"]
    token = accounts[0]["token"]
    return {"Authorization": f"Bearer {token}"}


def _create_order(client: TestClient, headers: dict) -> dict:
    return client.post(
        "/api/delivery/submit",
        json={
            "address": {
                "lat": 25.033, "lng": 121.565,
                "city": "台北市", "area": "大安區", "street": "忠孝東路四段100號",
                "remark": "", "contact_name": "王小明",
            },
            "goods": [{"id": "item-001", "title": "招牌雞腿便當", "price": 110, "quantity": 1}],
            "store_id": "store-001",
            "store_name": "好味道便當",
            "store_address": "台北市大安區忠孝東路四段100號",
        },
        headers=headers,
    ).json()


def test_simulate_delivery_status_advances_order_status_and_driver_info():
    client = TestClient(app)
    headers = _auth_headers(client)
    created = _create_order(client, headers)
    assert created["order_status"] == "01"

    response = client.post(
        f"/api/delivery/orders/{created['request_id']}/simulate",
        json={
            "vendor_status": 1,
            "delivery": {"driver_name": "示範外送員", "driver_phone": "0912345678", "eta_minutes": 20},
        },
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["order_status"] == "02"

    detail = client.get(f"/api/delivery/orders/{created['request_id']}", headers=headers).json()
    assert detail["order_status"] == "02"
    assert detail["vendor_data"]["delivery"]["driver_name"] == "示範外送員"


def test_simulate_delivery_status_returns_404_for_missing_order():
    client = TestClient(app)
    headers = _auth_headers(client)

    response = client.post(
        "/api/delivery/orders/REQ-DOES-NOT-EXIST/simulate",
        json={"vendor_status": 1},
        headers=headers,
    )
    assert response.status_code == 404
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_delivery_api.py -v`
Expected: FAIL，`404 Not Found`（路由尚未註冊，回應內容沒有 `order_status` 這個 key）

- [ ] **Step 3: 實作**

在 `backend/app/api/delivery.py` 的 `cancel_delivery_order` 端點之後、`delivery_webhook` 之前，新增：

```python
@router.post("/api/delivery/orders/{request_id}/simulate")
def simulate_delivery_status(
    request_id: str,
    body: dict,
    user: CurrentUser = Depends(get_current_user),
):
    """Demo 用：手動推進外送訂單的第三方狀態碼，內部走的路徑與真實 webhook 完全相同。"""
    vendor_status = body.get("vendor_status")
    if vendor_status is None:
        _raise_api_error(400, "INVALID_FORM_DATA", "缺少 vendor_status。")
    delivery_info = body.get("delivery")
    result = delivery.update_delivery_status_from_vendor(user.sub, request_id, int(vendor_status), delivery_info)
    if not result.get("success"):
        error = result.get("error", {})
        status_code = 404 if error.get("code") == "REQUEST_NOT_FOUND" else 400
        _raise_api_error(status_code, error.get("code", "UPDATE_FAILED"), error.get("message", "狀態更新失敗"))
    return result
```

- [ ] **Step 4: 執行測試確認通過**

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_delivery_api.py -v`
Expected: PASS（2 passed）

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/delivery.py backend/tests/test_delivery_api.py
git commit -m "feat: add demo endpoint to manually advance delivery order status"
```

---

## Task 7: 前端追蹤頁加 Demo 模擬按鈕

**Files:**
- Modify: `frontend/src/api/delivery.ts`
- Modify: `frontend/src/pages/DeliveryFlowPage.tsx`

**Interfaces:**
- Consumes: `POST /api/delivery/orders/{request_id}/simulate`（Task 6）
- Produces: `simulateDeliveryStatus(requestId: string, vendorStatus: number, driver?: {...}) -> Promise<{success, order_status, order_status_label}>`

- [ ] **Step 1: 新增 API 函式**

在 `frontend/src/api/delivery.ts` 檔案最後追加：

```ts
export function simulateDeliveryStatus(
  requestId: string,
  vendorStatus: number,
  driver?: { driver_name: string; driver_phone: string; eta_minutes: number },
): Promise<{ success: boolean; order_status: string; order_status_label: string }> {
  return api(`/api/delivery/orders/${requestId}/simulate`, {
    method: "POST",
    body: JSON.stringify({ vendor_status: vendorStatus, delivery: driver }),
  });
}
```

- [ ] **Step 2: `DeliveryFlowPage.tsx` import 新函式**

把檔案頂部的：

```ts
import {
  getDeliveryOrder,
  getDeliveryStore,
  listDeliveryStores,
  submitDeliveryOrder,
} from "../api/delivery";
```

改成：

```ts
import {
  getDeliveryOrder,
  getDeliveryStore,
  listDeliveryStores,
  simulateDeliveryStatus,
  submitDeliveryOrder,
} from "../api/delivery";
```

- [ ] **Step 3: 在 tracking 步驟加上 Demo 按鈕**

在 tracking 區塊裡，找到「配送狀態」進度條這個 `<div>`（結尾是 `</div>` 後緊接著返回首頁按鈕）：

```tsx
            {/* Status progress bar */}
            <div className="rounded-xl bg-slate-50 p-4">
              ...
            </div>

            <button
              type="button"
              onClick={() => navigate("/home")}
              className="mt-2 min-h-[44px] rounded-2xl border-2 border-brand px-6 py-4 text-base font-bold text-brand"
            >
              返回首頁
            </button>
```

在進度條 `</div>` 和「返回首頁」按鈕之間插入：

```tsx
            {(() => {
              const PLATFORM_STATUS_ORDER = ["01", "02", "03", "04", "05", "70"];
              const currentIndex = PLATFORM_STATUS_ORDER.indexOf(order.order_status);
              if (currentIndex === -1 || currentIndex === PLATFORM_STATUS_ORDER.length - 1) return null;
              const nextVendorStatus = currentIndex + 1;
              const driver =
                nextVendorStatus >= 3
                  ? {
                      driver_name: "示範外送員",
                      driver_phone: "0912345678",
                      eta_minutes: Math.max(0, (5 - nextVendorStatus) * 10),
                    }
                  : undefined;
              return (
                <button
                  type="button"
                  onClick={() =>
                    simulateDeliveryStatus(order.request_id, nextVendorStatus, driver).then(async () => {
                      const updated = await getDeliveryOrder(order.request_id);
                      setOrder(updated);
                    })
                  }
                  className="mt-2 min-h-[44px] rounded-2xl border-2 border-brand px-6 py-4 text-base font-bold text-brand"
                >
                  Demo：模擬下一個外送狀態
                </button>
              );
            })()}
```

- [ ] **Step 4: 型別檢查**

Run: `cd frontend && npx tsc --noEmit`
Expected: 無錯誤輸出

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/delivery.ts frontend/src/pages/DeliveryFlowPage.tsx
git commit -m "feat: add demo button to advance delivery tracking status"
```

---

## Task 8: 端到端手動驗證

這個任務沒有新程式碼，目的是確認前面六個任務組裝起來後，聊天下單與 Demo 模擬按鈕在真實跑起來的 App 裡確實可用。

- [ ] **Step 1: 啟動後端**

Run: `cd backend && .venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8000`
Expected: 啟動成功，無 import 錯誤（若 Task 1-6 有遺漏的 import 修正，這一步會立刻曝露）

- [ ] **Step 2: 啟動前端**

Run: `cd frontend && npm run dev`
Expected: 啟動成功，可在瀏覽器開啟

- [ ] **Step 3: 走一次完整聊天下單流程**

在瀏覽器登入任一 demo 帳號，開啟 ButlerLauncher 聊天視窗，依序輸入：
1. `我想叫外送`（預期機器人列出三間店家詢問）
2. `好味道便當`（預期機器人詢問想點哪一項）
3. `招牌雞腿便當一個`（預期機器人確認已加入，並詢問是否加點）
4. `不用了`（預期進入地址詢問）
5. `台北市大安區忠孝東路四段100號`
6. `王小明`
7. `不辣`（預期出現含店家、餐點、地址、收件人、備註的摘要覆誦）
8. `確認送出`（預期收到案件編號回覆）

Expected: 到「我的服務」可以看到這筆美食外送案件；點進去能看到追蹤頁顯示「待接單」狀態。

- [ ] **Step 4: 驗證 Demo 模擬按鈕**

在剛剛建立的案件追蹤頁，重複點擊「Demo：模擬下一個外送狀態」按鈕。

Expected: 狀態依序推進「商家已接單」→「備餐中」→「外送員已取餐」（此時應該開始顯示外送員姓名/電話/預估到達分鐘數）→「配送中」→「已送達」；到「已送達」後按鈕消失。

- [ ] **Step 5: 記錄結果**

若任何一步行為與預期不符，回到對應任務修正並補測試，不要跳過直接修 patch。全部驗證通過後，本計畫視為完成。
