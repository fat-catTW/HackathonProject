# 包裹寄送留資表單 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增 `package_shipping`（包裹寄送）服務，可透過 AI 管家對話與首頁卡片手動表單兩種入口送出，統一收斂到 `shipping.create_shipping_order()`，套用真實黑貓宅急便／7-11 交貨便資費試算、違禁品關鍵字攔截、材積/重量/服務區域限制。

**Architecture:** 比照現有 `reservation.py`/`delivery.py` 的模式，新增一個獨立服務模組 `backend/app/services/shipping.py` 承載驗證/試算/建單邏輯；`catalog.py` 與 `frontend/src/data/services.ts` 各自新增一筆 schema（兩份 schema 沿用專案既有的手動同步慣例）；`agent.py` 修兩個既有的通用收集引擎缺口（`visibleWhen` 未生效、地址型別判斷寫死欄位 id）並新增一個小型「違禁品確認」中斷子流程；`services.py` 的卡片送出端點改為依 `service_id` 分流到 `shipping.create_shipping_order()`。

**Tech Stack:** FastAPI（backend）、React + TypeScript + Vite（frontend）、pytest。

## Global Constraints

- 測試策略依使用者指示做過裁減：只對「純邏輯、可獨立驗證」的部分（`shipping.py` 業務規則、`agent.py` 既有引擎的兩個修正）寫自動化 pytest；完整對話流程、卡片表單送出端點、前端渲染改由你手動實際操作驗證，不另外寫端對端自動測試（最後一個任務會列出手動檢查清單，不是我要執行的步驟）。
- 所有新程式碼比照專案現有慣例：Python 型別提示、`from __future__ import annotations`（若該檔案已使用）、繁體中文 UI 文案。
- `cms_type`/`order_type` 使用內部保留碼 `"20"`（未取得官方資料集代碼表，理由見 spec 的「已知限制」）。
- `service_vendor_id=2` 固定代表「統一速達（黑貓宅急便）」，不拆兩個廠商。
- 已知限制：`weight_kg`/`length_cm`/`width_cm`/`height_cm` 目前只接受整數。`agent.py` 的 `_normalize_field_value()` 對所有 `number` 型別欄位一律擋掉小數輸入（`DECIMAL_NUMBER_RE` 全域檢查，原本是為了數量類欄位如「幾台」設計的），要支援小數重量/材積需要讓這個檢查改成依欄位而非全域擋，這次不動它，示範時包裹重量/材積請一律用整數（例如「3公斤」而非「3.5公斤」）。
- 已知限制：Task 6 的違禁品攔截只掛在 `handle_message()` 最後一段「一般欄位收集」路徑上。如果使用者先給了乾淨的內容物描述、走到「請確認以下申請內容」的摘要階段後才回覆「內容物改成鋰電池」去覆蓋這個欄位，會走 `awaiting_confirmation` 分支裡另一段 `_extract_fields`/`.update()`，不會觸發攔截。這是刻意先不處理的邊界情況（demo 走一般收集路徑不會遇到），要補齊的話要在那個 override 分支也加一次同樣的檢查。

---

### Task 1: 案件狀態與示範廠商帳號

**Files:**
- Modify: `backend/app/services/statuses.py`
- Modify: `backend/app/config.py`

**Interfaces:**
- Produces: `STATUS_LABELS["AWAITING_QUOTE"] == "待廠商報價"`；`AWAITING_QUOTE` 出現在 `VENDOR_PENDING_STATUSES`；`_BUILTIN_VENDOR_ACCOUNTS["vendor2@demo.local"] == {"vendor_id": 2, "name": "統一速達（黑貓宅急便）", "password": "vendor1234"}`。

這兩處都是純資料字典編輯，沒有分支邏輯，不另外寫測試（後續 Task 3 的 `shipping.py` 測試會間接驗證 `AWAITING_QUOTE` 字串正確）。

- [ ] **Step 1: 編輯 `backend/app/services/statuses.py`**

把 `STATUS_LABELS` 字典改成：

```python
STATUS_LABELS = {
    "DRAFT": "草稿",
    "AWAITING_USER_CONFIRMATION": "等待使用者確認",
    "SUBMITTED": "等待廠商確認",
    "AWAITING_QUOTE": "待廠商報價",
    "PENDING_PROVIDER": "等待廠商確認",
    "CONFIRMED": "已確認",
    "IN_PROGRESS": "服務進行中",
    "COMPLETED": "已完成",
    "CANCELLED": "已取消",
    "FAILED": "失敗",
    "VERIFIED": "已核銷",
}
```

把 `VENDOR_PENDING_STATUSES` 改成：

```python
VENDOR_PENDING_STATUSES = ("SUBMITTED", "PENDING_PROVIDER", "AWAITING_QUOTE")
```

- [ ] **Step 2: 編輯 `backend/app/config.py`**

在 `_BUILTIN_VENDOR_ACCOUNTS` 字典（目前只有 `vendor1@demo.local`／`vendor11@demo.local` 兩筆）裡新增一筆：

```python
_BUILTIN_VENDOR_ACCOUNTS: dict = {
    "vendor1@demo.local": {
        "vendor_id": 1,
        "name": "潔家家事服務",
        "password": "vendor1234",
    },
    "vendor11@demo.local": {
        "vendor_id": 11,
        "name": "安心水電工程行",
        "password": "vendor1234",
    },
    "vendor2@demo.local": {
        "vendor_id": 2,
        "name": "統一速達（黑貓宅急便）",
        "password": "vendor1234",
    },
}
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/statuses.py backend/app/config.py
git commit -m "feat: add AWAITING_QUOTE status and package_shipping vendor account"
```

---

### Task 2: `catalog.py` 新增 `package_shipping` schema

**Files:**
- Modify: `backend/app/services/catalog.py`
- Test: `backend/tests/test_catalog_shipping.py`

**Interfaces:**
- Consumes: 無（純資料）。
- Produces: `catalog.get_service_schema("package_shipping")` 回傳 `fields` 陣列，欄位 id 依序為 `pickup_method, sender_address, receiver_address, sender_store, receiver_store, weight_kg, length_cm, width_cm, height_cm, item_description, declared_value, pickup_time_slot, contact_name, phone`；`catalog.vendor_id_for_service("package_shipping") == 2`。

- [ ] **Step 1: 寫失敗測試 `backend/tests/test_catalog_shipping.py`**

```python
from backend.app.services import catalog


def test_package_shipping_schema_field_order_and_branching():
    schema = catalog.get_service_schema("package_shipping")
    field_ids = [f["id"] for f in schema["fields"]]
    assert field_ids == [
        "pickup_method",
        "sender_address",
        "receiver_address",
        "sender_store",
        "receiver_store",
        "weight_kg",
        "length_cm",
        "width_cm",
        "height_cm",
        "item_description",
        "declared_value",
        "pickup_time_slot",
        "contact_name",
        "phone",
    ]

    fields_by_id = {f["id"]: f for f in schema["fields"]}
    assert fields_by_id["sender_address"]["visibleWhen"] == {
        "fieldId": "pickup_method",
        "value": "HOME_PICKUP",
    }
    assert fields_by_id["sender_store"]["visibleWhen"] == {
        "fieldId": "pickup_method",
        "value": "STORE_TO_STORE",
    }
    assert fields_by_id["sender_address"]["type"] == "address"
    assert fields_by_id["pickup_method"]["options"] == ["HOME_PICKUP", "STORE_TO_STORE"]


def test_package_shipping_vendor_is_two():
    assert catalog.vendor_id_for_service("package_shipping") == 2
```

- [ ] **Step 2: 執行測試確認失敗**

```bash
cd backend && python -m pytest tests/test_catalog_shipping.py -v
```
預期：`SERVICE_NOT_FOUND`／`NoneType` 相關失敗（`package_shipping` 尚不存在）。

- [ ] **Step 3: 在 `backend/app/services/catalog.py` 的 `SERVICES` 陣列裡新增一筆**（加在 `food_delivery` entry 後面，`]` 收尾之前）：

```python
    {
        "id": "package_shipping",
        "name": "包裹寄送",
        "description": "統一速達（黑貓宅急便）到府收件或 7-11 店到店寄件",
        "service_vendor_id": 2,
        "cms_type": "20",
        "enabled": True,
        "keywords": ["包裹", "寄件", "寄送", "宅配", "黑貓", "交貨便", "寄快遞", "寄包裹"],
        "schema": {
            "fields": [
                {
                    "id": "pickup_method",
                    "label": "取件方式",
                    "type": "select",
                    "required": True,
                    "options": ["HOME_PICKUP", "STORE_TO_STORE"],
                    "question": "請問希望到府收件，還是要用 7-11 店到店寄件呢？",
                },
                {
                    "id": "sender_address",
                    "label": "寄件地址",
                    "type": "address",
                    "required": True,
                    "visibleWhen": {"fieldId": "pickup_method", "value": "HOME_PICKUP"},
                    "question": "請提供寄件地址。",
                },
                {
                    "id": "receiver_address",
                    "label": "收件地址",
                    "type": "address",
                    "required": True,
                    "visibleWhen": {"fieldId": "pickup_method", "value": "HOME_PICKUP"},
                    "question": "請提供收件地址。",
                },
                {
                    "id": "sender_store",
                    "label": "寄件門市",
                    "type": "text",
                    "required": True,
                    "visibleWhen": {"fieldId": "pickup_method", "value": "STORE_TO_STORE"},
                    "question": "請問要從哪一間 7-11 門市寄件呢？",
                },
                {
                    "id": "receiver_store",
                    "label": "收件門市",
                    "type": "text",
                    "required": True,
                    "visibleWhen": {"fieldId": "pickup_method", "value": "STORE_TO_STORE"},
                    "question": "請問收件人要在哪一間 7-11 門市取件呢？",
                },
                {
                    "id": "weight_kg",
                    "label": "包裹重量（公斤）",
                    "type": "number",
                    "required": True,
                    "question": "請問包裹大約多重呢？（公斤，請填整數）",
                },
                {
                    "id": "length_cm",
                    "label": "包裹長度（公分）",
                    "type": "number",
                    "required": True,
                    "question": "請問包裹的長是幾公分呢？",
                },
                {
                    "id": "width_cm",
                    "label": "包裹寬度（公分）",
                    "type": "number",
                    "required": True,
                    "question": "請問包裹的寬是幾公分呢？",
                },
                {
                    "id": "height_cm",
                    "label": "包裹高度（公分）",
                    "type": "number",
                    "required": True,
                    "question": "請問包裹的高是幾公分呢？",
                },
                {
                    "id": "item_description",
                    "label": "內容物概述",
                    "type": "textarea",
                    "required": True,
                    "question": "請簡單描述包裹內容物是什麼。",
                },
                {
                    "id": "declared_value",
                    "label": "申報價值（元）",
                    "type": "number",
                    "required": True,
                    "question": "請問包裹內容物大約值多少錢呢？",
                },
                {
                    "id": "pickup_time_slot",
                    "label": "取件時段",
                    "type": "time",
                    "required": True,
                    "minValue": "08:30",
                    "maxValue": "18:00",
                    "step": 300,
                    "question": "請問希望什麼時間取件呢？",
                },
                {
                    "id": "contact_name",
                    "label": "聯絡人姓名",
                    "type": "text",
                    "required": True,
                    "question": "請問聯絡人姓名是？",
                },
                {
                    "id": "phone",
                    "label": "聯絡電話",
                    "type": "text",
                    "required": True,
                    "question": "請提供聯絡手機號碼。",
                },
            ]
        },
    },
```

- [ ] **Step 4: 執行測試確認通過**

```bash
cd backend && python -m pytest tests/test_catalog_shipping.py -v
```
預期：2 個測試皆 PASS。

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/catalog.py backend/tests/test_catalog_shipping.py
git commit -m "feat: add package_shipping service schema to catalog"
```

---

### Task 3: `shipping.py` 服務模組（驗證、試算、建單）

**Files:**
- Create: `backend/app/services/shipping.py`
- Test: `backend/tests/test_shipping_service.py`

**Interfaces:**
- Consumes: `backend.app.services.store.STORE` / `now_iso()`（比照 `reservation.py` 的用法）。
- Produces：
  - `contains_prohibited_keywords(text: str) -> list[str]`
  - `estimate_shipping_fee(pickup_method: str, weight_kg: float, length_cm: float, width_cm: float, height_cm: float) -> tuple[int, int]`
  - `create_shipping_order(actor_id: str, payload: dict) -> dict`（成功時回傳 `{"success": True, "request_id": str, "status": "AWAITING_QUOTE", "order_status": "01", "estimated_fee_min": int, "estimated_fee_max": int}`；失敗回傳 `{"success": False, "error": {"code": str, "message": str}}`）
  - 後續 Task 6（agent.py）與 Task 7（services.py）都會 import 並呼叫 `create_shipping_order` 與 `contains_prohibited_keywords`。

- [ ] **Step 1: 寫失敗測試 `backend/tests/test_shipping_service.py`**

```python
import tempfile
from pathlib import Path

import pytest

from backend.app.services import shipping, store as store_module


@pytest.fixture(autouse=True)
def isolated_store(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        test_store = store_module.MemoryStore(storage_path=Path(tmp) / "store.json")
        monkeypatch.setattr(store_module, "STORE", test_store)
        monkeypatch.setattr(shipping, "STORE", test_store)
        yield test_store


def valid_home_pickup_payload(**overrides):
    payload = {
        "pickup_method": "HOME_PICKUP",
        "sender_address": "台北市信義區松仁路100號",
        "receiver_address": "新北市板橋區文化路一段1號",
        "weight_kg": 3,
        "length_cm": 20,
        "width_cm": 20,
        "height_cm": 15,
        "item_description": "衣物",
        "declared_value": 500,
        "pickup_time_slot": "14:00",
        "contact_name": "王大明",
        "phone": "0912345678",
    }
    payload.update(overrides)
    return payload


def valid_store_to_store_payload(**overrides):
    payload = {
        "pickup_method": "STORE_TO_STORE",
        "sender_store": "7-ELEVEN 信義門市",
        "receiver_store": "7-ELEVEN 板橋門市",
        "weight_kg": 2,
        "length_cm": 20,
        "width_cm": 15,
        "height_cm": 10,
        "item_description": "書籍",
        "declared_value": 300,
        "pickup_time_slot": "14:00",
        "contact_name": "王大明",
        "phone": "0912345678",
    }
    payload.update(overrides)
    return payload


# ---- estimate_shipping_fee ----

def test_estimate_fee_home_pickup_tiers():
    assert shipping.estimate_shipping_fee("HOME_PICKUP", 3, 20, 20, 15) == (110, 110)  # 55cm
    assert shipping.estimate_shipping_fee("HOME_PICKUP", 3, 30, 30, 25) == (150, 150)  # 85cm
    assert shipping.estimate_shipping_fee("HOME_PICKUP", 3, 40, 40, 30) == (190, 190)  # 110cm


def test_estimate_fee_store_to_store_tiers():
    assert shipping.estimate_shipping_fee("STORE_TO_STORE", 2, 20, 15, 10) == (60, 60)  # 45cm
    assert shipping.estimate_shipping_fee("STORE_TO_STORE", 2, 40, 40, 30) == (125, 135)  # 110cm


# ---- contains_prohibited_keywords ----

def test_prohibited_keywords_detects_battery():
    matched = shipping.contains_prohibited_keywords("裡面有一顆鋰電池")
    assert matched


def test_prohibited_keywords_ignores_plain_clothing():
    assert shipping.contains_prohibited_keywords("衣物一件") == []


# ---- create_shipping_order: happy paths ----

def test_create_shipping_order_home_pickup_success():
    result = shipping.create_shipping_order("user-1", valid_home_pickup_payload())

    assert result["success"] is True
    assert result["status"] == "AWAITING_QUOTE"
    assert result["order_status"] == "01"
    assert result["estimated_fee_min"] == 110

    order = store_module.STORE.get_request("user-1", result["request_id"])
    assert order["service_id"] == "package_shipping"
    assert order["service_vendor_id"] == 2
    assert order["order_type"] == "20"


def test_create_shipping_order_store_to_store_success():
    result = shipping.create_shipping_order("user-1", valid_store_to_store_payload())
    assert result["success"] is True
    assert result["estimated_fee_min"] == 60


# ---- create_shipping_order: validation errors ----

def test_create_shipping_order_rejects_missing_required_field():
    result = shipping.create_shipping_order("user-1", valid_home_pickup_payload(contact_name=""))
    assert result["success"] is False
    assert result["error"]["code"] == "INVALID_FORM_DATA"


def test_create_shipping_order_rejects_oversized_home_pickup_package():
    result = shipping.create_shipping_order(
        "user-1", valid_home_pickup_payload(length_cm=80, width_cm=80, height_cm=80)
    )
    assert result["success"] is False
    assert result["error"]["code"] == "PACKAGE_TOO_LARGE"


def test_create_shipping_order_rejects_overweight_store_to_store_package():
    result = shipping.create_shipping_order("user-1", valid_store_to_store_payload(weight_kg=6))
    assert result["success"] is False
    assert result["error"]["code"] == "PACKAGE_TOO_LARGE"


def test_create_shipping_order_rejects_declared_value_over_limit_for_store_to_store():
    result = shipping.create_shipping_order("user-1", valid_store_to_store_payload(declared_value=6000))
    assert result["success"] is False
    assert result["error"]["code"] == "DECLARED_VALUE_TOO_HIGH"


def test_create_shipping_order_rejects_excluded_county_for_home_pickup():
    result = shipping.create_shipping_order(
        "user-1", valid_home_pickup_payload(sender_address="金門縣金城鎮民生路1號")
    )
    assert result["success"] is False
    assert result["error"]["code"] == "OUT_OF_SERVICE_AREA"
```

- [ ] **Step 2: 執行測試確認失敗**

```bash
cd backend && python -m pytest tests/test_shipping_service.py -v
```
預期：`ModuleNotFoundError: No module named 'backend.app.services.shipping'`。

- [ ] **Step 3: 建立 `backend/app/services/shipping.py`**

```python
"""Package shipping order service (統一速達／黑貓宅急便 + 7-11 店到店)."""
from __future__ import annotations

from .store import STORE, now_iso

EXCLUDED_COUNTIES = {"金門縣", "連江縣", "澎湖縣"}

PROHIBITED_KEYWORDS: dict[str, tuple[str, ...]] = {
    "危險/易燃易爆物品": ("電池", "鋰電池", "瓦斯", "打火機", "油漆", "易燃", "易爆"),
    "易碎品": ("玻璃", "瓷器", "易碎"),
    "生鮮/冷藏冷凍食品": ("生鮮", "冷藏", "冷凍", "海鮮", "肉品"),
    "精密儀器/3C家電": ("筆電", "手機", "相機", "3C", "家電", "精密儀器"),
    "有價證券/證件": ("現金", "股票", "票券", "證件", "有價證券"),
}

_REQUIRED_FIELDS = (
    "pickup_method",
    "weight_kg",
    "length_cm",
    "width_cm",
    "height_cm",
    "item_description",
    "declared_value",
    "pickup_time_slot",
    "contact_name",
    "phone",
)


def contains_prohibited_keywords(text: str) -> list[str]:
    return [
        category
        for category, keywords in PROHIBITED_KEYWORDS.items()
        if any(keyword in text for keyword in keywords)
    ]


def estimate_shipping_fee(
    pickup_method: str, weight_kg: float, length_cm: float, width_cm: float, height_cm: float
) -> tuple[int, int]:
    total_cm = length_cm + width_cm + height_cm
    if pickup_method == "HOME_PICKUP":
        if total_cm <= 60:
            return (110, 110)
        if total_cm <= 90:
            return (150, 150)
        return (190, 190)  # 91–120cm；超過 120cm 由 _validate_payload 擋下
    if total_cm <= 105:
        return (60, 60)
    return (125, 135)  # 106–120cm 大包裹；超過 120cm 由 _validate_payload 擋下


def _error(code: str, message: str) -> dict:
    return {"success": False, "error": {"code": code, "message": message}}


def _validate_payload(payload: dict) -> dict | None:
    for field_id in _REQUIRED_FIELDS:
        if payload.get(field_id) in (None, ""):
            return _error("INVALID_FORM_DATA", f"Missing required field: {field_id}")

    pickup_method = payload["pickup_method"]
    if pickup_method not in ("HOME_PICKUP", "STORE_TO_STORE"):
        return _error("INVALID_FORM_DATA", "pickup_method 必須是 HOME_PICKUP 或 STORE_TO_STORE。")

    if pickup_method == "HOME_PICKUP":
        if payload.get("sender_address") in (None, "") or payload.get("receiver_address") in (None, ""):
            return _error("INVALID_FORM_DATA", "到府收件需要填寫寄件與收件地址。")
    else:
        if payload.get("sender_store") in (None, "") or payload.get("receiver_store") in (None, ""):
            return _error("INVALID_FORM_DATA", "店到店需要填寫寄件與收件門市。")

    total_cm = payload["length_cm"] + payload["width_cm"] + payload["height_cm"]
    weight_kg = payload["weight_kg"]

    if pickup_method == "HOME_PICKUP":
        if total_cm > 120 or weight_kg > 20:
            return _error(
                "PACKAGE_TOO_LARGE",
                "包裹尺寸或重量超過到府收件上限（三邊合計120公分、20公斤），請聯繫客服安排其他貨運。",
            )
        sender_address = payload.get("sender_address", "")
        if any(county in sender_address for county in EXCLUDED_COUNTIES):
            return _error("OUT_OF_SERVICE_AREA", "暫不提供此地區收件服務。")
    else:
        if total_cm > 120 or weight_kg > 5:
            return _error(
                "PACKAGE_TOO_LARGE",
                "包裹尺寸或重量超過店到店上限（三邊合計120公分、5公斤），請改選到府收件。",
            )
        if payload["declared_value"] > 5000:
            return _error("DECLARED_VALUE_TOO_HIGH", "申報價值超過店到店上限（5,000元），請改選到府收件。")

    return None


def create_shipping_order(actor_id: str, payload: dict) -> dict:
    validation_error = _validate_payload(payload)
    if validation_error:
        return validation_error

    fee_min, fee_max = estimate_shipping_fee(
        payload["pickup_method"],
        payload["weight_kg"],
        payload["length_cm"],
        payload["width_cm"],
        payload["height_cm"],
    )

    request_id = STORE.next_request_id()
    created_at = now_iso()
    order = {
        "request_id": request_id,
        "session_id": payload.get("session_id"),
        "service_id": "package_shipping",
        "service_name": "包裹寄送",
        "service_vendor_id": 2,
        "order_type": "20",
        "order_status": "01",
        "status": "AWAITING_QUOTE",
        "form_data": {k: v for k, v in payload.items() if k != "session_id"},
        "estimated_fee_min": fee_min,
        "estimated_fee_max": fee_max,
        "created_at": created_at,
    }

    try:
        STORE.save_request(actor_id, order)
    except Exception as exc:
        return _error("ORDER_SAVE_FAILED", str(exc))

    return {
        "success": True,
        "request_id": request_id,
        "status": "AWAITING_QUOTE",
        "order_status": "01",
        "estimated_fee_min": fee_min,
        "estimated_fee_max": fee_max,
    }
```

- [ ] **Step 4: 執行測試確認全部通過**

```bash
cd backend && python -m pytest tests/test_shipping_service.py -v
```
預期：12 個測試全部 PASS。

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/shipping.py backend/tests/test_shipping_service.py
git commit -m "feat: add shipping service with fee estimation and validation"
```

---

### Task 4: 修正 `agent.py` 通用收集引擎的兩個既有缺口

**Files:**
- Modify: `backend/app/agent/agent.py`
- Test: `backend/tests/test_agent_regressions.py`（既有檔案，附加測試）

**Interfaces:**
- Produces: `_recompute_missing(state)` 會跳過 `visibleWhen` 條件不成立的欄位；`_normalize_field_value(field, value, original_text)` 對任何 `field["type"] == "address"` 的欄位（不只是 `field_id == "address"`）都會走 `nlu.parse_address`。

這是包裹寄送分岔表單能一次一問運作的前提（見 spec 架構第 2 節），也是既有程式碼的缺陷修正，其他服務不受影響（用回歸測試保證）。

- [ ] **Step 1: 在 `backend/tests/test_agent_regressions.py` 尾端附加失敗測試**

```python
from backend.app.agent.agent import _recompute_missing


def test_recompute_missing_skips_fields_hidden_by_visible_when():
    state = {
        "service_schema": {
            "fields": [
                {"id": "pickup_method", "type": "select", "required": True},
                {
                    "id": "sender_store",
                    "type": "text",
                    "required": True,
                    "visibleWhen": {"fieldId": "pickup_method", "value": "STORE_TO_STORE"},
                },
                {
                    "id": "sender_address",
                    "type": "address",
                    "required": True,
                    "visibleWhen": {"fieldId": "pickup_method", "value": "HOME_PICKUP"},
                },
            ]
        },
        "collected_fields": {"pickup_method": "HOME_PICKUP"},
    }

    _recompute_missing(state)

    assert state["missing_fields"] == ["sender_address"]


def test_normalize_field_value_parses_address_type_by_type_not_field_id():
    field = {"id": "receiver_address", "type": "address", "required": True}
    noisy_text = "地址是台北市信義區松仁路100號沒錯"
    result = _normalize_field_value(field, noisy_text, noisy_text)
    assert result == "台北市信義區松仁路100號"
```

- [ ] **Step 2: 執行測試確認失敗**

```bash
cd backend && python -m pytest tests/test_agent_regressions.py -v -k "visible_when or address_type"
```
預期：兩個新測試都 FAIL。`test_recompute_missing_skips_fields_hidden_by_visible_when` 的 `missing_fields` 會同時包含 `sender_store` 和 `sender_address`（目前沒檢查 `visibleWhen`，兩個分支的必填欄位都被當成缺漏）。`test_normalize_field_value_parses_address_type_by_type_not_field_id` 會得到整句未清理的雜訊文字，不等於預期的乾淨地址（`receiver_address` 的 `field_id` 不等於字面上的 `"address"`，目前程式碼判斷的是 `field_id == "address"`，不會命中，會落到最後通用的 `str(value).strip()` 分支，原封不動回傳整句雜訊；修正後改判斷 `field["type"] == "address"`，才會命中並呼叫 `nlu.parse_address()` 正確截出乾淨地址）。

- [ ] **Step 3: 修正 `backend/app/agent/agent.py` 的 `_recompute_missing`（第 243–249 行）**

把：

```python
def _recompute_missing(state: dict) -> None:
    fields = state["service_schema"]["fields"]
    state["missing_fields"] = [
        field["id"]
        for field in fields
        if field.get("required") and field["id"] not in state["collected_fields"]
    ]
```

改成：

```python
def _field_is_visible(field: dict, collected: dict) -> bool:
    visible_when = field.get("visibleWhen")
    if not isinstance(visible_when, dict):
        return True
    parent_field_id = visible_when.get("fieldId")
    expected_value = visible_when.get("value")
    if not isinstance(parent_field_id, str):
        return True
    return collected.get(parent_field_id) == expected_value


def _recompute_missing(state: dict) -> None:
    fields = state["service_schema"]["fields"]
    collected = state["collected_fields"]
    state["missing_fields"] = [
        field["id"]
        for field in fields
        if field.get("required") and field["id"] not in collected and _field_is_visible(field, collected)
    ]
```

- [ ] **Step 4: 修正 `backend/app/agent/agent.py` 的地址型別判斷（第 552–553 行）**

把：

```python
    if field_id == "address":
        return nlu.parse_address(str(value)) or nlu.parse_address(original_text) or str(value).strip()
```

改成：

```python
    if field["type"] == "address":
        return nlu.parse_address(str(value)) or nlu.parse_address(original_text) or str(value).strip()
```

- [ ] **Step 5: 執行測試確認通過**

```bash
cd backend && python -m pytest tests/test_agent_regressions.py -v
```
預期：檔案內全部測試（含既有的與新增的）皆 PASS。

- [ ] **Step 6: 執行完整後端測試套件，確認沒有破壞其他服務**

```bash
cd backend && python -m pytest -q
```
預期：全部 PASS（`antibacterial_film_quantity` 這種既有 `visibleWhen` 用法本來就是非必填欄位，行為不受這次修正影響）。

- [ ] **Step 7: Commit**

```bash
git add backend/app/agent/agent.py backend/tests/test_agent_regressions.py
git commit -m "fix: make _recompute_missing respect visibleWhen and generalize address type check"
```

---

### Task 5: 取件方式的離線解析與顯示名稱

**Files:**
- Modify: `backend/app/agent/nlu.py`
- Modify: `backend/app/agent/agent.py`

**Interfaces:**
- Produces: `nlu.parse_pickup_method(text: str) -> str | None`（"HOME_PICKUP" / "STORE_TO_STORE" / `None`）；`agent.SELECT_ALIASES`/`agent.SELECT_DISPLAY_NAMES` 新增 `HOME_PICKUP`/`STORE_TO_STORE` 兩個 key，讓摘要文字顯示中文而非代碼。

`_build_field_question()` 不需要改——每個新欄位在 Task 2 的 schema 裡都已經帶 `question` 文字，函式最後本來就有 `return field.get("question") or ...` 的通用 fallback。`FIELD_DISPLAY_NAMES`／`_display_field_label()` 也不需要改，因為它一樣是先看 `field.get("label")`（Task 2 的 schema 每個欄位都帶了 `label`）才會退回內建字典。`SERVICE_DISPLAY_NAMES`／`_display_service_name()` 同理不需要改，`state["service_name"]` 一開始就是從 `catalog.py` 的 `name`（「包裹寄送」）帶入，不在內建字典裡的服務會直接用這個帶入值當 fallback。

- [ ] **Step 1: 在 `backend/app/agent/nlu.py` 新增函式**（放在 `parse_yes_no_option` 後面）：

```python
def parse_pickup_method(text: str) -> str | None:
    if re.search(r"店到店|超商|7-11|7-eleven|7-ELEVEN", text, re.IGNORECASE):
        return "STORE_TO_STORE"
    if re.search(r"到府|宅配到府|到家|上門", text):
        return "HOME_PICKUP"
    return None
```

- [ ] **Step 2: 在 `backend/app/agent/nlu.py` 的 `extract_fields()` dispatcher 新增一個分支**（在 `elif fid == "antibacterial_film_addon":` 那行之後加一行同層級的 `elif`）：

```python
        elif fid == "pickup_method":
            value = parse_pickup_method(text)
```

- [ ] **Step 3: 在 `backend/app/agent/agent.py` 的 `SELECT_ALIASES` 字典新增兩筆**（跟著既有的 `"NO": (...)`那行後面加）：

```python
    "HOME_PICKUP": ("HOME_PICKUP", "到府收件", "到府", "宅配到府"),
    "STORE_TO_STORE": ("STORE_TO_STORE", "店到店", "超商", "7-11", "7-ELEVEN"),
```

- [ ] **Step 4: 在 `backend/app/agent/agent.py` 的 `SELECT_DISPLAY_NAMES` 字典新增兩筆：**

```python
    "HOME_PICKUP": "到府收件",
    "STORE_TO_STORE": "7-11 店到店",
```

- [ ] **Step 5: 在 `backend/app/agent/agent.py` 的 `_normalize_field_value()` select 分支新增 `pickup_method` 判斷**（加在 `if field_id == "antibacterial_film_addon":` 那個 if 區塊後面，`return _normalize_select(...)` 那行之前）：

```python
        if field_id == "pickup_method":
            return (
                _normalize_select(str(value), field.get("options", []))
                or nlu.parse_pickup_method(str(value))
                or nlu.parse_pickup_method(original_text)
            )
```

- [ ] **Step 6: 手動確認語法正確**

```bash
cd backend && python -c "from app.agent import agent, nlu; print(nlu.parse_pickup_method('我要店到店寄件')); print(nlu.parse_pickup_method('到府收件就好'))"
```
預期輸出：
```
STORE_TO_STORE
HOME_PICKUP
```

- [ ] **Step 7: Commit**

```bash
git add backend/app/agent/nlu.py backend/app/agent/agent.py
git commit -m "feat: parse pickup method from free text and display it in Chinese"
```

---

### Task 6: agent.py 違禁品確認子流程與送出邏輯

**Files:**
- Modify: `backend/app/agent/agent.py`

**Interfaces:**
- Consumes: `shipping.contains_prohibited_keywords(text)`、`shipping.create_shipping_order(actor_id, payload)`（Task 3 產生）。
- Produces: `state["pending_prohibited_item"]`（`new_state()` 新增的 key）；`_submit_package_shipping(actor_id, state, latest_user_message) -> dict`；`_submit()` 新增 `package_shipping` 分支。

這個任務是新的對話分支邏輯，依你的指示不另外寫自動化測試——Task 9 的手動檢查清單會涵蓋這條路徑的驗證。

- [ ] **Step 1: 在 `backend/app/agent/agent.py` 檔案開頭的 import 加上 `shipping`**

把：

```python
from ..services import delivery, delivery_catalog, reservation
```

改成：

```python
from ..services import delivery, delivery_catalog, reservation, shipping
```

- [ ] **Step 2: 在 `new_state()` 回傳的字典裡新增一個 key**（跟著 `"pending_delivery_field": None,` 那行後面加）：

```python
        "pending_prohibited_item": None,
```

- [ ] **Step 3: 在 `handle_message()` 裡新增違禁品中斷檢查**

找到這段（在 `pending_delivery_field` 檢查之後）：

```python
    if state.get("pending_delivery_field"):
        return _handle_delivery_pending_reply(actor_id, state, text, events)

    if state.get("pending_pref_field"):
```

改成：

```python
    if state.get("pending_delivery_field"):
        return _handle_delivery_pending_reply(actor_id, state, text, events)

    if state.get("pending_prohibited_item"):
        return _handle_prohibited_item_reply(actor_id, state, text, events)

    if state.get("pending_pref_field"):
```

- [ ] **Step 4: 在 `handle_message()` 尾端攔截 `item_description`**

找到這段（`handle_message` 函式最後三行）：

```python
    found = _extract_fields(actor_id, state, text, events)
    state["collected_fields"].update(found)
    _recompute_missing(state)
    return _continue_collection(actor_id, state, latest_user_message=text, events=events)
```

改成：

```python
    found = _extract_fields(actor_id, state, text, events)
    if state.get("service_id") == "package_shipping" and "item_description" in found:
        matched = shipping.contains_prohibited_keywords(found["item_description"])
        if matched:
            state["pending_prohibited_item"] = found.pop("item_description")
            state["collected_fields"].update(found)
            _recompute_missing(state)
            categories = "、".join(matched)
            return _reply(
                state,
                f"你提到的內容物可能屬於「{categories}」類別，這類物品寄送有限制。"
                "請問已詳讀寄送規範，確認可以寄送嗎？如果不確定，也可以直接重新描述內容物。",
            )
    state["collected_fields"].update(found)
    _recompute_missing(state)
    return _continue_collection(actor_id, state, latest_user_message=text, events=events)
```

- [ ] **Step 5: 新增 `_handle_prohibited_item_reply()`**（放在 `_handle_delivery_pending_reply()` 函式後面）：

```python
def _handle_prohibited_item_reply(actor_id: str, state: dict, text: str, events: list[dict] | None) -> dict:
    pending_text = state["pending_prohibited_item"]
    verdict = _judge_reply("已詳讀寄送規範，確認可以寄送嗎？", text)
    state["pending_prohibited_item"] = None
    if verdict == "yes":
        state["collected_fields"]["item_description"] = pending_text
        _recompute_missing(state)
        return _continue_collection(actor_id, state, latest_user_message=text, events=events)
    return _reply(state, "好的，請重新描述包裹內容物，我們可以再確認一次是否能寄送。")
```

- [ ] **Step 6: 新增 `_submit_package_shipping()`**（放在 `_submit_delivery()` 函式後面）：

```python
def _submit_package_shipping(actor_id: str, state: dict, latest_user_message: str) -> dict:
    payload = dict(state["collected_fields"])
    result = shipping.create_shipping_order(actor_id, payload)

    if not result.get("success"):
        message = result.get("error", {}).get("message", "包裹寄送建立失敗")
        state["awaiting_confirmation"] = False
        state["status"] = "COLLECTING_INFORMATION"
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
    fee_min = result.get("estimated_fee_min")
    fee_max = result.get("estimated_fee_max")
    if fee_min is not None:
        reply = f"{reply}\n依重量與材積試算，預估運費約 NT${fee_min}–{fee_max}，正式報價將由客服於 30 分鐘內回覆確認。"
    return _reply(state, reply)
```

- [ ] **Step 7: 在 `_submit()` 裡新增分流**

找到這段：

```python
    if state["service_id"] == "restaurant_reservation":
        return _submit_reservation(actor_id, state, latest_user_message)

    if state["service_id"] == "food_delivery":
        return _submit_delivery(actor_id, state, latest_user_message)
```

改成：

```python
    if state["service_id"] == "restaurant_reservation":
        return _submit_reservation(actor_id, state, latest_user_message)

    if state["service_id"] == "food_delivery":
        return _submit_delivery(actor_id, state, latest_user_message)

    if state["service_id"] == "package_shipping":
        return _submit_package_shipping(actor_id, state, latest_user_message)
```

- [ ] **Step 8: 執行完整後端測試套件，確認沒有語法錯誤或既有測試被破壞**

```bash
cd backend && python -m pytest -q
```
預期：全部 PASS（這個任務沒新增自動化測試，這一步只是確認沒有把既有功能弄壞）。

- [ ] **Step 9: Commit**

```bash
git add backend/app/agent/agent.py
git commit -m "feat: wire package_shipping into the chat agent with prohibited-item confirmation"
```

---

### Task 7: 卡片表單送出端點改走 `shipping.create_shipping_order()`

**Files:**
- Modify: `backend/app/api/services.py`

**Interfaces:**
- Consumes: `shipping.create_shipping_order(actor_id, payload)`（Task 3）。
- Produces: `POST /api/services/package_shipping/requests` 回傳格式與其他服務一致（`{success, request_id, status, message}`），業務規則跟 AI 管家對話入口一致。

- [ ] **Step 1: 修改 `backend/app/api/services.py`**

把 import 區塊：

```python
from ..services import catalog
from ..services.submission import create_manual_service_request
```

改成：

```python
from ..services import catalog, shipping
from ..services.submission import create_manual_service_request
```

把 `create_service_request()` 函式本體：

```python
@router.post("/api/services/{service_id}/requests")
def create_service_request(
    service_id: str,
    body: dict,
    user: CurrentUser = Depends(get_current_user),
):
    payload = body.get("payload") or {}
    result = create_manual_service_request(
        actor_id=user.sub,
        service_id=service_id,
        payload=payload,
    )
    if not result.get("success", True):
        error = result.get("error", {})
        status_code = (
            400
            if error.get("code") == "INVALID_FORM_DATA"
            else 404
            if error.get("code") == "SERVICE_NOT_FOUND"
            else 503
        )
        _raise_api_error(
            status_code,
            error.get("code", "REQUEST_CREATE_FAILED"),
            error.get("message", "Failed to create service request."),
            missing_fields=error.get("missing_fields", []),
        )
    return {
        "success": True,
        "request_id": result.get("request_id"),
        "status": result.get("status"),
        "message": result.get("message", ""),
    }
```

改成：

```python
@router.post("/api/services/{service_id}/requests")
def create_service_request(
    service_id: str,
    body: dict,
    user: CurrentUser = Depends(get_current_user),
):
    payload = body.get("payload") or {}

    if service_id == "package_shipping":
        result = shipping.create_shipping_order(actor_id=user.sub, payload=payload)
    else:
        result = create_manual_service_request(
            actor_id=user.sub,
            service_id=service_id,
            payload=payload,
        )

    if not result.get("success", True):
        error = result.get("error", {})
        client_error_codes = {
            "INVALID_FORM_DATA",
            "PACKAGE_TOO_LARGE",
            "OUT_OF_SERVICE_AREA",
            "DECLARED_VALUE_TOO_HIGH",
        }
        status_code = (
            400
            if error.get("code") in client_error_codes
            else 404
            if error.get("code") == "SERVICE_NOT_FOUND"
            else 503
        )
        _raise_api_error(
            status_code,
            error.get("code", "REQUEST_CREATE_FAILED"),
            error.get("message", "Failed to create service request."),
            missing_fields=error.get("missing_fields", []),
        )

    message = result.get("message", "")
    if result.get("estimated_fee_min") is not None:
        message = (
            f"預估運費約 NT${result['estimated_fee_min']}–{result['estimated_fee_max']}，"
            "正式報價將由客服於 30 分鐘內回覆確認。"
        )
    return {
        "success": True,
        "request_id": result.get("request_id"),
        "status": result.get("status"),
        "message": message,
    }
```

- [ ] **Step 2: 執行完整後端測試套件確認沒有破壞既有服務**

```bash
cd backend && python -m pytest -q
```
預期：全部 PASS（水電/清潔/冷氣/洗衣機仍走 `create_manual_service_request` 分支，行為不變）。

- [ ] **Step 3: Commit**

```bash
git add backend/app/api/services.py
git commit -m "feat: route package_shipping card submissions through shipping.create_shipping_order"
```

---

### Task 8: 首頁卡片 schema（`frontend/src/data/services.ts`）

**Files:**
- Modify: `frontend/src/data/services.ts`

**Interfaces:**
- Produces: `SERVICES` 陣列新增 `service_id: "package_shipping"` 一筆，`HomePage.tsx` 會自動渲染出卡片（不需要改 `HomePage.tsx`），點卡片會走萬用路由 `/services/:serviceId` → `ServiceFormPage.tsx`（不需要改 `App.tsx`，因為沒有幫 `package_shipping` 加專屬路由）。

- [ ] **Step 1: 在 `frontend/src/data/services.ts` 的 `SERVICES` 陣列新增一筆**（加在 `food_delivery` entry 後面，陣列 `]` 之前）：

```typescript
  {
    service_id: "package_shipping",
    title: "包裹寄送",
    subtitle: "統一速達（黑貓宅急便）到府收件或 7-11 店到店",
    description: "填寫寄件/收件資訊與包裹重量材積，由統一速達為您安排收送件。",
    icon: "moving",
    fields: [
      {
        id: "pickup_method",
        label: "取件方式",
        type: "select",
        required: true,
        options: ["HOME_PICKUP", "STORE_TO_STORE"],
        hint: "選擇到府收件或 7-11 店到店寄件。",
        sectionTitle: "取件方式",
        inputIcon: "moving",
      },
      {
        id: "sender_address",
        label: "寄件地址",
        type: "text",
        required: true,
        hint: "請填寫完整寄件地址。",
        placeholder: "例如：台北市信義區松仁路100號",
        visibleWhen: { fieldId: "pickup_method", value: "HOME_PICKUP" },
        sectionTitle: "地址資訊",
        inputIcon: "location",
      },
      {
        id: "receiver_address",
        label: "收件地址",
        type: "text",
        required: true,
        hint: "請填寫完整收件地址。",
        placeholder: "例如：新北市板橋區文化路一段1號",
        visibleWhen: { fieldId: "pickup_method", value: "HOME_PICKUP" },
        sectionTitle: "地址資訊",
        inputIcon: "location",
      },
      {
        id: "sender_store",
        label: "寄件門市",
        type: "text",
        required: true,
        hint: "請填寫 7-11 寄件門市全名。",
        placeholder: "例如：7-ELEVEN 信義門市",
        visibleWhen: { fieldId: "pickup_method", value: "STORE_TO_STORE" },
        sectionTitle: "門市資訊",
        inputIcon: "location",
      },
      {
        id: "receiver_store",
        label: "收件門市",
        type: "text",
        required: true,
        hint: "請填寫 7-11 收件門市全名。",
        placeholder: "例如：7-ELEVEN 板橋門市",
        visibleWhen: { fieldId: "pickup_method", value: "STORE_TO_STORE" },
        sectionTitle: "門市資訊",
        inputIcon: "location",
      },
      {
        id: "weight_kg",
        label: "包裹重量（公斤）",
        type: "number",
        required: true,
        hint: "請填寫包裹重量，單位公斤。",
        placeholder: "例如：3",
        sectionTitle: "包裹規格",
        inputIcon: "check",
      },
      {
        id: "length_cm",
        label: "包裹長度（公分）",
        type: "number",
        required: true,
        placeholder: "例如：30",
        sectionTitle: "包裹規格",
        inputIcon: "check",
      },
      {
        id: "width_cm",
        label: "包裹寬度（公分）",
        type: "number",
        required: true,
        placeholder: "例如：25",
        sectionTitle: "包裹規格",
        inputIcon: "check",
      },
      {
        id: "height_cm",
        label: "包裹高度（公分）",
        type: "number",
        required: true,
        placeholder: "例如：20",
        sectionTitle: "包裹規格",
        inputIcon: "check",
      },
      {
        id: "item_description",
        label: "內容物概述",
        type: "textarea",
        required: true,
        hint: "請簡單描述包裹內容物，違禁品（電池、易碎品、生鮮等）將無法受理。",
        placeholder: "例如：衣物一件",
        rows: 3,
        sectionTitle: "包裹規格",
        inputIcon: "info",
      },
      {
        id: "declared_value",
        label: "申報價值（元）",
        type: "number",
        required: true,
        hint: "店到店申報價值上限 5,000 元。",
        placeholder: "例如：500",
        sectionTitle: "包裹規格",
        inputIcon: "check",
      },
      {
        id: "pickup_time_slot",
        label: "取件時段",
        type: "time",
        required: true,
        hint: "請選擇希望的取件時間。",
        minValue: "08:30",
        maxValue: "18:00",
        step: 300,
        sectionTitle: "預約時間",
        inputIcon: "clock",
      },
      {
        id: "contact_name",
        label: "聯絡人姓名",
        type: "text",
        required: true,
        placeholder: "例如：王大明",
        sectionTitle: "聯絡資訊",
        inputIcon: "phone",
      },
      {
        id: "phone",
        label: "聯絡電話",
        type: "text",
        required: true,
        placeholder: "例如：0912345678",
        sectionTitle: "聯絡資訊",
        inputIcon: "phone",
      },
    ],
  },
```

- [ ] **Step 2: 型別檢查**

```bash
cd frontend && npx tsc -b --noEmit
```
預期：沒有型別錯誤（`type: "text"`／`"select"`／`"number"`／`"textarea"`／`"time"` 都在 `ServiceField["type"]` 既有的 union 裡）。

- [ ] **Step 3: Commit**

```bash
git add frontend/src/data/services.ts
git commit -m "feat: add package_shipping card form schema"
```

---

### Task 9: 手動驗證清單（由你操作，不是自動化步驟）

這個任務不寫程式，只列出兩個入口各自的檢查點，跑起來的方式：

```bash
cd backend && uvicorn app.main:app --reload
cd frontend && npm run dev
```

- [ ] AI 管家對話：輸入「我要寄包裹」，選「到府收件」，依序回答寄件地址、收件地址、重量、長寬高、內容物（先用「衣物」測正常路徑）、申報價值、取件時段、聯絡人、電話，確認摘要後送出，確認回覆有出現預估運費文字（三邊合計對應級距）。
- [ ] 同上，但取件方式改選「店到店」，確認改問門市欄位而不是地址欄位（驗證 Task 4 的 `visibleWhen` 修正生效）。
- [ ] 對話中內容物描述講「裡面有一顆鋰電池」，確認會被攔下要求確認寄送規範，確認回覆「是」後能繼續完成流程；改回覆「不是」，確認會要求重新描述內容物。
- [ ] 首頁點「包裹寄送」卡片，確認能看到完整表單（不是空白頁），切換取件方式時對應欄位會顯示/隱藏，送出後確認案件狀態顯示「待廠商報價」。
- [ ] 用 `vendor2@demo.local` / `vendor1234` 登入廠商後台（`/vendor/login`），確認「待處理諮詢單」分頁能看到剛剛建立的包裹寄送案件。
- [ ] 故意送出超過店到店限制的重量（例如 6 公斤）或超過申報價值（6000 元），確認前端會顯示對應的錯誤訊息而不是靜默失敗。
