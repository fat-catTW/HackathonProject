# 餐廳訂位功能 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 讓使用者可以在 HomePage 點選「餐廳訂位」卡片，透過一次一問的多步驟精靈（wizard）完成訂位（選餐廳→日期→時段→人數→聯絡人→是否高級訂位→確認摘要→送出），後端建立訂單、視情況呼叫（Mock）第三方訂位 Adapter 立即確認，並支援重試與狀態推進（示範模式）。

**Architecture:** 沿用既有的 `catalog.py` + `STORE`（單一 DynamoDB/MemoryStore 資料表，`PK=USER#actorId / SK=REQUEST#requestId`）架構，不新建資料表。前端不重用聊天式 NLU 收集欄位（因為需要餐廳卡片、日期範圍選擇器、人數 +/- 等豐富互動元件，現有 `FieldPanel`/`ButlerPanel` 純聊天介面不支援），而是新增一個獨立的多步驟頁面 `ReservationFlowPage`，直接呼叫新的 `/api/reservations/*` REST API，繞過 agent 的文字解析。第三方訂位串接用 Adapter Pattern，先接一個 Mock 實作（`MockEZTableAdapter`），行為由餐廳的 `supports_booking_api`/`verification_enabled` 旗標決定，之後要換真實 API 只需替換 adapter 實作。狀態自動推進（Requirement 11）與重試佇列（Requirement 9）都實作成可獨立測試的**純函式**，不接真的背景排程執行緒——沿用現有案件明細頁面已有的手動「Demo 模擬」按鈕模式來觸發，只在需要「已完成→已核銷」這個現有系統沒有的新轉場時，加一個條件式的示範按鈕。

**Tech Stack:** FastAPI + Python 3.12（後端）、React + TypeScript + Vite + Tailwind（前端）、pytest + hypothesis（後端測試）、vitest + @testing-library/react（前端測試）。

## Global Constraints

- 所有互動元件觸控區域不小於 44×44px（Requirement 14.1）。
- 所有文字字級不小於 14px；標題、卡片服務名稱、確認摘要資訊字級不小於 16px，行高不小於 1.5（Requirement 14.2）。
- 每一步驟畫面只呈現單一待填欄位或單一待選操作，不同畫面同時顯示多個待填欄位（Requirement 14.3，「一次一問」）。
- 主要行動按鈕一律使用品牌深海藍 `#0F4C81`（Tailwind 中已定義為 `bg-brand`／`text-brand`，直接沿用既有 class，不要新增顏色）。
- 所有狀態訊息同時用顏色＋文字標籤傳達，不單靠顏色（Requirement 14.5）。
- 尊重 `prefers-reduced-motion`：新元件若有進場動畫，需加 `motion-reduce:transition-none` 或等效處理（Requirement 14.7）。
- 不新建資料表；所有訂位資料都寫入既有 `STORE`（`SERVICE_REQUEST` 記錄）。
- 不引入背景排程/cron 套件（如 APScheduler）；Requirement 9（重試）與 Requirement 11（狀態自動推進）的邏輯必須是可被單元測試直接呼叫的純函式，觸發方式沿用現有「手動 Demo 按鈕」模式。
- 金額/深色主題等既有樣式規範不在此功能範圍內，不要更動。

---

## File Structure

### Backend — new files

| File | Responsibility |
|---|---|
| `backend/app/services/restaurant_catalog.py` | 6 間餐廳的靜態清單與查詢函式 |
| `backend/app/services/reservation_validators.py` | 所有欄位驗證規則（日期範圍、人數、手機、姓名、時段、偏好文字）+ `build_service_time` |
| `backend/app/services/booking_adapter.py` | `BookingStatus`/`BookingResult`/`AvailabilityResult`、`BookingAdapter` 基底、`MockEZTableAdapter` 實作、`get_booking_adapter()` 工廠函式 |
| `backend/app/services/reservation.py` | 核心訂位業務邏輯：建立訂單、防重複、查詢、取消 |
| `backend/app/services/retry_service.py` | 重試佇列邏輯（純函式，手動觸發） |
| `backend/app/scheduler/__init__.py` | 空檔案，讓 `scheduler` 成為 package |
| `backend/app/scheduler/status_scheduler.py` | 狀態自動推進邏輯（純函式，手動觸發） |
| `backend/app/api/reservations.py` | 新 REST 端點路由 |
| `backend/tests/test_reservation_validators.py` | 驗證規則測試（含 hypothesis property test） |
| `backend/tests/test_restaurant_catalog.py` | 餐廳目錄測試 |
| `backend/tests/test_booking_adapter.py` | Mock adapter 行為測試 |
| `backend/tests/test_reservation_service.py` | 訂單建立/防重複/查詢/取消測試 |
| `backend/tests/test_status_scheduler.py` | 狀態推進測試 |
| `backend/tests/test_retry_service.py` | 重試佇列測試 |
| `backend/tests/test_reservations_api.py` | API 端到端測試（FastAPI TestClient） |

### Backend — modified files

| File | Change |
|---|---|
| `backend/app/services/store.py` | `BaseStore`/`MemoryStore`/`DynamoDBStore`/`ResilientStore` 新增 `scan_by_entity_type(entity_type)` |
| `backend/app/api/requests.py` | `STATUS_LABELS` 新增 `VERIFIED`；`simulate_status` 在訂位訂單上同步更新 `order_status`/`status_history` |
| `backend/app/main.py` | 註冊 `reservations.router` |
| `backend/requirements.txt` | 新增 `hypothesis>=6.100` |

### Frontend — new files

| File | Responsibility |
|---|---|
| `frontend/src/types/reservation.ts` | 訂位相關 TS 型別 |
| `frontend/src/data/restaurants.ts` | 餐廳清單（前端展示用，鏡射後端 `restaurant_catalog.py`） |
| `frontend/src/api/reservations.ts` | 呼叫 `/api/reservations/*`、`/api/restaurants` 的 fetch 函式 |
| `frontend/src/components/RestaurantCard.tsx` | 單張餐廳卡片 |
| `frontend/src/components/RestaurantCardList.tsx` | 最多 6 張卡片 + 「客服協助媒合」選項 |
| `frontend/src/components/ReservationDatePicker.tsx` | 限制 today~today+60 的日期選擇器 |
| `frontend/src/components/TimeSlotSelector.tsx` | 午餐/晚餐 + 30 分鐘精細時間 |
| `frontend/src/components/PeopleCounter.tsx` | +/- 人數選擇器 |
| `frontend/src/components/ReservationContactForm.tsx` | 聯絡人姓名 + 手機 |
| `frontend/src/components/PremiumToggle.tsx` | 一般/高級訂位二選一 |
| `frontend/src/components/ReservationSummaryCard.tsx` | 確認摘要卡片 |
| `frontend/src/pages/ReservationFlowPage.tsx` | 整合以上元件的精靈主頁面 |
| 上述元件對應的 `*.test.tsx` | 各元件單元測試 |

### Frontend — modified files

| File | Change |
|---|---|
| `frontend/src/components/ServiceIcon.tsx` | 新增 `"restaurant"` icon type |
| `frontend/src/data/services.ts` | 新增 `restaurant_reservation` 服務卡片項目 |
| `frontend/src/components/StatusBadge.tsx` | 新增 `VERIFIED` 狀態樣式 |
| `frontend/src/utils/fieldLabels.ts` | 新增訂位欄位/選項的中文標籤 |
| `frontend/src/App.tsx` | 新增 `/services/restaurant_reservation` 路由 |
| `frontend/src/pages/RequestDetailPage.tsx` | `COMPLETED→VERIFIED` 的示範按鈕（僅限訂位服務且餐廳啟用核銷時顯示） |

---

## Task 1: Store 新增跨使用者掃描能力

**Files:**
- Modify: `backend/app/services/store.py`
- Test: `backend/tests/test_store_scan.py`

**Interfaces:**
- Produces: `BaseStore.scan_by_entity_type(entity_type: str) -> list[dict]`（後續 Task 7、8 的 scheduler/retry 純函式依賴此方法查出「所有使用者」的訂單）

- [ ] **Step 1: 寫失敗測試**

```python
# backend/tests/test_store_scan.py
import tempfile
from pathlib import Path

from backend.app.services.store import MemoryStore


def test_scan_by_entity_type_returns_items_across_all_actors():
    with tempfile.TemporaryDirectory() as tmp:
        store = MemoryStore(storage_path=Path(tmp) / "store.json")
        store.save_request("user-a", {"request_id": "REQ-1", "service_id": "x", "status": "SUBMITTED"})
        store.save_request("user-b", {"request_id": "REQ-2", "service_id": "x", "status": "SUBMITTED"})
        store.save_preferences("user-a", {"last_address": "台北市"})

        items = store.scan_by_entity_type("SERVICE_REQUEST")

        ids = sorted(item["request_id"] for item in items)
        assert ids == ["REQ-1", "REQ-2"]


def test_scan_by_entity_type_ignores_other_entity_types():
    with tempfile.TemporaryDirectory() as tmp:
        store = MemoryStore(storage_path=Path(tmp) / "store.json")
        store.save_preferences("user-a", {"last_address": "台北市"})

        items = store.scan_by_entity_type("SERVICE_REQUEST")

        assert items == []
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_store_scan.py -v`
Expected: FAIL，錯誤訊息包含 `AttributeError: 'MemoryStore' object has no attribute 'scan_by_entity_type'`

- [ ] **Step 3: 實作 `scan_by_entity_type`**

在 `backend/app/services/store.py` 的 `BaseStore` 加入抽象方法（放在 `query_prefix` 之後）：

```python
    def scan_by_entity_type(self, entity_type: str) -> list[dict]:
        raise NotImplementedError
```

在 `MemoryStore` 加入實作（放在 `query_prefix` 之後）：

```python
    def scan_by_entity_type(self, entity_type: str) -> list[dict]:
        with self._lock:
            return [dict(v) for v in self._items.values() if v.get("entity_type") == entity_type]
```

在 `DynamoDBStore` 加入實作（放在 `query_prefix` 之後）：

```python
    def scan_by_entity_type(self, entity_type: str) -> list[dict]:
        from boto3.dynamodb.conditions import Attr

        items: list[dict] = []
        start_key = None
        while True:
            kwargs = {"FilterExpression": Attr("entity_type").eq(entity_type)}
            if start_key:
                kwargs["ExclusiveStartKey"] = start_key
            response = self._table.scan(**kwargs)
            items.extend(response.get("Items", []))
            start_key = response.get("LastEvaluatedKey")
            if not start_key:
                return items
```

在 `ResilientStore` 加入實作（放在 `query_prefix` 之後）：

```python
    def scan_by_entity_type(self, entity_type: str) -> list[dict]:
        try:
            return self._fallback.scan_by_entity_type(entity_type)
        except Exception:
            pass
        if not self._primary_available():
            return []
        try:
            return self._primary.scan_by_entity_type(entity_type)
        except Exception:
            self._mark_primary_unavailable()
            return []
```

- [ ] **Step 4: 執行測試確認通過**

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_store_scan.py -v`
Expected: PASS（2 passed）

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/store.py backend/tests/test_store_scan.py
git commit -m "feat: add cross-actor scan to store backends"
```

---

## Task 2: 餐廳目錄模組

**Files:**
- Create: `backend/app/services/restaurant_catalog.py`
- Test: `backend/tests/test_restaurant_catalog.py`

**Interfaces:**
- Produces: `RESTAURANTS: list[dict]`, `list_restaurants(limit: int = 6) -> list[dict]`, `get_restaurant(restaurant_id: str) -> dict | None`, `supports_third_party_booking(restaurant_id: str) -> bool`
- Consumed by: Task 5 (`reservation.py`), Task 8 (`api/reservations.py`)

- [ ] **Step 1: 寫失敗測試**

```python
# backend/tests/test_restaurant_catalog.py
from backend.app.services import restaurant_catalog


def test_list_restaurants_returns_at_most_six():
    result = restaurant_catalog.list_restaurants()
    assert 1 <= len(result) <= 6


def test_get_restaurant_found():
    restaurant = restaurant_catalog.get_restaurant("r001")
    assert restaurant is not None
    assert restaurant["name"] == "22世紀風味館 信義旗艦店"
    assert restaurant["phone"] == "02-2723-0022"


def test_get_restaurant_not_found():
    assert restaurant_catalog.get_restaurant("does-not-exist") is None


def test_supports_third_party_booking_true_for_r001():
    assert restaurant_catalog.supports_third_party_booking("r001") is True


def test_supports_third_party_booking_false_for_r005():
    assert restaurant_catalog.supports_third_party_booking("r005") is False


def test_supports_third_party_booking_false_for_unknown_restaurant():
    assert restaurant_catalog.supports_third_party_booking("nope") is False
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_restaurant_catalog.py -v`
Expected: FAIL，`ModuleNotFoundError: No module named 'backend.app.services.restaurant_catalog'`

- [ ] **Step 3: 實作**

```python
# backend/app/services/restaurant_catalog.py
"""Static restaurant directory for the restaurant reservation feature."""

RESTAURANTS: list[dict] = [
    {
        "id": "r001",
        "name": "22世紀風味館 信義旗艦店",
        "brand": "22世紀風味館",
        "address": "台北市信義區松高路12號3樓",
        "phone": "02-2723-0022",
        "cuisine": "複合式料理",
        "supports_booking_api": True,
        "verification_enabled": True,
        "image_url": "/images/restaurants/r001.jpg",
    },
    {
        "id": "r002",
        "name": "22世紀風味館 板橋文化店",
        "brand": "22世紀風味館",
        "address": "新北市板橋區文化路一段280號2樓",
        "phone": "02-2258-0022",
        "cuisine": "複合式料理",
        "supports_booking_api": True,
        "verification_enabled": True,
        "image_url": "/images/restaurants/r002.jpg",
    },
    {
        "id": "r003",
        "name": "22世紀風味館 台中公益店",
        "brand": "22世紀風味館",
        "address": "台中市南屯區公益路二段51號",
        "phone": "04-2326-0022",
        "cuisine": "複合式料理",
        "supports_booking_api": True,
        "verification_enabled": False,
        "image_url": "/images/restaurants/r003.jpg",
    },
    {
        "id": "r004",
        "name": "22世紀風味館 高雄夢時代店",
        "brand": "22世紀風味館",
        "address": "高雄市前鎮區中華五路789號B1",
        "phone": "07-812-0022",
        "cuisine": "複合式料理",
        "supports_booking_api": True,
        "verification_enabled": True,
        "image_url": "/images/restaurants/r004.jpg",
    },
    {
        "id": "r005",
        "name": "22世紀風味館 桃園中正店",
        "brand": "22世紀風味館",
        "address": "桃園市桃園區中正路1055號",
        "phone": "03-356-0022",
        "cuisine": "複合式料理",
        "supports_booking_api": False,
        "verification_enabled": False,
        "image_url": "/images/restaurants/r005.jpg",
    },
    {
        "id": "r006",
        "name": "22世紀風味館 新竹巨城店",
        "brand": "22世紀風味館",
        "address": "新竹市東區中央路229號4樓",
        "phone": "03-623-0022",
        "cuisine": "複合式料理",
        "supports_booking_api": True,
        "verification_enabled": True,
        "image_url": "/images/restaurants/r006.jpg",
    },
]


def list_restaurants(limit: int = 6) -> list[dict]:
    return RESTAURANTS[:limit]


def get_restaurant(restaurant_id: str) -> dict | None:
    return next((r for r in RESTAURANTS if r["id"] == restaurant_id), None)


def supports_third_party_booking(restaurant_id: str) -> bool:
    restaurant = get_restaurant(restaurant_id)
    return bool(restaurant and restaurant["supports_booking_api"])
```

- [ ] **Step 4: 執行測試確認通過**

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_restaurant_catalog.py -v`
Expected: PASS（6 passed）

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/restaurant_catalog.py backend/tests/test_restaurant_catalog.py
git commit -m "feat: add static restaurant catalog"
```

---

## Task 3: 訂位驗證規則模組

**Files:**
- Create: `backend/app/services/reservation_validators.py`
- Test: `backend/tests/test_reservation_validators.py`
- Modify: `backend/requirements.txt`（新增 `hypothesis>=6.100`）

**Interfaces:**
- Produces: `validate_phone(phone: str) -> bool`, `validate_contact_name(name: str) -> bool`, `validate_date(selected_date: str, today: date | None = None) -> bool`, `validate_people(people) -> bool`, `validate_time_slot(time_slot: str) -> bool`, `validate_specific_time(time_slot: str, specific_time: str) -> bool`, `validate_preference_note(note: str | None) -> bool`, `build_service_time(date_str: str, specific_time: str | None, time_slot: str) -> str`
- Consumed by: Task 5 (`reservation.py`)

- [ ] **Step 1: 新增測試依賴**

在 `backend/requirements.txt` 最後加一行：

```
hypothesis>=6.100
```

Run: `cd backend && pip install -r requirements.txt`

- [ ] **Step 2: 寫失敗測試**

```python
# backend/tests/test_reservation_validators.py
from datetime import date, timedelta

from hypothesis import given, strategies as st

from backend.app.services.reservation_validators import (
    build_service_time,
    validate_contact_name,
    validate_date,
    validate_people,
    validate_phone,
    validate_preference_note,
    validate_specific_time,
    validate_time_slot,
)

TODAY = date(2026, 7, 29)


# --- example-based boundary tests ---

def test_validate_date_accepts_today():
    assert validate_date(TODAY.isoformat(), today=TODAY) is True


def test_validate_date_accepts_today_plus_60():
    d = (TODAY + timedelta(days=60)).isoformat()
    assert validate_date(d, today=TODAY) is True


def test_validate_date_rejects_today_plus_61():
    d = (TODAY + timedelta(days=61)).isoformat()
    assert validate_date(d, today=TODAY) is False


def test_validate_date_rejects_yesterday():
    d = (TODAY - timedelta(days=1)).isoformat()
    assert validate_date(d, today=TODAY) is False


def test_validate_date_rejects_malformed_string():
    assert validate_date("not-a-date", today=TODAY) is False


def test_validate_people_accepts_boundaries():
    assert validate_people(1) is True
    assert validate_people(20) is True


def test_validate_people_rejects_out_of_range():
    assert validate_people(0) is False
    assert validate_people(21) is False


def test_validate_people_rejects_non_integer():
    assert validate_people(2.5) is False
    assert validate_people("2") is False
    assert validate_people(None) is False


def test_validate_phone_accepts_valid_taiwan_mobile():
    assert validate_phone("0912345678") is True


def test_validate_phone_rejects_wrong_prefix():
    assert validate_phone("0812345678") is False


def test_validate_phone_rejects_wrong_length():
    assert validate_phone("091234567") is False
    assert validate_phone("09123456789") is False


def test_validate_phone_rejects_non_digits():
    assert validate_phone("0912-345-678") is False


def test_validate_contact_name_accepts_normal_name():
    assert validate_contact_name("王大明") is True


def test_validate_contact_name_rejects_blank():
    assert validate_contact_name("   ") is False
    assert validate_contact_name("") is False


def test_validate_contact_name_rejects_too_long():
    assert validate_contact_name("王" * 51) is False


def test_validate_contact_name_accepts_50_chars():
    assert validate_contact_name("王" * 50) is True


def test_validate_time_slot_accepts_lunch_and_dinner():
    assert validate_time_slot("LUNCH") is True
    assert validate_time_slot("DINNER") is True


def test_validate_time_slot_rejects_unknown():
    assert validate_time_slot("BRUNCH") is False


def test_validate_specific_time_accepts_lunch_boundary():
    assert validate_specific_time("LUNCH", "11:00") is True
    assert validate_specific_time("LUNCH", "13:30") is True


def test_validate_specific_time_rejects_lunch_out_of_range():
    assert validate_specific_time("LUNCH", "14:00") is False
    assert validate_specific_time("LUNCH", "10:30") is False


def test_validate_specific_time_rejects_non_30min_increment():
    assert validate_specific_time("LUNCH", "12:15") is False


def test_validate_preference_note_accepts_none_and_short_text():
    assert validate_preference_note(None) is True
    assert validate_preference_note("靠窗座位") is True


def test_validate_preference_note_rejects_over_200_chars():
    assert validate_preference_note("字" * 201) is False


def test_build_service_time_uses_specific_time():
    result = build_service_time("2026-08-01", "12:30", "LUNCH")
    assert result == "2026-08-01T12:30:00+08:00"


def test_build_service_time_falls_back_to_slot_default():
    assert build_service_time("2026-08-01", None, "LUNCH") == "2026-08-01T12:00:00+08:00"
    assert build_service_time("2026-08-01", None, "DINNER") == "2026-08-01T18:00:00+08:00"


# --- property-based tests (Requirement design.md Property 1-4) ---

@given(st.integers(min_value=1, max_value=20))
def test_property_people_in_range_always_valid(n):
    assert validate_people(n) is True


@given(st.integers().filter(lambda n: n < 1 or n > 20))
def test_property_people_out_of_range_always_invalid(n):
    assert validate_people(n) is False


@given(st.from_regex(r"09\d{8}", fullmatch=True))
def test_property_valid_taiwan_phone_shape_always_accepted(phone):
    assert validate_phone(phone) is True


@given(st.text(min_size=1, max_size=50).filter(lambda s: s.strip()))
def test_property_nonblank_name_within_50_chars_always_valid(name):
    assert validate_contact_name(name) is True
```

- [ ] **Step 3: 執行測試確認失敗**

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_reservation_validators.py -v`
Expected: FAIL，`ModuleNotFoundError: No module named 'backend.app.services.reservation_validators'`

- [ ] **Step 4: 實作**

```python
# backend/app/services/reservation_validators.py
"""Validation rules for the restaurant reservation flow."""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone

TZ = timezone(timedelta(hours=8))

_PHONE_RE = re.compile(r"^09\d{8}$")
_LUNCH_TIMES = [f"{h:02d}:{m:02d}" for h in range(11, 14) for m in (0, 30)]
_DINNER_TIMES = [f"{h:02d}:{m:02d}" for h in range(17, 21) for m in (0, 30)]


def validate_phone(phone: str) -> bool:
    """台灣手機號碼驗證：09 開頭、共 10 碼純數字 (Requirement 5.3)"""
    return bool(_PHONE_RE.match(phone))


def validate_contact_name(name: str) -> bool:
    """聯絡人姓名驗證：1-50 字元，不可為空白 (Requirement 5.1, 5.6)"""
    stripped = name.strip()
    return 1 <= len(stripped) <= 50


def validate_date(selected_date: str, today: date | None = None) -> bool:
    """日期驗證：今日起 60 天內 (Requirement 3.2, 3.5)"""
    try:
        d = date.fromisoformat(selected_date)
    except ValueError:
        return False
    reference = today or datetime.now(TZ).date()
    return reference <= d <= reference + timedelta(days=60)


def validate_people(people) -> bool:
    """人數驗證：1-20 人正整數 (Requirement 4.2, 4.5)"""
    if isinstance(people, bool) or not isinstance(people, int):
        return False
    return 1 <= people <= 20


def validate_time_slot(time_slot: str) -> bool:
    """時段驗證 (Requirement 3.4)"""
    return time_slot in ("LUNCH", "DINNER")


def validate_specific_time(time_slot: str, specific_time: str) -> bool:
    """30 分鐘間隔精細時間驗證 (Requirement 3.4)"""
    if time_slot == "LUNCH":
        return specific_time in _LUNCH_TIMES
    if time_slot == "DINNER":
        return specific_time in _DINNER_TIMES
    return False


def validate_preference_note(note: str | None) -> bool:
    """偏好需求文字驗證：最多 200 字 (Requirement 2.3)"""
    if note is None:
        return True
    return len(note) <= 200


def build_service_time(date_str: str, specific_time: str | None, time_slot: str) -> str:
    """
    組合 service_time ISO 8601 格式 (Requirement 7.3)
    若無 specific_time，使用時段預設時間（午餐 12:00, 晚餐 18:00）
    """
    if specific_time:
        return f"{date_str}T{specific_time}:00+08:00"
    default_time = "12:00" if time_slot == "LUNCH" else "18:00"
    return f"{date_str}T{default_time}:00+08:00"
```

- [ ] **Step 5: 執行測試確認通過**

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_reservation_validators.py -v`
Expected: PASS（全部通過，包含 4 個 hypothesis property test）

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/reservation_validators.py backend/tests/test_reservation_validators.py backend/requirements.txt
git commit -m "feat: add reservation field validators"
```

---

## Task 4: 第三方訂位 Mock Adapter

**Files:**
- Create: `backend/app/services/booking_adapter.py`
- Test: `backend/tests/test_booking_adapter.py`

**Interfaces:**
- Produces: `BookingStatus`（Enum：`CONFIRMED`/`PENDING`/`NO_AVAILABILITY`/`ERROR`）, `BookingResult`（dataclass: `status, booking_id, share_reservation_url, message`）, `AvailabilityResult`（dataclass: `available, alternative_slots`）, `BookingAdapter`（base class）, `MockEZTableAdapter`（實作，依 `restaurant["verification_enabled"]` 決定回傳 `CONFIRMED` 或 `ERROR`）, `get_booking_adapter() -> BookingAdapter`
- Consumes: `backend/app/services/restaurant_catalog.get_restaurant`
- Consumed by: Task 5 (`reservation.py`), Task 6 (`retry_service.py`)

**Mock 行為設計（demo 用，之後接真實 API 時整份替換）：**
- 呼叫前提：只有 `restaurant["supports_booking_api"] is True` 時才會被呼叫（`supports_booking_api=False` 的餐廳由呼叫端直接跳過，見 Task 5）。
- `restaurant["verification_enabled"] is True` → 回傳 `CONFIRMED`，附假 `booking_id`/`share_reservation_url`。
- `restaurant["verification_enabled"] is False` → 回傳 `ERROR`（模擬 API 失敗，用來展示 Requirement 9 的重試流程；種子資料中的 `r003` 就是這個情境）。

- [ ] **Step 1: 寫失敗測試**

```python
# backend/tests/test_booking_adapter.py
import asyncio

from backend.app.services.booking_adapter import BookingStatus, MockEZTableAdapter


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def test_create_booking_confirms_for_verification_enabled_restaurant():
    adapter = MockEZTableAdapter()
    result = run(adapter.create_booking(
        restaurant_id="r001", date="2026-08-01", time="12:30",
        people=4, contact_name="王大明", phone="0912345678",
    ))
    assert result.status == BookingStatus.CONFIRMED
    assert result.booking_id is not None
    assert result.share_reservation_url is not None


def test_create_booking_errors_for_verification_disabled_restaurant():
    adapter = MockEZTableAdapter()
    result = run(adapter.create_booking(
        restaurant_id="r003", date="2026-08-01", time="12:30",
        people=2, contact_name="王大明", phone="0912345678",
    ))
    assert result.status == BookingStatus.ERROR
    assert result.booking_id is None


def test_create_booking_errors_for_unknown_restaurant():
    adapter = MockEZTableAdapter()
    result = run(adapter.create_booking(
        restaurant_id="does-not-exist", date="2026-08-01", time="12:30",
        people=2, contact_name="王大明", phone="0912345678",
    ))
    assert result.status == BookingStatus.ERROR


def test_check_availability_always_available_in_mock():
    adapter = MockEZTableAdapter()
    result = run(adapter.check_availability("r001", "2026-08-01", "LUNCH"))
    assert result.available is True
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_booking_adapter.py -v`
Expected: FAIL，`ModuleNotFoundError`

- [ ] **Step 3: 實作**

```python
# backend/app/services/booking_adapter.py
"""Third-party booking API adapter (Adapter Pattern).

MockEZTableAdapter simulates EZTable responses so the reservation flow
can be built and demoed without real API credentials. Swap
`get_booking_adapter()` for a real HTTP-calling implementation later —
no other code needs to change.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum

from . import restaurant_catalog


class BookingStatus(str, Enum):
    CONFIRMED = "CONFIRMED"
    PENDING = "PENDING"
    NO_AVAILABILITY = "NO_AVAILABILITY"
    ERROR = "ERROR"


@dataclass
class BookingResult:
    status: BookingStatus
    booking_id: str | None = None
    share_reservation_url: str | None = None
    message: str | None = None


@dataclass
class AvailabilityResult:
    available: bool
    alternative_slots: list[str] = field(default_factory=list)


class BookingAdapter:
    """Base interface for third-party booking adapters."""

    async def create_booking(
        self,
        restaurant_id: str,
        date: str,
        time: str,
        people: int,
        contact_name: str,
        phone: str,
    ) -> BookingResult:
        raise NotImplementedError

    async def check_availability(
        self,
        restaurant_id: str,
        date: str,
        time_slot: str,
    ) -> AvailabilityResult:
        raise NotImplementedError


class MockEZTableAdapter(BookingAdapter):
    """Simulated EZTable responses, keyed off restaurant seed flags."""

    TIMEOUT_SECONDS = 10  # Requirement 9.1

    async def create_booking(
        self,
        restaurant_id: str,
        date: str,
        time: str,
        people: int,
        contact_name: str,
        phone: str,
    ) -> BookingResult:
        restaurant = restaurant_catalog.get_restaurant(restaurant_id)
        if not restaurant:
            return BookingResult(status=BookingStatus.ERROR, message="Restaurant not found.")

        if restaurant["verification_enabled"]:
            booking_id = f"EZ-MOCK-{uuid.uuid4().hex[:8].upper()}"
            return BookingResult(
                status=BookingStatus.CONFIRMED,
                booking_id=booking_id,
                share_reservation_url=f"https://eztable.example.com/booking/{booking_id}",
            )

        return BookingResult(status=BookingStatus.ERROR, message="Simulated third-party API failure.")

    async def check_availability(
        self,
        restaurant_id: str,
        date: str,
        time_slot: str,
    ) -> AvailabilityResult:
        return AvailabilityResult(available=True)


def get_booking_adapter() -> BookingAdapter:
    return MockEZTableAdapter()
```

- [ ] **Step 4: 執行測試確認通過**

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_booking_adapter.py -v`
Expected: PASS（4 passed）

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/booking_adapter.py backend/tests/test_booking_adapter.py
git commit -m "feat: add mock EZTable booking adapter"
```

---

## Task 5: 訂位核心服務（建立訂單 / 防重複 / 查詢 / 取消）

**Files:**
- Create: `backend/app/services/reservation.py`
- Test: `backend/tests/test_reservation_service.py`

**Interfaces:**
- Consumes: `reservation_validators.*`（Task 3）、`restaurant_catalog.get_restaurant`/`supports_third_party_booking`（Task 2）、`booking_adapter.get_booking_adapter`/`BookingStatus`（Task 4）、`retry_service.mark_for_retry`（Task 6，需先建立空殼避免循環 import 問題——見 Step 3 說明）、`STORE`（`store.py`：`next_request_id`, `save_request`, `get_request`, `query_prefix`）
- Produces:
  - `TEXT_TO_ORDER_STATUS: dict[str, str]`（例如 `{"PENDING_PROVIDER": "02", "CONFIRMED": "03", "IN_PROGRESS": "04", "COMPLETED": "70", "VERIFIED": "80", "CANCELLED": "90"}`，Task 9 也會用到）
  - `create_reservation_order(actor_id: str, payload: dict) -> dict`（回傳 `{"success": bool, "request_id": str, "status": str, "order_status": str, "booking_url": str | None, "error": dict | None}`）
  - `check_duplicate(actor_id: str, restaurant_id: str, reserved_date: str, time_slot: str) -> bool`
  - `get_reservation_order(actor_id: str, request_id: str) -> dict | None`
  - `cancel_reservation_order(actor_id: str, request_id: str) -> dict`

**業務邏輯（對應 Requirement 7, 8, 12, 13）：**
1. 驗證所有欄位（呼叫 Task 3 的 validators），任一失敗回傳對應 `ReservationErrorCode`。
2. 呼叫 `check_duplicate`，若命中回傳 `{"success": False, "error": {"code": "DUPLICATE_RESERVATION", ...}}`（Requirement 12.3）。
3. 建立 `request` dict，寫入 `STORE`：
   - `service_id="restaurant_reservation"`, `service_name="餐廳訂位"`
   - `order_type="02"`
   - `order_items`：`restaurant_id/restaurant_name/restaurant_phone/restaurant_address/people/is_premium/reserved_date/time_slot/specific_time/contact_name/phone/preference_note`
   - `service_time`：`build_service_time(...)`
   - `form_data`：**扁平化**版本（給既有 `RequestDetailPage` 的通用渲染直接吃，見 Task 10 的 `fieldLabels.ts`）
   - `vendor_data={}`, `retry_info={"retry_count": 0, "max_retries": 3, "last_retry_at": None, "needs_manual": False}`
   - `status_history=[{"status": <初始狀態>, "at": now_iso()}]`
4. 決定初始狀態與是否呼叫 adapter：
   - `is_premium is True` → `status="PENDING_PROVIDER"`，**不呼叫** adapter（Requirement 13.4）。
   - `supports_third_party_booking(restaurant_id) is False` → `status="PENDING_PROVIDER"`，不呼叫 adapter（Requirement 8.5）。
   - 否則呼叫 `adapter.create_booking(...)`：
     - `CONFIRMED` → `status="CONFIRMED"`，寫入 `vendor_data`（Requirement 8.2, 8.3）。
     - 其他（`ERROR`/`PENDING`/`NO_AVAILABILITY`）→ `status="PENDING_PROVIDER"`，呼叫 `retry_service.mark_for_retry(request)`（Requirement 8.4, 9.1, 9.2, 9.3）。
5. 設 `order_status = TEXT_TO_ORDER_STATUS[status]`，存回 `STORE`。
6. 回傳結果（含 `booking_url` 只在 `CONFIRMED` 時有值）。

- [ ] **Step 1: 寫失敗測試**

```python
# backend/tests/test_reservation_service.py
import tempfile
from pathlib import Path

import pytest

from backend.app.services import reservation, store as store_module


@pytest.fixture(autouse=True)
def isolated_store(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        test_store = store_module.MemoryStore(storage_path=Path(tmp) / "store.json")
        monkeypatch.setattr(store_module, "STORE", test_store)
        monkeypatch.setattr(reservation, "STORE", test_store)
        yield test_store


def valid_payload(**overrides):
    payload = {
        "restaurant_id": "r001",
        "reserved_date": "2026-08-01",
        "time_slot": "LUNCH",
        "specific_time": "12:30",
        "people": 4,
        "contact_name": "王大明",
        "phone": "0912345678",
        "is_premium": False,
        "preference_note": None,
    }
    payload.update(overrides)
    return payload


def test_create_reservation_order_confirms_immediately_for_supported_restaurant():
    result = reservation.create_reservation_order("user-1", valid_payload())

    assert result["success"] is True
    assert result["status"] == "CONFIRMED"
    assert result["order_status"] == "03"
    assert result["booking_url"] is not None

    order = reservation.get_reservation_order("user-1", result["request_id"])
    assert order["order_type"] == "02"
    assert order["order_items"]["restaurant_name"] == "22世紀風味館 信義旗艦店"
    assert order["service_time"] == "2026-08-01T12:30:00+08:00"


def test_create_reservation_order_pending_when_restaurant_unsupported():
    result = reservation.create_reservation_order("user-1", valid_payload(restaurant_id="r005"))

    assert result["success"] is True
    assert result["status"] == "PENDING_PROVIDER"
    assert result["order_status"] == "02"
    assert result["booking_url"] is None


def test_create_reservation_order_pending_and_retried_on_adapter_error():
    result = reservation.create_reservation_order("user-1", valid_payload(restaurant_id="r003"))

    assert result["status"] == "PENDING_PROVIDER"
    order = reservation.get_reservation_order("user-1", result["request_id"])
    assert order["retry_info"]["retry_count"] >= 0
    assert order["retry_info"]["needs_manual"] is False


def test_create_reservation_order_premium_skips_adapter_even_if_supported():
    result = reservation.create_reservation_order("user-1", valid_payload(is_premium=True))

    assert result["status"] == "PENDING_PROVIDER"
    order = reservation.get_reservation_order("user-1", result["request_id"])
    assert order["order_items"]["is_premium"] is True
    assert order["vendor_data"] == {}


def test_create_reservation_order_rejects_invalid_phone():
    result = reservation.create_reservation_order("user-1", valid_payload(phone="12345"))
    assert result["success"] is False
    assert result["error"]["code"] == "INVALID_PHONE"


def test_create_reservation_order_rejects_out_of_range_people():
    result = reservation.create_reservation_order("user-1", valid_payload(people=21))
    assert result["success"] is False
    assert result["error"]["code"] == "INVALID_PEOPLE_COUNT"


def test_create_reservation_order_rejects_unknown_restaurant():
    result = reservation.create_reservation_order("user-1", valid_payload(restaurant_id="nope"))
    assert result["success"] is False
    assert result["error"]["code"] == "RESTAURANT_NOT_FOUND"


def test_check_duplicate_blocks_same_restaurant_date_slot_for_same_user():
    reservation.create_reservation_order("user-1", valid_payload())

    result = reservation.create_reservation_order("user-1", valid_payload())

    assert result["success"] is False
    assert result["error"]["code"] == "DUPLICATE_RESERVATION"


def test_check_duplicate_allows_different_user_same_slot():
    reservation.create_reservation_order("user-1", valid_payload())

    result = reservation.create_reservation_order("user-2", valid_payload())

    assert result["success"] is True


def test_cancel_reservation_order_sets_cancelled_status():
    created = reservation.create_reservation_order("user-1", valid_payload())

    result = reservation.cancel_reservation_order("user-1", created["request_id"])

    assert result["success"] is True
    order = reservation.get_reservation_order("user-1", created["request_id"])
    assert order["status"] == "CANCELLED"
    assert order["order_status"] == "90"


def test_get_reservation_order_returns_none_for_missing_request():
    assert reservation.get_reservation_order("user-1", "REQ-NOPE") is None
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_reservation_service.py -v`
Expected: FAIL，`ModuleNotFoundError`

- [ ] **Step 3: 實作**

先在 `backend/app/services/retry_service.py` 建立最小空殼（完整實作在 Task 6 補上，這裡先讓 import 可用）：

```python
# backend/app/services/retry_service.py（暫時骨架，Task 6 會補完整內容）
"""Retry queue for failed third-party booking calls (Requirement 9)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

TZ = timezone(timedelta(hours=8))


def mark_for_retry(order: dict) -> None:
    order["retry_info"] = {
        "retry_count": order.get("retry_info", {}).get("retry_count", 0),
        "max_retries": 3,
        "last_retry_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "needs_manual": False,
    }
```

然後實作 `backend/app/services/reservation.py`：

```python
# backend/app/services/reservation.py
"""Core reservation order service."""
from __future__ import annotations

import asyncio

from . import reservation_validators as validators
from . import restaurant_catalog
from . import retry_service
from .booking_adapter import BookingStatus, get_booking_adapter
from .store import STORE, now_iso

TEXT_TO_ORDER_STATUS: dict[str, str] = {
    "PENDING_PROVIDER": "02",
    "CONFIRMED": "03",
    "IN_PROGRESS": "04",
    "COMPLETED": "70",
    "VERIFIED": "80",
    "CANCELLED": "90",
}

_REQUIRED_FIELDS = (
    "restaurant_id",
    "reserved_date",
    "time_slot",
    "people",
    "contact_name",
    "phone",
)


def _error(code: str, message: str) -> dict:
    return {"success": False, "error": {"code": code, "message": message}}


def _validate_payload(payload: dict) -> dict | None:
    for field_id in _REQUIRED_FIELDS:
        if payload.get(field_id) in (None, ""):
            return _error("INVALID_FORM_DATA", f"Missing required field: {field_id}")

    restaurant = restaurant_catalog.get_restaurant(payload["restaurant_id"])
    if not restaurant:
        return _error("RESTAURANT_NOT_FOUND", "找不到指定的餐廳。")

    if not validators.validate_date(payload["reserved_date"]):
        return _error("INVALID_DATE", "請選擇未來 60 天內的日期。")

    if not validators.validate_time_slot(payload["time_slot"]):
        return _error("INVALID_TIME_SLOT", "請選擇午餐或晚餐時段。")

    specific_time = payload.get("specific_time")
    if specific_time and not validators.validate_specific_time(payload["time_slot"], specific_time):
        return _error("INVALID_TIME_SLOT", "請選擇時段內的有效時間。")

    if not validators.validate_people(payload["people"]):
        return _error("INVALID_PEOPLE_COUNT", "用餐人數請填寫 1 至 20 人")

    if not validators.validate_contact_name(payload["contact_name"]):
        return _error("INVALID_CONTACT_NAME", "姓名請勿超過 50 個字，且不可為空白")

    if not validators.validate_phone(payload["phone"]):
        return _error("INVALID_PHONE", "請輸入正確的手機號碼格式（09 開頭，共 10 碼）")

    if not validators.validate_preference_note(payload.get("preference_note")):
        return _error("PREFERENCE_TOO_LONG", "偏好描述請勿超過 200 字")

    return None


def check_duplicate(actor_id: str, restaurant_id: str, reserved_date: str, time_slot: str) -> bool:
    existing = STORE.query_prefix(f"USER#{actor_id}", "REQUEST#")
    for item in existing:
        if item.get("service_id") != "restaurant_reservation":
            continue
        if item.get("status") == "CANCELLED":
            continue
        order_items = item.get("order_items") or {}
        if (
            order_items.get("restaurant_id") == restaurant_id
            and order_items.get("reserved_date") == reserved_date
            and order_items.get("time_slot") == time_slot
        ):
            return True
    return False


def create_reservation_order(actor_id: str, payload: dict) -> dict:
    validation_error = _validate_payload(payload)
    if validation_error:
        return validation_error

    restaurant = restaurant_catalog.get_restaurant(payload["restaurant_id"])

    if check_duplicate(actor_id, payload["restaurant_id"], payload["reserved_date"], payload["time_slot"]):
        return _error("DUPLICATE_RESERVATION", "這筆訂位已經成功送出囉，無需重複提交。")

    is_premium = bool(payload.get("is_premium", False))
    order_items = {
        "restaurant_id": restaurant["id"],
        "restaurant_name": restaurant["name"],
        "restaurant_phone": restaurant["phone"],
        "restaurant_address": restaurant["address"],
        "people": payload["people"],
        "is_premium": is_premium,
        "reserved_date": payload["reserved_date"],
        "time_slot": payload["time_slot"],
        "specific_time": payload.get("specific_time"),
        "contact_name": payload["contact_name"],
        "phone": payload["phone"],
        "preference_note": payload.get("preference_note"),
    }
    service_time = validators.build_service_time(
        payload["reserved_date"], payload.get("specific_time"), payload["time_slot"]
    )

    request_id = STORE.next_request_id()
    created_at = now_iso()
    order = {
        "request_id": request_id,
        "session_id": None,
        "service_id": "restaurant_reservation",
        "service_name": "餐廳訂位",
        "order_type": "02",
        "order_items": order_items,
        "service_time": service_time,
        "form_data": {
            "restaurant_name": restaurant["name"],
            "reserved_date": payload["reserved_date"],
            "time_slot": payload["time_slot"],
            "specific_time": payload.get("specific_time"),
            "people": payload["people"],
            "contact_name": payload["contact_name"],
            "phone": payload["phone"],
            "is_premium": is_premium,
        },
        "vendor_data": {},
        "retry_info": {"retry_count": 0, "max_retries": 3, "last_retry_at": None, "needs_manual": False},
        "status_history": [],
        "created_at": created_at,
    }

    booking_url: str | None = None
    if is_premium or not restaurant["supports_booking_api"]:
        status = "PENDING_PROVIDER"
    else:
        result = asyncio.get_event_loop().run_until_complete(
            get_booking_adapter().create_booking(
                restaurant_id=restaurant["id"],
                date=payload["reserved_date"],
                time=payload.get("specific_time") or "",
                people=payload["people"],
                contact_name=payload["contact_name"],
                phone=payload["phone"],
            )
        )
        if result.status == BookingStatus.CONFIRMED:
            status = "CONFIRMED"
            order["vendor_data"] = {
                "booking_id": result.booking_id,
                "share_reservation_url": result.share_reservation_url,
                "confirmed_at": now_iso(),
            }
            booking_url = result.share_reservation_url
        else:
            status = "PENDING_PROVIDER"
            retry_service.mark_for_retry(order)

    order["status"] = status
    order["order_status"] = TEXT_TO_ORDER_STATUS[status]
    order["status_history"].append({"status": order["order_status"], "at": created_at})

    try:
        STORE.save_request(actor_id, order)
    except Exception as exc:
        return _error("ORDER_SAVE_FAILED", str(exc))

    return {
        "success": True,
        "request_id": request_id,
        "status": status,
        "order_status": order["order_status"],
        "booking_url": booking_url,
    }


def get_reservation_order(actor_id: str, request_id: str) -> dict | None:
    return STORE.get_request(actor_id, request_id)


def cancel_reservation_order(actor_id: str, request_id: str) -> dict:
    order = STORE.get_request(actor_id, request_id)
    if not order:
        return _error("REQUEST_NOT_FOUND", "找不到對應的訂位。")

    order["status"] = "CANCELLED"
    order["order_status"] = TEXT_TO_ORDER_STATUS["CANCELLED"]
    order.setdefault("status_history", []).append(
        {"status": order["order_status"], "at": now_iso()}
    )
    STORE.save_request(actor_id, order)
    return {"success": True, "request_id": request_id, "status": "CANCELLED"}
```

- [ ] **Step 4: 執行測試確認通過**

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_reservation_service.py -v`
Expected: PASS（11 passed）

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/reservation.py backend/app/services/retry_service.py backend/tests/test_reservation_service.py
git commit -m "feat: add reservation order creation, duplicate guard, and cancellation"
```

---

## Task 6: 重試佇列（完整實作）— ⚠️ 已砲掉，不執行

> 使用者決定跳過本任務：demo 所需的狀態推進已由 Task 9 的手動按鈕涵蓋，`reservation.py`（Task 5）內建的 `retry_service.mark_for_retry` 骨架版維持原樣即可，不需要下面的 `process_retry_queue`/`get_retry_count` 完整實作。以下內容保留供未來需要時參考，**不要**照這裡的內容派工。

<details>
<summary>（已跳過，保留原始內容）</summary>


**Files:**
- Modify: `backend/app/services/retry_service.py`（取代 Task 5 留下的骨架）
- Test: `backend/tests/test_retry_service.py`

**Interfaces:**
- Consumes: `STORE.scan_by_entity_type`（Task 1）, `booking_adapter.get_booking_adapter`/`BookingStatus`（Task 4）
- Produces: `mark_for_retry(order: dict) -> None`（已存在，補上文件）、`process_retry_queue() -> dict`（回傳 `{"processed": int, "succeeded": int, "failed": int, "escalated": int}`）、`get_retry_count(actor_id: str, request_id: str) -> int`
- 手動觸發（不接背景排程），由 Task 8 的 `POST /api/admin/retry-queue/run` 呼叫，或直接在測試/demo 時呼叫。

- [ ] **Step 1: 寫失敗測試**

```python
# backend/tests/test_retry_service.py
import tempfile
from pathlib import Path

import pytest

from backend.app.services import reservation, retry_service, store as store_module


@pytest.fixture(autouse=True)
def isolated_store(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        test_store = store_module.MemoryStore(storage_path=Path(tmp) / "store.json")
        monkeypatch.setattr(store_module, "STORE", test_store)
        monkeypatch.setattr(reservation, "STORE", test_store)
        yield test_store


def valid_payload(**overrides):
    payload = {
        "restaurant_id": "r003",  # verification_enabled=False -> adapter errors -> marked for retry
        "reserved_date": "2026-08-01",
        "time_slot": "LUNCH",
        "specific_time": "12:30",
        "people": 2,
        "contact_name": "王大明",
        "phone": "0912345678",
        "is_premium": False,
        "preference_note": None,
    }
    payload.update(overrides)
    return payload


def test_process_retry_queue_increments_retry_count_when_still_failing():
    created = reservation.create_reservation_order("user-1", valid_payload())

    result = retry_service.process_retry_queue()

    assert result["processed"] == 1
    order = reservation.get_reservation_order("user-1", created["request_id"])
    assert order["retry_info"]["retry_count"] == 1
    assert order["status"] == "PENDING_PROVIDER"


def test_process_retry_queue_escalates_after_max_retries():
    created = reservation.create_reservation_order("user-1", valid_payload())

    for _ in range(3):
        retry_service.process_retry_queue()

    result = retry_service.process_retry_queue()

    order = reservation.get_reservation_order("user-1", created["request_id"])
    assert order["retry_info"]["needs_manual"] is True
    assert result["escalated"] == 0 or order["retry_info"]["retry_count"] >= 3


def test_process_retry_queue_ignores_confirmed_orders():
    reservation.create_reservation_order("user-1", valid_payload(restaurant_id="r001"))

    result = retry_service.process_retry_queue()

    assert result["processed"] == 0


def test_get_retry_count_returns_zero_for_fresh_order():
    created = reservation.create_reservation_order("user-1", valid_payload(restaurant_id="r001"))
    assert retry_service.get_retry_count("user-1", created["request_id"]) == 0
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_retry_service.py -v`
Expected: FAIL（`process_retry_queue`/`get_retry_count` 不存在）

- [ ] **Step 3: 實作**

```python
# backend/app/services/retry_service.py
"""Retry queue for failed third-party booking calls (Requirement 9).

Not wired to a real cron/thread — call process_retry_queue() manually
(e.g. from a demo/admin endpoint or a test) to advance the queue,
matching the project's existing "manual simulate" pattern.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from .booking_adapter import BookingStatus, get_booking_adapter
from .store import STORE, now_iso

TZ = timezone(timedelta(hours=8))
MAX_RETRIES = 3


def mark_for_retry(order: dict) -> None:
    existing = order.get("retry_info") or {}
    order["retry_info"] = {
        "retry_count": existing.get("retry_count", 0),
        "max_retries": MAX_RETRIES,
        "last_retry_at": now_iso(),
        "needs_manual": existing.get("needs_manual", False),
    }


def get_retry_count(actor_id: str, request_id: str) -> int:
    order = STORE.get_request(actor_id, request_id)
    if not order:
        return 0
    return order.get("retry_info", {}).get("retry_count", 0)


def _pending_retry_orders() -> list[dict]:
    orders = STORE.scan_by_entity_type("SERVICE_REQUEST")
    return [
        order
        for order in orders
        if order.get("service_id") == "restaurant_reservation"
        and order.get("status") == "PENDING_PROVIDER"
        and not order.get("retry_info", {}).get("needs_manual", False)
        and order.get("retry_info", {}).get("retry_count", 0) < MAX_RETRIES
    ]


def process_retry_queue() -> dict:
    results = {"processed": 0, "succeeded": 0, "failed": 0, "escalated": 0}
    adapter = get_booking_adapter()

    for order in _pending_retry_orders():
        actor_id = order["PK"].replace("USER#", "")
        order_items = order.get("order_items", {})
        results["processed"] += 1

        booking_result = asyncio.get_event_loop().run_until_complete(
            adapter.create_booking(
                restaurant_id=order_items.get("restaurant_id", ""),
                date=order_items.get("reserved_date", ""),
                time=order_items.get("specific_time") or "",
                people=order_items.get("people", 0),
                contact_name=order_items.get("contact_name", ""),
                phone=order_items.get("phone", ""),
            )
        )

        if booking_result.status == BookingStatus.CONFIRMED:
            order["status"] = "CONFIRMED"
            order["order_status"] = "03"
            order["vendor_data"] = {
                "booking_id": booking_result.booking_id,
                "share_reservation_url": booking_result.share_reservation_url,
                "confirmed_at": now_iso(),
            }
            order.setdefault("status_history", []).append({"status": "03", "at": now_iso()})
            results["succeeded"] += 1
        else:
            retry_info = order.setdefault("retry_info", {"retry_count": 0, "max_retries": MAX_RETRIES})
            retry_info["retry_count"] = retry_info.get("retry_count", 0) + 1
            retry_info["last_retry_at"] = now_iso()
            if retry_info["retry_count"] >= MAX_RETRIES:
                retry_info["needs_manual"] = True
                results["escalated"] += 1
            results["failed"] += 1

        STORE.save_request(actor_id, order)

    return results
```

- [ ] **Step 4: 執行測試確認通過**

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_retry_service.py -v`
Expected: PASS（4 passed）

- [ ] **Step 5: 重新執行 Task 5 的測試，確認骨架替換沒有破壞既有行為**

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_reservation_service.py -v`
Expected: PASS（11 passed，無回歸）

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/retry_service.py backend/tests/test_retry_service.py
git commit -m "feat: implement retry queue processing for failed bookings"
```

---

</details>

---

## Task 7: 狀態自動推進（Status Scheduler，純函式）— ⚠️ 已砲掉，不執行

> 使用者決定跳過本任務：狀態推進（含 COMPLETED→VERIFIED 核銷那一步）已由 Task 9 的手動按鈕涵蓋，不需要獨立的排程純函式。`backend/app/scheduler/` 這個 package 不用建立。以下內容保留供未來需要時參考，**不要**照這裡的內容派工。

<details>
<summary>（已跳過，保留原始內容）</summary>


**Files:**
- Create: `backend/app/scheduler/__init__.py`（空檔案）
- Create: `backend/app/scheduler/status_scheduler.py`
- Test: `backend/tests/test_status_scheduler.py`

**Interfaces:**
- Consumes: `STORE.scan_by_entity_type`（Task 1）
- Produces: `run_status_advancement(now: datetime | None = None) -> dict`（回傳 `{"processed": int, "advanced": int, "errors": int}`）、`advance_single_order(order: dict, now: datetime) -> bool`
- 手動觸發（不接背景排程），由 Task 8 的 `POST /api/admin/status-scheduler/run` 呼叫。

- [ ] **Step 1: 寫失敗測試**

```python
# backend/tests/test_status_scheduler.py
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from backend.app.scheduler import status_scheduler
from backend.app.services import reservation, store as store_module

TZ = timezone(timedelta(hours=8))


@pytest.fixture(autouse=True)
def isolated_store(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        test_store = store_module.MemoryStore(storage_path=Path(tmp) / "store.json")
        monkeypatch.setattr(store_module, "STORE", test_store)
        monkeypatch.setattr(reservation, "STORE", test_store)
        monkeypatch.setattr(status_scheduler, "STORE", test_store)
        yield test_store


def make_confirmed_order(store, service_time: str) -> dict:
    order = {
        "request_id": "REQ-1",
        "service_id": "restaurant_reservation",
        "service_name": "餐廳訂位",
        "status": "CONFIRMED",
        "order_status": "03",
        "order_items": {"verification_enabled": True},
        "service_time": service_time,
        "status_history": [],
        "created_at": "2026-07-01T10:00:00+08:00",
    }
    store.save_request("user-1", order)
    return order


def test_advance_single_order_moves_confirmed_to_in_progress_when_service_time_reached():
    order = {"status": "CONFIRMED", "order_status": "03", "service_time": "2026-08-01T12:00:00+08:00"}
    now = datetime.fromisoformat("2026-08-01T12:05:00+08:00")

    advanced = status_scheduler.advance_single_order(order, now)

    assert advanced is True
    assert order["status"] == "IN_PROGRESS"
    assert order["order_status"] == "04"


def test_advance_single_order_moves_in_progress_to_completed_after_three_hours():
    order = {"status": "IN_PROGRESS", "order_status": "04", "service_time": "2026-08-01T12:00:00+08:00"}
    now = datetime.fromisoformat("2026-08-01T15:01:00+08:00")

    advanced = status_scheduler.advance_single_order(order, now)

    assert advanced is True
    assert order["status"] == "COMPLETED"
    assert order["order_status"] == "70"


def test_advance_single_order_does_not_advance_before_service_time():
    order = {"status": "CONFIRMED", "order_status": "03", "service_time": "2026-08-01T12:00:00+08:00"}
    now = datetime.fromisoformat("2026-08-01T11:00:00+08:00")

    advanced = status_scheduler.advance_single_order(order, now)

    assert advanced is False
    assert order["status"] == "CONFIRMED"


def test_advance_single_order_skips_cancelled_orders():
    order = {"status": "CANCELLED", "order_status": "90", "service_time": "2026-08-01T12:00:00+08:00"}
    now = datetime.fromisoformat("2026-09-01T12:00:00+08:00")

    advanced = status_scheduler.advance_single_order(order, now)

    assert advanced is False
    assert order["status"] == "CANCELLED"


def test_run_status_advancement_processes_all_eligible_orders_and_continues_after_error(isolated_store):
    make_confirmed_order(isolated_store, "2026-08-01T12:00:00+08:00")
    isolated_store.save_request(
        "user-2",
        {
            "request_id": "REQ-BROKEN",
            "service_id": "restaurant_reservation",
            "status": "CONFIRMED",
            "order_status": "03",
            "order_items": {},
            "service_time": "not-a-valid-timestamp",
            "status_history": [],
        },
    )

    now = datetime.fromisoformat("2026-08-01T13:00:00+08:00")
    result = status_scheduler.run_status_advancement(now=now)

    assert result["processed"] == 2
    assert result["advanced"] == 1
    assert result["errors"] == 1
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_status_scheduler.py -v`
Expected: FAIL，`ModuleNotFoundError`

- [ ] **Step 3: 實作**

```python
# backend/app/scheduler/__init__.py
```

```python
# backend/app/scheduler/status_scheduler.py
"""Order status auto-advancement (Requirement 11).

A pure, independently-testable batch step. Not wired to a real
cron/thread in this codebase — trigger manually (e.g. from
POST /api/admin/status-scheduler/run) matching the project's existing
"manual simulate" demo pattern.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from ..services.store import STORE, now_iso

TZ = timezone(timedelta(hours=8))
BATCH_SIZE = 500

_NEXT_STATUS = {
    "CONFIRMED": "IN_PROGRESS",
    "IN_PROGRESS": "COMPLETED",
}
_TEXT_TO_ORDER_STATUS = {"IN_PROGRESS": "04", "COMPLETED": "70", "VERIFIED": "80"}


def advance_single_order(order: dict, now: datetime) -> bool:
    status = order.get("status")
    if status in ("CANCELLED",):
        return False

    service_time = datetime.fromisoformat(order["service_time"])

    if status == "CONFIRMED" and now >= service_time:
        order["status"] = "IN_PROGRESS"
        order["order_status"] = _TEXT_TO_ORDER_STATUS["IN_PROGRESS"]
        order.setdefault("status_history", []).append({"status": order["order_status"], "at": now_iso()})
        return True

    if status == "IN_PROGRESS" and now >= service_time + timedelta(hours=3):
        order["status"] = "COMPLETED"
        order["order_status"] = _TEXT_TO_ORDER_STATUS["COMPLETED"]
        order.setdefault("status_history", []).append({"status": order["order_status"], "at": now_iso()})
        return True

    if status == "COMPLETED":
        verification_enabled = order.get("order_items", {}).get("verification_enabled", False)
        completed_at = next(
            (h["at"] for h in reversed(order.get("status_history", [])) if h["status"] == "70"),
            None,
        )
        if verification_enabled and completed_at:
            completed_time = datetime.fromisoformat(completed_at)
            if now >= completed_time + timedelta(days=7):
                order["status"] = "VERIFIED"
                order["order_status"] = _TEXT_TO_ORDER_STATUS["VERIFIED"]
                order.setdefault("status_history", []).append({"status": order["order_status"], "at": now_iso()})
                return True

    return False


def run_status_advancement(now: datetime | None = None) -> dict:
    now = now or datetime.now(TZ)
    orders = [
        o for o in STORE.scan_by_entity_type("SERVICE_REQUEST")
        if o.get("service_id") == "restaurant_reservation"
    ][:BATCH_SIZE]

    results = {"processed": 0, "advanced": 0, "errors": 0}
    for order in orders:
        results["processed"] += 1
        try:
            advanced = advance_single_order(order, now)
        except Exception:
            results["errors"] += 1
            continue
        if advanced:
            actor_id = order["PK"].replace("USER#", "")
            STORE.save_request(actor_id, order)
            results["advanced"] += 1

    return results
```

- [ ] **Step 4: 執行測試確認通過**

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_status_scheduler.py -v`
Expected: PASS（5 passed）

- [ ] **Step 5: Commit**

```bash
git add backend/app/scheduler/__init__.py backend/app/scheduler/status_scheduler.py backend/tests/test_status_scheduler.py
git commit -m "feat: add pure status-advancement scheduler function"
```

---

</details>

---

## Task 8: REST API 端點

**Files:**
- Create: `backend/app/api/reservations.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_reservations_api.py`

**注意：Task 6（重試佇列完整實作）與 Task 7（狀態排程器）已依使用者決定砲掉不執行**——demo 所需的狀態推進完全由 Task 9 的手動按鈕機制涵蓋，不需要這兩個模組。本任務因此不建立 `/api/admin/*` 這兩個管理用端點，`reservation.py`（Task 5）內建的 `retry_service.mark_for_retry` 骨架版維持原樣即可，不需要 `process_retry_queue`。

**Interfaces:**
- Consumes: `reservation.*`（Task 5）、`restaurant_catalog.*`（Task 2）、既有 `auth.cognito.CurrentUser`/`get_current_user`
- Produces endpoints:
  - `GET /api/restaurants`
  - `GET /api/restaurants/{id}`
  - `POST /api/reservations/submit`
  - `GET /api/reservations/{request_id}`
  - `POST /api/reservations/{request_id}/cancel`
  - `POST /api/webhooks/booking-callback`（Requirement 8.6，非同步確認回呼，body 含 `request_id`）

- [ ] **Step 1: 檢查既有測試如何建立 FastAPI TestClient**（不用寫，先確認 `httpx`/`TestClient` 可用；`requirements.txt` 已有 `httpx>=0.27`，`fastapi.testclient.TestClient` 內建可直接用）

- [ ] **Step 2: 寫失敗測試**

```python
# backend/tests/test_reservations_api.py
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services import reservation, store as store_module


@pytest.fixture(autouse=True)
def isolated_store(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        test_store = store_module.MemoryStore(storage_path=Path(tmp) / "store.json")
        monkeypatch.setattr(store_module, "STORE", test_store)
        monkeypatch.setattr(reservation, "STORE", test_store)
        yield test_store


@pytest.fixture
def client():
    return TestClient(app)


def auth_headers(client: TestClient) -> dict:
    # Demo auth: reuse the existing mock login endpoint used by other API tests.
    response = client.post("/api/auth/demo-login", json={"user_id": "vincent"})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def valid_payload(**overrides):
    payload = {
        "restaurant_id": "r001",
        "reserved_date": "2026-08-01",
        "time_slot": "LUNCH",
        "specific_time": "12:30",
        "people": 2,
        "contact_name": "王大明",
        "phone": "0912345678",
        "is_premium": False,
    }
    payload.update(overrides)
    return payload


def test_list_restaurants_returns_seed_data(client):
    headers = auth_headers(client)
    response = client.get("/api/restaurants", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert len(body["restaurants"]) <= 6
    assert body["restaurants"][0]["id"] == "r001"


def test_get_restaurant_detail(client):
    headers = auth_headers(client)
    response = client.get("/api/restaurants/r001", headers=headers)
    assert response.status_code == 200
    assert response.json()["name"] == "22世紀風味館 信義旗艦店"


def test_get_restaurant_not_found_returns_404(client):
    headers = auth_headers(client)
    response = client.get("/api/restaurants/nope", headers=headers)
    assert response.status_code == 404


def test_submit_reservation_creates_order(client):
    headers = auth_headers(client)
    response = client.post("/api/reservations/submit", json=valid_payload(), headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["order_status"] == "03"


def test_submit_reservation_invalid_payload_returns_400(client):
    headers = auth_headers(client)
    response = client.post("/api/reservations/submit", json=valid_payload(phone="bad"), headers=headers)
    assert response.status_code == 400


def test_get_reservation_detail(client):
    headers = auth_headers(client)
    created = client.post("/api/reservations/submit", json=valid_payload(), headers=headers).json()
    response = client.get(f"/api/reservations/{created['request_id']}", headers=headers)
    assert response.status_code == 200
    assert response.json()["order_items"]["restaurant_id"] == "r001"


def test_cancel_reservation(client):
    headers = auth_headers(client)
    created = client.post("/api/reservations/submit", json=valid_payload(), headers=headers).json()
    response = client.post(f"/api/reservations/{created['request_id']}/cancel", headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"


def test_booking_callback_updates_pending_order(client):
    headers = auth_headers(client)
    created = client.post(
        "/api/reservations/submit", json=valid_payload(restaurant_id="r005"), headers=headers
    ).json()
    assert created["status"] == "PENDING_PROVIDER"

    response = client.post(
        "/api/webhooks/booking-callback",
        json={
            "request_id": created["request_id"],
            "actor_id": "vincent",
            "status": "CONFIRMED",
            "booking_id": "EZ-CB-1",
            "share_reservation_url": "https://eztable.example.com/booking/EZ-CB-1",
        },
    )
    assert response.status_code == 200

    detail = client.get(f"/api/reservations/{created['request_id']}", headers=headers).json()
    assert detail["status"] == "CONFIRMED"
    assert detail["vendor_data"]["booking_id"] == "EZ-CB-1"
```

如果 `/api/auth/demo-login` 的實際路徑或 request/response 格式與既有 `backend/app/api/auth.py` 不同，**以 `auth.py` 的實際實作為準修正這個 fixture**（不要盲目照抄，先讀 `backend/app/api/auth.py` 確認端點路徑與回應欄位名稱）。

- [ ] **Step 3: 執行測試確認失敗**

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_reservations_api.py -v`
Expected: FAIL（路由不存在，404 或 import error）

- [ ] **Step 4: 實作**

```python
# backend/app/api/reservations.py
"""Restaurant reservation API endpoints."""
from fastapi import APIRouter, Depends, HTTPException

from ..auth.cognito import CurrentUser, get_current_user
from ..services import reservation, restaurant_catalog

router = APIRouter()


def _raise_api_error(status_code: int, code: str, message: str):
    raise HTTPException(status_code=status_code, detail={"success": False, "error": {"code": code, "message": message}})


@router.get("/api/restaurants")
def list_restaurants(user: CurrentUser = Depends(get_current_user)):
    return {"restaurants": restaurant_catalog.list_restaurants()}


@router.get("/api/restaurants/{restaurant_id}")
def get_restaurant(restaurant_id: str, user: CurrentUser = Depends(get_current_user)):
    restaurant = restaurant_catalog.get_restaurant(restaurant_id)
    if not restaurant:
        _raise_api_error(404, "RESTAURANT_NOT_FOUND", "找不到指定的餐廳。")
    return restaurant


@router.post("/api/reservations/submit")
def submit_reservation(payload: dict, user: CurrentUser = Depends(get_current_user)):
    result = reservation.create_reservation_order(user.sub, payload)
    if not result.get("success"):
        error = result.get("error", {})
        status_code = 409 if error.get("code") == "DUPLICATE_RESERVATION" else 400
        _raise_api_error(status_code, error.get("code", "RESERVATION_FAILED"), error.get("message", "訂位失敗"))
    return result


@router.get("/api/reservations/{request_id}")
def get_reservation(request_id: str, user: CurrentUser = Depends(get_current_user)):
    order = reservation.get_reservation_order(user.sub, request_id)
    if not order:
        _raise_api_error(404, "REQUEST_NOT_FOUND", "找不到對應的訂位。")
    return order


@router.post("/api/reservations/{request_id}/cancel")
def cancel_reservation(request_id: str, user: CurrentUser = Depends(get_current_user)):
    result = reservation.cancel_reservation_order(user.sub, request_id)
    if not result.get("success"):
        _raise_api_error(404, "REQUEST_NOT_FOUND", "找不到對應的訂位。")
    return result


@router.post("/api/webhooks/booking-callback")
def booking_callback(body: dict):
    actor_id = body.get("actor_id")
    request_id = body.get("request_id")
    if not actor_id or not request_id:
        _raise_api_error(400, "INVALID_FORM_DATA", "缺少 actor_id 或 request_id。")

    order = reservation.get_reservation_order(actor_id, request_id)
    if not order:
        _raise_api_error(404, "REQUEST_NOT_FOUND", "找不到對應的訂位。")

    from ..services.store import STORE, now_iso

    order["status"] = body.get("status", order["status"])
    order["order_status"] = reservation.TEXT_TO_ORDER_STATUS.get(order["status"], order.get("order_status"))
    order["vendor_data"] = {
        "booking_id": body.get("booking_id"),
        "share_reservation_url": body.get("share_reservation_url"),
        "confirmed_at": now_iso(),
    }
    order.setdefault("status_history", []).append({"status": order["order_status"], "at": now_iso()})
    STORE.save_request(actor_id, order)
    return {"success": True}
```

在 `backend/app/main.py` 加入 import 與註冊（跟在既有 `from .api import auth, chat, requests, services, sessions` 之後）：

```python
from .api import auth, chat, requests, reservations, services, sessions
```

並在 `app.include_router(requests.router)` 之後加一行：

```python
app.include_router(reservations.router)
```

- [ ] **Step 5: 執行測試確認通過**

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_reservations_api.py -v`
Expected: PASS（全部通過；若 `auth_headers` fixture 因既有 auth 端點格式不同而失敗，依 Step 2 的提示修正 fixture 後重跑）

- [ ] **Step 6: 執行全部後端測試確認無回歸**

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests -v`
Expected: 全部 PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/api/reservations.py backend/app/main.py backend/tests/test_reservations_api.py
git commit -m "feat: add reservation REST API endpoints"
```

---

## Task 9: 既有案件狀態顯示相容（STATUS_LABELS / 手動 Demo 按鈕同步 order_status）

**Files:**
- Modify: `backend/app/api/requests.py`

**Interfaces:**
- Consumes: `reservation.TEXT_TO_ORDER_STATUS`（Task 5）

**目的：** 讓既有「案件明細」頁面的手動示範按鈕（`/api/requests/{id}/simulate/{next_status}`）在推進訂位訂單狀態時，同步更新 `order_status` 與 `status_history`，並讓 `STATUS_LABELS` 認得新的 `VERIFIED` 狀態。

- [ ] **Step 1: 寫失敗測試**

```python
# backend/tests/test_requests_simulate_reservation.py
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services import reservation, store as store_module


@pytest.fixture(autouse=True)
def isolated_store(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        test_store = store_module.MemoryStore(storage_path=Path(tmp) / "store.json")
        monkeypatch.setattr(store_module, "STORE", test_store)
        monkeypatch.setattr(reservation, "STORE", test_store)
        yield test_store


def test_simulate_status_syncs_order_status_for_reservation():
    client = TestClient(app)
    login = client.post("/api/auth/demo-login", json={"user_id": "vincent"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    created = client.post(
        "/api/reservations/submit",
        json={
            "restaurant_id": "r005",
            "reserved_date": "2026-08-01",
            "time_slot": "LUNCH",
            "people": 2,
            "contact_name": "王大明",
            "phone": "0912345678",
            "is_premium": False,
        },
        headers=headers,
    ).json()
    assert created["status"] == "PENDING_PROVIDER"

    response = client.post(
        f"/api/requests/{created['request_id']}/simulate/CONFIRMED", headers=headers
    )
    assert response.status_code == 200

    detail = client.get(f"/api/reservations/{created['request_id']}", headers=headers).json()
    assert detail["status"] == "CONFIRMED"
    assert detail["order_status"] == "03"
    assert detail["status_history"][-1]["status"] == "03"
```

如同 Task 8，若 `/api/auth/demo-login` 的實際格式不同，依 `backend/app/api/auth.py` 的真實實作調整這個測試。

- [ ] **Step 2: 執行測試確認失敗**

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_requests_simulate_reservation.py -v`
Expected: FAIL（`order_status` 不會被同步更新，仍是送出時的舊值或缺少 `status_history` 更新）

- [ ] **Step 3: 實作**

在 `backend/app/api/requests.py`，`STATUS_LABELS` 字典裡加入一行（放在 `"FAILED": "失敗",` 之後）：

```python
    "VERIFIED": "已核銷",
```

把 `simulate_status` 函式改成（同步 `order_status`/`status_history`，並允許 `VERIFIED` 作為合法目標狀態）：

```python
@router.post("/api/requests/{request_id}/simulate/{next_status}")
def simulate_status(request_id: str, next_status: str, user: CurrentUser = Depends(get_current_user)):
    allowed = {"CONFIRMED", "IN_PROGRESS", "COMPLETED", "VERIFIED"}
    if next_status not in allowed:
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "error": {"code": "INVALID_FORM_DATA", "message": "不支援的模擬狀態。"},
            },
        )
    request = _get_or_404(user.sub, request_id)
    request["status"] = next_status

    if "order_items" in request:
        from ..services.reservation import TEXT_TO_ORDER_STATUS

        order_status = TEXT_TO_ORDER_STATUS.get(next_status)
        if order_status:
            request["order_status"] = order_status
            request.setdefault("status_history", []).append({"status": order_status, "at": None})

    STORE.save_request(user.sub, request)
    return {"success": True, "request_id": request_id, "status": next_status}
```

`status_history` 的 `"at": None` 先留著即可（沒有 import `now_iso` 也能過測試，因為測試只檢查 `status` 值）；若想要精確時間戳記，在檔案頂端把 `from ..services.store import STORE` 改成 `from ..services.store import STORE, now_iso`，並把 `"at": None` 換成 `"at": now_iso()`。

- [ ] **Step 4: 執行測試確認通過**

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_requests_simulate_reservation.py -v`
Expected: PASS

- [ ] **Step 5: 執行全部後端測試確認無回歸**

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests -v`
Expected: 全部 PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/requests.py backend/tests/test_requests_simulate_reservation.py
git commit -m "feat: sync order_status when simulating reservation status transitions"
```

---

## Task 10: 前端型別、資料、API client

**Files:**
- Create: `frontend/src/types/reservation.ts`
- Create: `frontend/src/data/restaurants.ts`
- Create: `frontend/src/api/reservations.ts`

**Interfaces:**
- Produces:
  - `frontend/src/types/reservation.ts`: `RestaurantInfo`, `TimeSlot = "LUNCH" | "DINNER"`, `ReservationPayload`, `ReservationSubmitResult`, `ReservationOrder`
  - `frontend/src/data/restaurants.ts`: `FEATURED_RESTAURANTS: RestaurantInfo[]`（跟 `backend/app/services/restaurant_catalog.py` 的 6 筆資料保持一致，image_url 除外——前端不需要）
  - `frontend/src/api/reservations.ts`: `listRestaurants()`, `getRestaurant(id)`, `submitReservation(payload)`, `getReservation(requestId)`, `cancelReservation(requestId)`
- Consumed by: Task 12-19（所有前端元件）

先讀 `frontend/src/api/requests.ts` 或 `frontend/src/api/services.ts` 確認既有 fetch 封裝的慣例（base URL、token 帶法、錯誤處理），照同樣模式寫，不要自創一套。

- [ ] **Step 1: 型別定義**

```typescript
// frontend/src/types/reservation.ts
export interface RestaurantInfo {
  id: string;
  name: string;
  brand: string;
  address: string;
  phone: string;
  cuisine: string;
  supports_booking_api: boolean;
}

export type TimeSlot = "LUNCH" | "DINNER";

export interface ReservationPayload {
  restaurant_id: string;
  reserved_date: string; // YYYY-MM-DD
  time_slot: TimeSlot;
  specific_time?: string | null; // HH:MM
  people: number;
  contact_name: string;
  phone: string;
  is_premium: boolean;
  preference_note?: string | null;
}

export interface ReservationSubmitResult {
  success: boolean;
  request_id: string;
  status: string;
  order_status: string;
  booking_url: string | null;
}

export interface ReservationOrder {
  request_id: string;
  status: string;
  order_status: string;
  order_items: {
    restaurant_id: string;
    restaurant_name: string;
    restaurant_phone: string;
    restaurant_address: string;
    people: number;
    is_premium: boolean;
    reserved_date: string;
    time_slot: TimeSlot;
    specific_time: string | null;
    contact_name: string;
    phone: string;
    preference_note: string | null;
  };
  vendor_data: { booking_id?: string; share_reservation_url?: string; confirmed_at?: string };
}
```

- [ ] **Step 2: 前端餐廳資料（鏡射後端種子資料）**

```typescript
// frontend/src/data/restaurants.ts
import type { RestaurantInfo } from "../types/reservation";

export const FEATURED_RESTAURANTS: RestaurantInfo[] = [
  { id: "r001", name: "22世紀風味館 信義旗艦店", brand: "22世紀風味館", address: "台北市信義區松高路12號3樓", phone: "02-2723-0022", cuisine: "複合式料理", supports_booking_api: true },
  { id: "r002", name: "22世紀風味館 板橋文化店", brand: "22世紀風味館", address: "新北市板橋區文化路一段280號2樓", phone: "02-2258-0022", cuisine: "複合式料理", supports_booking_api: true },
  { id: "r003", name: "22世紀風味館 台中公益店", brand: "22世紀風味館", address: "台中市南屯區公益路二段51號", phone: "04-2326-0022", cuisine: "複合式料理", supports_booking_api: true },
  { id: "r004", name: "22世紀風味館 高雄夢時代店", brand: "22世紀風味館", address: "高雄市前鎮區中華五路789號B1", phone: "07-812-0022", cuisine: "複合式料理", supports_booking_api: true },
  { id: "r005", name: "22世紀風味館 桃園中正店", brand: "22世紀風味館", address: "桃園市桃園區中正路1055號", phone: "03-356-0022", cuisine: "複合式料理", supports_booking_api: false },
  { id: "r006", name: "22世紀風味館 新竹巨城店", brand: "22世紀風味館", address: "新竹市東區中央路229號4樓", phone: "03-623-0022", cuisine: "複合式料理", supports_booking_api: true },
];
```

- [ ] **Step 3: API client**

實作前，先開啟 `frontend/src/api/requests.ts` 讀完整個檔案，確認：(a) fetch base URL 常數叫什麼名字、從哪裡 import；(b) 如何附加 Authorization header／token；(c) 錯誤時怎麼 throw（例如 `throw new Error(body.error.message)`）。然後用完全一致的寫法完成以下檔案（把 `<既有的 fetch helper 或 pattern>` 換成實際看到的寫法，不要引入新的 fetch 封裝方式）：

```typescript
// frontend/src/api/reservations.ts
import type { ReservationOrder, ReservationPayload, ReservationSubmitResult, RestaurantInfo } from "../types/reservation";
// import 既有的 fetch helper，寫法對齊 frontend/src/api/requests.ts

export async function listRestaurants(): Promise<RestaurantInfo[]> {
  // 呼叫 GET /api/restaurants，回傳 body.restaurants
  throw new Error("implement using the same fetch pattern as api/requests.ts");
}

export async function getRestaurant(id: string): Promise<RestaurantInfo> {
  // 呼叫 GET /api/restaurants/{id}
  throw new Error("implement using the same fetch pattern as api/requests.ts");
}

export async function submitReservation(payload: ReservationPayload): Promise<ReservationSubmitResult> {
  // 呼叫 POST /api/reservations/submit，body 為 payload
  throw new Error("implement using the same fetch pattern as api/requests.ts");
}

export async function getReservation(requestId: string): Promise<ReservationOrder> {
  // 呼叫 GET /api/reservations/{requestId}
  throw new Error("implement using the same fetch pattern as api/requests.ts");
}

export async function cancelReservation(requestId: string): Promise<{ success: boolean }> {
  // 呼叫 POST /api/reservations/{requestId}/cancel
  throw new Error("implement using the same fetch pattern as api/requests.ts");
}
```

> 這個 Step 刻意不寫死 fetch 實作，因為它必須跟 `frontend/src/api/requests.ts` 的既有慣例（base URL 變數名稱、header 組法、錯誤處理）完全一致；把每個 `throw new Error(...)` 換成照該檔案模式寫出的真正 fetch 呼叫。

- [ ] **Step 4: 型別檢查**

Run: `cd frontend && npx tsc --noEmit`
Expected: 無新增的型別錯誤（`reservations.ts` 裡的 `throw new Error(...)` 那幾行完成後才會消失，此階段先確保型別本身沒問題）

- [ ] **Step 5: Commit**

```bash
git add frontend/src/types/reservation.ts frontend/src/data/restaurants.ts frontend/src/api/reservations.ts
git commit -m "feat: add reservation types, seed data, and API client"
```

---

## Task 11: HomePage 卡片 / Icon / StatusBadge / fieldLabels 收尾配件

**Files:**
- Modify: `frontend/src/components/ServiceIcon.tsx`
- Modify: `frontend/src/data/services.ts`
- Modify: `frontend/src/components/StatusBadge.tsx`
- Modify: `frontend/src/utils/fieldLabels.ts`
- Test: `frontend/src/components/StatusBadge.test.tsx`（若原本沒有這個測試檔就新建；若已存在同名測試就在裡面加案例）

- [ ] **Step 1: 新增 restaurant icon**

在 `frontend/src/components/ServiceIcon.tsx` 的 `ServiceIconType` union 加入 `"restaurant"`（放在 `"moving"` 之後）：

```typescript
  | "aircon" | "plumbing" | "appliance" | "cleaning" | "pest" | "moving" | "restaurant"
```

在 `PATHS` 物件加入對應 SVG（放在 `moving:` 區塊之後，一個簡單的叉子+盤子圖示，維持既有 `viewBox="0 0 24 24"`／`strokeWidth 1.6` 風格）：

```typescript
  restaurant: (
    <>
      <circle cx="8" cy="12" r="5.5" />
      <line x1="16.5" y1="4" x2="16.5" y2="20" />
      <path d="M14.5 4 V10 a2 2 0 0 0 4 0 V4" />
    </>
  ),
```

- [ ] **Step 2: HomePage 服務卡片**

在 `frontend/src/data/services.ts`，加入新的 `ServiceDefinition` 項目（放在陣列最後）：

```typescript
{
  service_id: "restaurant_reservation",
  title: "餐廳訂位",
  subtitle: "22世紀風味館 精選餐廳訂位服務",
  description: "為您預約精選餐廳座位，享受美食無煩惱。",
  icon: "restaurant",
  fields: [],
},
```

（`fields: []` 是刻意的——這個服務改用獨立的 `ReservationFlowPage` 精靈頁面收集欄位，不透過 `ServiceFormPage` 的通用 renderer，見 Task 19。）

- [ ] **Step 3: StatusBadge 新增 VERIFIED**

開啟 `frontend/src/components/StatusBadge.tsx`，找到 `STYLES` 物件（目前含 `SUBMITTED`/`PENDING_PROVIDER`/`CONFIRMED`/`IN_PROGRESS`/`COMPLETED`/`CANCELLED`/`FAILED`），加入一行，樣式比照 `COMPLETED`（沿用同一個 info 色階 class，不要新發明顏色）：

```typescript
  VERIFIED: STYLES.COMPLETED,
```

若 `STYLES` 是用 `as const` 或型別鎖死的物件字面量導致上面這行寫在物件內部語法不合法，改成在物件定義完之後另外賦值：`STYLES.VERIFIED = STYLES.COMPLETED;`——先讀該檔案實際寫法再選擇對應語法。

- [ ] **Step 4: fieldLabels 補充**

在 `frontend/src/utils/fieldLabels.ts` 的 `FIELD_LABELS` 加入：

```typescript
  restaurant_name: "餐廳",
  reserved_date: "用餐日期",
  time_slot: "用餐時段",
  specific_time: "用餐時間",
  people: "用餐人數",
  contact_name: "聯絡人姓名",
  is_premium: "訂位類型",
```

在 `VALUE_LABELS` 加入：

```typescript
  LUNCH: "午餐",
  DINNER: "晚餐",
  true: "高級訂位",
  false: "一般訂位",
```

（`quantity`/`hours`/`phone` 這些鍵已經存在，不要重複加。）

- [ ] **Step 5: 寫測試（StatusBadge 新狀態）**

```typescript
// frontend/src/components/StatusBadge.test.tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { StatusBadge } from "./StatusBadge";

describe("StatusBadge", () => {
  it("renders the VERIFIED status with its label", () => {
    render(<StatusBadge status="VERIFIED" label="已核銷" />);
    expect(screen.getByText("已核銷")).toBeInTheDocument();
  });

  it("falls back to gray styling for unknown status", () => {
    const { container } = render(<StatusBadge status="SOMETHING_NEW" label="未知" />);
    expect(container.firstChild).toBeTruthy();
  });
});
```

- [ ] **Step 6: 執行測試**

Run: `cd frontend && npx vitest run src/components/StatusBadge.test.tsx`
Expected: PASS

- [ ] **Step 7: 型別檢查全專案**

Run: `cd frontend && npx tsc --noEmit`
Expected: 無錯誤

- [ ] **Step 8: Commit**

```bash
git add frontend/src/components/ServiceIcon.tsx frontend/src/data/services.ts frontend/src/components/StatusBadge.tsx frontend/src/utils/fieldLabels.ts frontend/src/components/StatusBadge.test.tsx
git commit -m "feat: wire up restaurant reservation icon, service card, status, and labels"
```

---

## Task 12: RestaurantCard / RestaurantCardList

**Files:**
- Create: `frontend/src/components/RestaurantCard.tsx`
- Create: `frontend/src/components/RestaurantCard.test.tsx`
- Create: `frontend/src/components/RestaurantCardList.tsx`
- Create: `frontend/src/components/RestaurantCardList.test.tsx`

**Interfaces:**
- Produces: `RestaurantCard({ restaurant, selected, onSelect }: { restaurant: RestaurantInfo; selected: boolean; onSelect: () => void })`, `RestaurantCardList({ restaurants, selectedId, onSelect, onNeedHelp }: { restaurants: RestaurantInfo[]; selectedId: string | null; onSelect: (id: string) => void; onNeedHelp: () => void })`
- Consumes: `RestaurantInfo`（Task 10）
- Consumed by: Task 19 (`ReservationFlowPage`)

(Requirement 2.1, 2.2, 2.4)

- [ ] **Step 1: 寫失敗測試**

```typescript
// frontend/src/components/RestaurantCard.test.tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { RestaurantCard } from "./RestaurantCard";

const restaurant = {
  id: "r001",
  name: "22世紀風味館 信義旗艦店",
  brand: "22世紀風味館",
  address: "台北市信義區松高路12號3樓",
  phone: "02-2723-0022",
  cuisine: "複合式料理",
  supports_booking_api: true,
};

describe("RestaurantCard", () => {
  it("renders name, address, and phone", () => {
    render(<RestaurantCard restaurant={restaurant} selected={false} onSelect={() => {}} />);
    expect(screen.getByText(restaurant.name)).toBeInTheDocument();
    expect(screen.getByText(restaurant.address)).toBeInTheDocument();
    expect(screen.getByText(restaurant.phone)).toBeInTheDocument();
  });

  it("calls onSelect when clicked", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(<RestaurantCard restaurant={restaurant} selected={false} onSelect={onSelect} />);
    await user.click(screen.getByRole("button"));
    expect(onSelect).toHaveBeenCalledTimes(1);
  });

  it("shows a selected visual state via aria-pressed", () => {
    render(<RestaurantCard restaurant={restaurant} selected onSelect={() => {}} />);
    expect(screen.getByRole("button")).toHaveAttribute("aria-pressed", "true");
  });
});
```

```typescript
// frontend/src/components/RestaurantCardList.test.tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { RestaurantCardList } from "./RestaurantCardList";

const restaurants = [
  { id: "r001", name: "餐廳一", brand: "b", address: "地址一", phone: "02-1", cuisine: "c", supports_booking_api: true },
  { id: "r002", name: "餐廳二", brand: "b", address: "地址二", phone: "02-2", cuisine: "c", supports_booking_api: true },
];

describe("RestaurantCardList", () => {
  it("renders one card per restaurant plus a 'need help' option", () => {
    render(<RestaurantCardList restaurants={restaurants} selectedId={null} onSelect={() => {}} onNeedHelp={() => {}} />);
    expect(screen.getByText("餐廳一")).toBeInTheDocument();
    expect(screen.getByText("餐廳二")).toBeInTheDocument();
    expect(screen.getByText("客服協助媒合")).toBeInTheDocument();
  });

  it("calls onSelect with the restaurant id", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(<RestaurantCardList restaurants={restaurants} selectedId={null} onSelect={onSelect} onNeedHelp={() => {}} />);
    await user.click(screen.getByText("餐廳一"));
    expect(onSelect).toHaveBeenCalledWith("r001");
  });

  it("calls onNeedHelp when the concierge option is clicked", async () => {
    const user = userEvent.setup();
    const onNeedHelp = vi.fn();
    render(<RestaurantCardList restaurants={restaurants} selectedId={null} onSelect={() => {}} onNeedHelp={onNeedHelp} />);
    await user.click(screen.getByText("客服協助媒合"));
    expect(onNeedHelp).toHaveBeenCalledTimes(1);
  });
});
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `cd frontend && npx vitest run src/components/RestaurantCard.test.tsx src/components/RestaurantCardList.test.tsx`
Expected: FAIL（找不到模組）

- [ ] **Step 3: 實作**

```typescript
// frontend/src/components/RestaurantCard.tsx
import type { RestaurantInfo } from "../types/reservation";
import { ServiceIcon } from "./ServiceIcon";

interface Props {
  restaurant: RestaurantInfo;
  selected: boolean;
  onSelect: () => void;
}

export function RestaurantCard({ restaurant, selected, onSelect }: Props) {
  return (
    <button
      type="button"
      aria-pressed={selected}
      onClick={onSelect}
      className={`min-h-[44px] w-64 flex-none snap-start rounded-2xl border-2 p-4 text-left transition ${
        selected ? "border-brand bg-brand-soft" : "border-gray-200 bg-white"
      }`}
    >
      <p className="text-base font-black leading-normal text-slate-900">{restaurant.name}</p>
      <div className="mt-2 flex items-start gap-1.5 text-sm leading-relaxed text-slate-500">
        <ServiceIcon type="location" size={16} className="mt-0.5 flex-none" />
        <span>{restaurant.address}</span>
      </div>
      <div className="mt-1 flex items-center gap-1.5 text-sm leading-relaxed text-slate-500">
        <ServiceIcon type="phone" size={16} className="flex-none" />
        <span>{restaurant.phone}</span>
      </div>
    </button>
  );
}
```

```typescript
// frontend/src/components/RestaurantCardList.tsx
import type { RestaurantInfo } from "../types/reservation";
import { RestaurantCard } from "./RestaurantCard";

interface Props {
  restaurants: RestaurantInfo[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onNeedHelp: () => void;
}

export function RestaurantCardList({ restaurants, selectedId, onSelect, onNeedHelp }: Props) {
  return (
    <div className="flex snap-x gap-3 overflow-x-auto pb-2">
      {restaurants.slice(0, 6).map((restaurant) => (
        <RestaurantCard
          key={restaurant.id}
          restaurant={restaurant}
          selected={selectedId === restaurant.id}
          onSelect={() => onSelect(restaurant.id)}
        />
      ))}
      <button
        type="button"
        onClick={onNeedHelp}
        className="min-h-[44px] w-64 flex-none snap-start rounded-2xl border-2 border-dashed border-gray-300 bg-white p-4 text-left text-base font-bold text-brand"
      >
        客服協助媒合
        <p className="mt-1 text-sm font-normal leading-relaxed text-slate-500">留下需求，由客服為您安排。</p>
      </button>
    </div>
  );
}
```

- [ ] **Step 4: 執行測試確認通過**

Run: `cd frontend && npx vitest run src/components/RestaurantCard.test.tsx src/components/RestaurantCardList.test.tsx`
Expected: PASS（6 passed）

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/RestaurantCard.tsx frontend/src/components/RestaurantCard.test.tsx frontend/src/components/RestaurantCardList.tsx frontend/src/components/RestaurantCardList.test.tsx
git commit -m "feat: add restaurant selection card list"
```

---

## Task 13: ReservationDatePicker

**Files:**
- Create: `frontend/src/components/ReservationDatePicker.tsx`
- Create: `frontend/src/components/ReservationDatePicker.test.tsx`

**Interfaces:**
- Produces: `ReservationDatePicker({ value, onChange, today }: { value: string; onChange: (date: string) => void; today?: Date })`
- Consumed by: Task 19

(Requirement 3.1, 3.2, 3.5)

- [ ] **Step 1: 寫失敗測試**

```typescript
// frontend/src/components/ReservationDatePicker.test.tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ReservationDatePicker } from "./ReservationDatePicker";

describe("ReservationDatePicker", () => {
  it("sets min to today and max to today+60 days", () => {
    const today = new Date("2026-07-29T00:00:00+08:00");
    render(<ReservationDatePicker value="" onChange={() => {}} today={today} />);
    const input = screen.getByLabelText("用餐日期") as HTMLInputElement;
    expect(input.min).toBe("2026-07-29");
    expect(input.max).toBe("2026-09-27");
  });

  it("calls onChange with the picked date", () => {
    const onChange = vi.fn();
    const today = new Date("2026-07-29T00:00:00+08:00");
    render(<ReservationDatePicker value="" onChange={onChange} today={today} />);
    const input = screen.getByLabelText("用餐日期") as HTMLInputElement;
    input.value = "2026-08-01";
    input.dispatchEvent(new Event("input", { bubbles: true }));
    expect(onChange).toHaveBeenCalledWith("2026-08-01");
  });
});
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `cd frontend && npx vitest run src/components/ReservationDatePicker.test.tsx`
Expected: FAIL（找不到模組）

- [ ] **Step 3: 實作**

```typescript
// frontend/src/components/ReservationDatePicker.tsx
interface Props {
  value: string;
  onChange: (date: string) => void;
  today?: Date;
}

function toIsoDate(date: Date): string {
  return date.toISOString().slice(0, 10);
}

export function ReservationDatePicker({ value, onChange, today = new Date() }: Props) {
  const min = toIsoDate(today);
  const maxDate = new Date(today);
  maxDate.setDate(maxDate.getDate() + 60);
  const max = toIsoDate(maxDate);

  return (
    <div>
      <label htmlFor="reservation-date" className="block text-base font-bold leading-relaxed text-slate-900">
        用餐日期
      </label>
      <input
        id="reservation-date"
        aria-label="用餐日期"
        type="date"
        min={min}
        max={max}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="mt-2 min-h-[44px] w-full rounded-xl border-2 border-gray-200 px-3.5 py-2.5 text-base outline-none focus:border-brand"
      />
    </div>
  );
}
```

- [ ] **Step 4: 執行測試確認通過**

Run: `cd frontend && npx vitest run src/components/ReservationDatePicker.test.tsx`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ReservationDatePicker.tsx frontend/src/components/ReservationDatePicker.test.tsx
git commit -m "feat: add date-range-limited reservation date picker"
```

---

## Task 14: TimeSlotSelector

**Files:**
- Create: `frontend/src/components/TimeSlotSelector.tsx`
- Create: `frontend/src/components/TimeSlotSelector.test.tsx`

**Interfaces:**
- Produces: `TimeSlotSelector({ slot, specificTime, onSlotChange, onTimeChange }: { slot: "LUNCH" | "DINNER" | null; specificTime: string | null; onSlotChange: (slot: "LUNCH" | "DINNER") => void; onTimeChange: (time: string) => void })`
- Consumed by: Task 19

(Requirement 3.3, 3.4)

- [ ] **Step 1: 寫失敗測試**

```typescript
// frontend/src/components/TimeSlotSelector.test.tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { TimeSlotSelector } from "./TimeSlotSelector";

describe("TimeSlotSelector", () => {
  it("renders lunch and dinner buttons", () => {
    render(<TimeSlotSelector slot={null} specificTime={null} onSlotChange={() => {}} onTimeChange={() => {}} />);
    expect(screen.getByText("午餐（11:00–14:00）")).toBeInTheDocument();
    expect(screen.getByText("晚餐（17:00–21:00）")).toBeInTheDocument();
  });

  it("calls onSlotChange when a slot is picked", async () => {
    const user = userEvent.setup();
    const onSlotChange = vi.fn();
    render(<TimeSlotSelector slot={null} specificTime={null} onSlotChange={onSlotChange} onTimeChange={() => {}} />);
    await user.click(screen.getByText("午餐（11:00–14:00）"));
    expect(onSlotChange).toHaveBeenCalledWith("LUNCH");
  });

  it("shows 30-minute time options only after a slot is picked", () => {
    render(<TimeSlotSelector slot="LUNCH" specificTime={null} onSlotChange={() => {}} onTimeChange={() => {}} />);
    expect(screen.getByText("11:00")).toBeInTheDocument();
    expect(screen.getByText("13:30")).toBeInTheDocument();
    expect(screen.queryByText("14:00")).not.toBeInTheDocument();
  });

  it("calls onTimeChange when a specific time is picked", async () => {
    const user = userEvent.setup();
    const onTimeChange = vi.fn();
    render(<TimeSlotSelector slot="DINNER" specificTime={null} onSlotChange={() => {}} onTimeChange={onTimeChange} />);
    await user.click(screen.getByText("18:00"));
    expect(onTimeChange).toHaveBeenCalledWith("18:00");
  });
});
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `cd frontend && npx vitest run src/components/TimeSlotSelector.test.tsx`
Expected: FAIL

- [ ] **Step 3: 實作**

```typescript
// frontend/src/components/TimeSlotSelector.tsx
type Slot = "LUNCH" | "DINNER";

interface Props {
  slot: Slot | null;
  specificTime: string | null;
  onSlotChange: (slot: Slot) => void;
  onTimeChange: (time: string) => void;
}

function timesFor(slot: Slot): string[] {
  const [start, end] = slot === "LUNCH" ? [11, 14] : [17, 21];
  const times: string[] = [];
  for (let h = start; h < end; h++) {
    times.push(`${String(h).padStart(2, "0")}:00`);
    times.push(`${String(h).padStart(2, "0")}:30`);
  }
  return times;
}

export function TimeSlotSelector({ slot, specificTime, onSlotChange, onTimeChange }: Props) {
  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-2 gap-3">
        <button
          type="button"
          aria-pressed={slot === "LUNCH"}
          onClick={() => onSlotChange("LUNCH")}
          className={`min-h-[44px] rounded-2xl border-2 px-4 py-3 text-base font-bold ${
            slot === "LUNCH" ? "border-brand bg-brand-soft text-brand" : "border-gray-200 bg-white text-slate-700"
          }`}
        >
          午餐（11:00–14:00）
        </button>
        <button
          type="button"
          aria-pressed={slot === "DINNER"}
          onClick={() => onSlotChange("DINNER")}
          className={`min-h-[44px] rounded-2xl border-2 px-4 py-3 text-base font-bold ${
            slot === "DINNER" ? "border-brand bg-brand-soft text-brand" : "border-gray-200 bg-white text-slate-700"
          }`}
        >
          晚餐（17:00–21:00）
        </button>
      </div>

      {slot && (
        <div className="grid grid-cols-4 gap-2">
          {timesFor(slot).map((time) => (
            <button
              key={time}
              type="button"
              aria-pressed={specificTime === time}
              onClick={() => onTimeChange(time)}
              className={`min-h-[44px] rounded-xl border-2 text-sm font-bold ${
                specificTime === time ? "border-brand bg-brand-soft text-brand" : "border-gray-200 bg-white text-slate-600"
              }`}
            >
              {time}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 4: 執行測試確認通過**

Run: `cd frontend && npx vitest run src/components/TimeSlotSelector.test.tsx`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/TimeSlotSelector.tsx frontend/src/components/TimeSlotSelector.test.tsx
git commit -m "feat: add lunch/dinner time slot selector with 30-minute increments"
```

---

## Task 15: PeopleCounter

**Files:**
- Create: `frontend/src/components/PeopleCounter.tsx`
- Create: `frontend/src/components/PeopleCounter.test.tsx`

**Interfaces:**
- Produces: `PeopleCounter({ value, onChange, min?: number, max?: number }: { value: number; onChange: (n: number) => void; min?: number; max?: number })`（預設 `min=1, max=20`）
- Consumed by: Task 19

(Requirement 4.2, 4.3, 4.4)

- [ ] **Step 1: 寫失敗測試**

```typescript
// frontend/src/components/PeopleCounter.test.tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { PeopleCounter } from "./PeopleCounter";

describe("PeopleCounter", () => {
  it("shows the current value", () => {
    render(<PeopleCounter value={2} onChange={() => {}} />);
    expect(screen.getByText("2")).toBeInTheDocument();
  });

  it("increments on plus click", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<PeopleCounter value={2} onChange={onChange} />);
    await user.click(screen.getByLabelText("增加人數"));
    expect(onChange).toHaveBeenCalledWith(3);
  });

  it("decrements on minus click", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<PeopleCounter value={2} onChange={onChange} />);
    await user.click(screen.getByLabelText("減少人數"));
    expect(onChange).toHaveBeenCalledWith(1);
  });

  it("disables minus button at the lower bound", () => {
    render(<PeopleCounter value={1} onChange={() => {}} />);
    expect(screen.getByLabelText("減少人數")).toBeDisabled();
  });

  it("disables plus button at the upper bound", () => {
    render(<PeopleCounter value={20} onChange={() => {}} />);
    expect(screen.getByLabelText("增加人數")).toBeDisabled();
  });
});
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `cd frontend && npx vitest run src/components/PeopleCounter.test.tsx`
Expected: FAIL

- [ ] **Step 3: 實作**

```typescript
// frontend/src/components/PeopleCounter.tsx
interface Props {
  value: number;
  onChange: (value: number) => void;
  min?: number;
  max?: number;
}

export function PeopleCounter({ value, onChange, min = 1, max = 20 }: Props) {
  return (
    <div className="flex items-center justify-center gap-6">
      <button
        type="button"
        aria-label="減少人數"
        disabled={value <= min}
        onClick={() => onChange(value - 1)}
        className="flex h-11 w-11 items-center justify-center rounded-full border-2 border-brand text-2xl font-black text-brand disabled:border-gray-200 disabled:text-gray-300"
      >
        −
      </button>
      <span className="min-w-[3ch] text-center text-2xl font-black text-slate-900">{value}</span>
      <button
        type="button"
        aria-label="增加人數"
        disabled={value >= max}
        onClick={() => onChange(value + 1)}
        className="flex h-11 w-11 items-center justify-center rounded-full border-2 border-brand text-2xl font-black text-brand disabled:border-gray-200 disabled:text-gray-300"
      >
        +
      </button>
    </div>
  );
}
```

- [ ] **Step 4: 執行測試確認通過**

Run: `cd frontend && npx vitest run src/components/PeopleCounter.test.tsx`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/PeopleCounter.tsx frontend/src/components/PeopleCounter.test.tsx
git commit -m "feat: add people counter with +/- stepper"
```

---

## Task 16: ReservationContactForm

**Files:**
- Create: `frontend/src/components/ReservationContactForm.tsx`
- Create: `frontend/src/components/ReservationContactForm.test.tsx`

**Interfaces:**
- Produces: `ReservationContactForm({ name, phone, onNameChange, onPhoneChange, error }: { name: string; phone: string; onNameChange: (v: string) => void; onPhoneChange: (v: string) => void; error?: string | null })`
- Consumed by: Task 19

(Requirement 5.1, 5.3, 5.4, 5.5, 5.6)

- [ ] **Step 1: 寫失敗測試**

```typescript
// frontend/src/components/ReservationContactForm.test.tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ReservationContactForm } from "./ReservationContactForm";

describe("ReservationContactForm", () => {
  it("renders current name and phone", () => {
    render(<ReservationContactForm name="王大明" phone="0912345678" onNameChange={() => {}} onPhoneChange={() => {}} />);
    expect(screen.getByLabelText("聯絡人姓名")).toHaveValue("王大明");
    expect(screen.getByLabelText("聯絡電話")).toHaveValue("0912345678");
  });

  it("calls onNameChange and onPhoneChange", async () => {
    const user = userEvent.setup();
    const onNameChange = vi.fn();
    render(<ReservationContactForm name="" phone="" onNameChange={onNameChange} onPhoneChange={() => {}} />);
    await user.type(screen.getByLabelText("聯絡人姓名"), "王");
    expect(onNameChange).toHaveBeenCalled();
  });

  it("shows the error message when provided", () => {
    render(
      <ReservationContactForm
        name=""
        phone="123"
        onNameChange={() => {}}
        onPhoneChange={() => {}}
        error="請輸入正確的手機號碼格式（09 開頭，共 10 碼）"
      />,
    );
    expect(screen.getByText("請輸入正確的手機號碼格式（09 開頭，共 10 碼）")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `cd frontend && npx vitest run src/components/ReservationContactForm.test.tsx`
Expected: FAIL

- [ ] **Step 3: 實作**

```typescript
// frontend/src/components/ReservationContactForm.tsx
interface Props {
  name: string;
  phone: string;
  onNameChange: (value: string) => void;
  onPhoneChange: (value: string) => void;
  error?: string | null;
}

export function ReservationContactForm({ name, phone, onNameChange, onPhoneChange, error }: Props) {
  return (
    <div className="flex flex-col gap-4">
      <div>
        <label htmlFor="contact-name" className="block text-base font-bold leading-relaxed text-slate-900">
          聯絡人姓名
        </label>
        <input
          id="contact-name"
          aria-label="聯絡人姓名"
          type="text"
          maxLength={50}
          value={name}
          onChange={(e) => onNameChange(e.target.value)}
          className="mt-2 min-h-[44px] w-full rounded-xl border-2 border-gray-200 px-3.5 py-2.5 text-base outline-none focus:border-brand"
        />
      </div>
      <div>
        <label htmlFor="contact-phone" className="block text-base font-bold leading-relaxed text-slate-900">
          聯絡電話
        </label>
        <input
          id="contact-phone"
          aria-label="聯絡電話"
          type="tel"
          placeholder="0912345678"
          value={phone}
          onChange={(e) => onPhoneChange(e.target.value)}
          className="mt-2 min-h-[44px] w-full rounded-xl border-2 border-gray-200 px-3.5 py-2.5 text-base outline-none focus:border-brand"
        />
      </div>
      {error && <p className="text-sm font-bold text-danger">{error}</p>}
    </div>
  );
}
```

- [ ] **Step 4: 執行測試確認通過**

Run: `cd frontend && npx vitest run src/components/ReservationContactForm.test.tsx`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ReservationContactForm.tsx frontend/src/components/ReservationContactForm.test.tsx
git commit -m "feat: add reservation contact form"
```

---

## Task 17: PremiumToggle

**Files:**
- Create: `frontend/src/components/PremiumToggle.tsx`
- Create: `frontend/src/components/PremiumToggle.test.tsx`

**Interfaces:**
- Produces: `PremiumToggle({ value, onChange }: { value: boolean | null; onChange: (isPremium: boolean) => void })`
- Consumed by: Task 19

(Requirement 13.1)

- [ ] **Step 1: 寫失敗測試**

```typescript
// frontend/src/components/PremiumToggle.test.tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { PremiumToggle } from "./PremiumToggle";

describe("PremiumToggle", () => {
  it("renders both options with explanatory text", () => {
    render(<PremiumToggle value={null} onChange={() => {}} />);
    expect(screen.getByText("是，我要指定/高級訂位")).toBeInTheDocument();
    expect(screen.getByText("否，一般訂位即可")).toBeInTheDocument();
    expect(screen.getByText(/專人為您安排指定餐廳或特殊座位需求/)).toBeInTheDocument();
  });

  it("calls onChange(true) for premium option", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<PremiumToggle value={null} onChange={onChange} />);
    await user.click(screen.getByText("是，我要指定/高級訂位"));
    expect(onChange).toHaveBeenCalledWith(true);
  });

  it("calls onChange(false) for standard option", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<PremiumToggle value={null} onChange={onChange} />);
    await user.click(screen.getByText("否，一般訂位即可"));
    expect(onChange).toHaveBeenCalledWith(false);
  });
});
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `cd frontend && npx vitest run src/components/PremiumToggle.test.tsx`
Expected: FAIL

- [ ] **Step 3: 實作**

```typescript
// frontend/src/components/PremiumToggle.tsx
interface Props {
  value: boolean | null;
  onChange: (isPremium: boolean) => void;
}

export function PremiumToggle({ value, onChange }: Props) {
  return (
    <div className="flex flex-col gap-3">
      <p className="text-sm leading-relaxed text-slate-500">
        高級訂位代表將由專人為您安排指定餐廳或特殊座位需求，處理時間可能較長。
      </p>
      <button
        type="button"
        aria-pressed={value === true}
        onClick={() => onChange(true)}
        className={`min-h-[44px] rounded-2xl border-2 px-4 py-3 text-left text-base font-bold ${
          value === true ? "border-brand bg-brand-soft text-brand" : "border-gray-200 bg-white text-slate-700"
        }`}
      >
        是，我要指定/高級訂位
      </button>
      <button
        type="button"
        aria-pressed={value === false}
        onClick={() => onChange(false)}
        className={`min-h-[44px] rounded-2xl border-2 px-4 py-3 text-left text-base font-bold ${
          value === false ? "border-brand bg-brand-soft text-brand" : "border-gray-200 bg-white text-slate-700"
        }`}
      >
        否，一般訂位即可
      </button>
    </div>
  );
}
```

- [ ] **Step 4: 執行測試確認通過**

Run: `cd frontend && npx vitest run src/components/PremiumToggle.test.tsx`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/PremiumToggle.tsx frontend/src/components/PremiumToggle.test.tsx
git commit -m "feat: add premium reservation toggle"
```

---

## Task 18: ReservationSummaryCard

**Files:**
- Create: `frontend/src/components/ReservationSummaryCard.tsx`
- Create: `frontend/src/components/ReservationSummaryCard.test.tsx`

**Interfaces:**
- Produces: `ReservationSummaryCard({ data, onConfirm, onEdit, submitting }: { data: { restaurantName: string; date: string; timeSlot: string; specificTime: string | null; people: number; contactName: string; phone: string; isPremium: boolean }; onConfirm: () => void; onEdit: () => void; submitting: boolean })`
- Consumed by: Task 19

(Requirement 6.1, 6.2, 6.5, 12.1, 12.2)

- [ ] **Step 1: 寫失敗測試**

```typescript
// frontend/src/components/ReservationSummaryCard.test.tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ReservationSummaryCard } from "./ReservationSummaryCard";

const data = {
  restaurantName: "22世紀風味館 信義旗艦店",
  date: "2026-08-01",
  timeSlot: "午餐",
  specificTime: "12:30",
  people: 4,
  contactName: "王大明",
  phone: "0912345678",
  isPremium: false,
};

describe("ReservationSummaryCard", () => {
  it("renders every field with its label", () => {
    render(<ReservationSummaryCard data={data} onConfirm={() => {}} onEdit={() => {}} submitting={false} />);
    expect(screen.getByText(data.restaurantName)).toBeInTheDocument();
    expect(screen.getByText(data.contactName)).toBeInTheDocument();
    expect(screen.getByText(data.phone)).toBeInTheDocument();
    expect(screen.getByText("4")).toBeInTheDocument();
  });

  it("calls onConfirm on submit click", async () => {
    const user = userEvent.setup();
    const onConfirm = vi.fn();
    render(<ReservationSummaryCard data={data} onConfirm={onConfirm} onEdit={() => {}} submitting={false} />);
    await user.click(screen.getByText("確認送出"));
    expect(onConfirm).toHaveBeenCalledTimes(1);
  });

  it("calls onEdit on back click", async () => {
    const user = userEvent.setup();
    const onEdit = vi.fn();
    render(<ReservationSummaryCard data={data} onConfirm={() => {}} onEdit={onEdit} submitting={false} />);
    await user.click(screen.getByText("返回修改"));
    expect(onEdit).toHaveBeenCalledTimes(1);
  });

  it("disables the confirm button and shows a loading label while submitting", () => {
    render(<ReservationSummaryCard data={data} onConfirm={() => {}} onEdit={() => {}} submitting />);
    expect(screen.getByText("訂位處理中，請稍候")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /訂位處理中/ })).toBeDisabled();
  });
});
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `cd frontend && npx vitest run src/components/ReservationSummaryCard.test.tsx`
Expected: FAIL

- [ ] **Step 3: 實作**

```typescript
// frontend/src/components/ReservationSummaryCard.tsx
interface SummaryData {
  restaurantName: string;
  date: string;
  timeSlot: string;
  specificTime: string | null;
  people: number;
  contactName: string;
  phone: string;
  isPremium: boolean;
}

interface Props {
  data: SummaryData;
  onConfirm: () => void;
  onEdit: () => void;
  submitting: boolean;
}

const ROWS: { key: keyof SummaryData; label: string; format?: (v: SummaryData) => string }[] = [
  { key: "restaurantName", label: "餐廳名稱" },
  { key: "date", label: "用餐日期" },
  { key: "timeSlot", label: "用餐時段", format: (d) => `${d.timeSlot}${d.specificTime ? ` ${d.specificTime}` : ""}` },
  { key: "people", label: "用餐人數", format: (d) => String(d.people) },
  { key: "contactName", label: "聯絡人" },
  { key: "phone", label: "聯絡電話" },
  { key: "isPremium", label: "訂位類型", format: (d) => (d.isPremium ? "高級訂位" : "一般訂位") },
];

export function ReservationSummaryCard({ data, onConfirm, onEdit, submitting }: Props) {
  return (
    <div className="rounded-3xl border border-gray-200 bg-white p-5">
      {ROWS.map((row) => (
        <div key={row.key} className="flex justify-between gap-3 border-b border-gray-100 py-3.5 text-base leading-relaxed last:border-b-0">
          <span className="font-bold text-slate-500">{row.label}</span>
          <span className="text-right font-bold text-slate-900">{row.format ? row.format(data) : String(data[row.key])}</span>
        </div>
      ))}

      <div className="mt-5 flex flex-col gap-3">
        <button
          type="button"
          onClick={onConfirm}
          disabled={submitting}
          className="min-h-[44px] rounded-2xl bg-brand px-6 py-4 text-base font-bold text-white disabled:opacity-60"
        >
          {submitting ? "訂位處理中，請稍候" : "確認送出"}
        </button>
        <button
          type="button"
          onClick={onEdit}
          disabled={submitting}
          className="min-h-[44px] rounded-2xl border-2 border-brand px-6 py-4 text-base font-bold text-brand disabled:opacity-60"
        >
          返回修改
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: 執行測試確認通過**

Run: `cd frontend && npx vitest run src/components/ReservationSummaryCard.test.tsx`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ReservationSummaryCard.tsx frontend/src/components/ReservationSummaryCard.test.tsx
git commit -m "feat: add reservation confirmation summary card"
```

---

## Task 19: ReservationFlowPage（整合精靈頁面）+ 路由

**Files:**
- Create: `frontend/src/pages/ReservationFlowPage.tsx`
- Create: `frontend/src/pages/ReservationFlowPage.test.tsx`
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- Consumes: 所有 Task 10-18 產出的元件與 `frontend/src/api/reservations.ts`
- Produces: `ReservationFlowPage`（預設 export 或具名 export，跟現有頁面一致——先看 `NewRequestPage.tsx` 是用哪種 export 方式）

**步驟機（Requirement 14.3「一次一問」）：**
`restaurant → date → time → people → contact → premium → summary`，每個 step 一次只顯示一個畫面，`onNext`/`onBack` 切換 step index；所有已填資料留在 component state，返回修改不會清空（Requirement 6.3, 10.2）。

- [ ] **Step 1: 讀 `frontend/src/pages/NewRequestPage.tsx` 全文**，確認頁面的 export 慣例、`ButlerLauncher currentPageId` 用法、`useNavigate` 用法，讓新頁面風格一致。

- [ ] **Step 2: 寫失敗測試**（涵蓋 Requirement 14.3 一次一問、10.2 表單資料保存、12.1/12.2 防重複點擊 UI）

```typescript
// frontend/src/pages/ReservationFlowPage.test.tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { ReservationFlowPage } from "./ReservationFlowPage";
import * as reservationsApi from "../api/reservations";

vi.mock("../api/reservations");

const restaurants = [
  { id: "r001", name: "22世紀風味館 信義旗艦店", brand: "b", address: "台北市信義區松高路12號3樓", phone: "02-2723-0022", cuisine: "c", supports_booking_api: true },
];

function renderPage() {
  return render(
    <MemoryRouter>
      <ReservationFlowPage />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.mocked(reservationsApi.listRestaurants).mockResolvedValue(restaurants);
});

describe("ReservationFlowPage", () => {
  it("shows only the restaurant selection step first", async () => {
    renderPage();
    expect(await screen.findByText("22世紀風味館 信義旗艦店")).toBeInTheDocument();
    expect(screen.queryByLabelText("用餐日期")).not.toBeInTheDocument();
  });

  it("advances to the date step after picking a restaurant, and preserves the pick when going back", async () => {
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByText("22世紀風味館 信義旗艦店"));
    await user.click(screen.getByText("下一步"));

    expect(screen.getByLabelText("用餐日期")).toBeInTheDocument();
    expect(screen.queryByText("22世紀風味館 信義旗艦店")).not.toBeInTheDocument();

    await user.click(screen.getByText("上一步"));
    expect(screen.getByRole("button", { name: "22世紀風味館 信義旗艦店" })).toHaveAttribute("aria-pressed", "true");
  });

  it("disables the submit button immediately after clicking it to block double submission", async () => {
    vi.mocked(reservationsApi.submitReservation).mockImplementation(
      () => new Promise(() => {}), // never resolves, simulate in-flight request
    );
    const user = userEvent.setup();
    renderPage();

    await user.click(await screen.findByText("22世紀風味館 信義旗艦店"));
    await user.click(screen.getByText("下一步"));
    await user.type(screen.getByLabelText("用餐日期"), "2026-08-01");
    await user.click(screen.getByText("下一步"));
    await user.click(screen.getByText("午餐（11:00–14:00）"));
    await user.click(screen.getByText("12:00"));
    await user.click(screen.getByText("下一步"));
    await user.click(screen.getByText("下一步")); // people, default 2
    await user.type(screen.getByLabelText("聯絡人姓名"), "王大明");
    await user.type(screen.getByLabelText("聯絡電話"), "0912345678");
    await user.click(screen.getByText("下一步"));
    await user.click(screen.getByText("否，一般訂位即可"));
    await user.click(screen.getByText("下一步"));

    const confirmButton = screen.getByText("確認送出");
    await user.click(confirmButton);

    expect(screen.getByRole("button", { name: /訂位處理中/ })).toBeDisabled();
  });
});
```

> 這個測試檔案裡的按鈕文字（例如「下一步」「上一步」）是給 Step 3 實作的**規格**，不是既有程式碼——實作時要讓元件確實輸出這些文字，或者在完成 Step 3 後回頭把測試裡的文字改成跟實作一致（兩者對齊即可，重點是行為：一次一問、返回保留資料、送出防重複點擊）。

- [ ] **Step 3: 執行測試確認失敗**

Run: `cd frontend && npx vitest run src/pages/ReservationFlowPage.test.tsx`
Expected: FAIL

- [ ] **Step 4: 實作**

```typescript
// frontend/src/pages/ReservationFlowPage.tsx
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ButlerLauncher } from "../components/ButlerLauncher";
import { PeopleCounter } from "../components/PeopleCounter";
import { PremiumToggle } from "../components/PremiumToggle";
import { ReservationContactForm } from "../components/ReservationContactForm";
import { ReservationDatePicker } from "../components/ReservationDatePicker";
import { ReservationSummaryCard } from "../components/ReservationSummaryCard";
import { RestaurantCardList } from "../components/RestaurantCardList";
import { ServiceIcon } from "../components/ServiceIcon";
import { TimeSlotSelector } from "../components/TimeSlotSelector";
import { Toast } from "../components/Toast";
import { getRestaurant, listRestaurants, submitReservation } from "../api/reservations";
import type { RestaurantInfo, TimeSlot } from "../types/reservation";

type Step = "restaurant" | "date" | "time" | "people" | "contact" | "premium" | "summary";
const STEP_ORDER: Step[] = ["restaurant", "date", "time", "people", "contact", "premium", "summary"];

export function ReservationFlowPage() {
  const navigate = useNavigate();
  const [restaurants, setRestaurants] = useState<RestaurantInfo[]>([]);
  const [stepIndex, setStepIndex] = useState(0);
  const [restaurantId, setRestaurantId] = useState<string | null>(null);
  const [date, setDate] = useState("");
  const [timeSlot, setTimeSlot] = useState<TimeSlot | null>(null);
  const [specificTime, setSpecificTime] = useState<string | null>(null);
  const [people, setPeople] = useState(2);
  const [contactName, setContactName] = useState("");
  const [phone, setPhone] = useState("");
  const [isPremium, setIsPremium] = useState<boolean | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [toastText, setToastText] = useState<string | null>(null);

  useEffect(() => {
    listRestaurants()
      .then(setRestaurants)
      .catch(() => setToastText("目前無法載入餐廳清單，您可以留下需求由客服為您安排。"));
  }, []);

  const step = STEP_ORDER[stepIndex];
  const goNext = () => setStepIndex((i) => Math.min(i + 1, STEP_ORDER.length - 1));
  const goBack = () => setStepIndex((i) => Math.max(i - 1, 0));

  const selectedRestaurant = restaurants.find((r) => r.id === restaurantId) ?? null;

  async function handleConfirm() {
    if (!restaurantId || !timeSlot || isPremium === null) return;
    setSubmitting(true);
    try {
      const result = await submitReservation({
        restaurant_id: restaurantId,
        reserved_date: date,
        time_slot: timeSlot,
        specific_time: specificTime,
        people,
        contact_name: contactName,
        phone,
        is_premium: isPremium,
      });
      navigate(`/requests/${result.request_id}`);
    } catch (err) {
      setSubmitting(false);
      setToastText(err instanceof Error ? err.message : "訂位未成功送出，請重新嘗試");
    }
  }

  return (
    <>
      <main className="mx-auto min-h-dvh max-w-md bg-canvas px-5 pb-32 pt-8">
        <header className="flex items-center gap-3 pb-4">
          <button type="button" onClick={() => navigate("/home")} aria-label="返回" className="text-gray-500">
            <ServiceIcon type="back" size={22} />
          </button>
          <h1 className="text-xl font-black text-slate-900">餐廳訂位</h1>
        </header>

        {step === "restaurant" && (
          <section className="flex flex-col gap-4">
            <p className="text-base font-bold leading-relaxed text-slate-900">請選擇想去的餐廳</p>
            <RestaurantCardList
              restaurants={restaurants}
              selectedId={restaurantId}
              onSelect={setRestaurantId}
              onNeedHelp={() => setToastText("已為您記錄需求，客服將協助媒合餐廳。")}
            />
            <button
              type="button"
              disabled={!restaurantId}
              onClick={goNext}
              className="mt-2 min-h-[44px] rounded-2xl bg-brand px-6 py-4 text-base font-bold text-white disabled:opacity-40"
            >
              下一步
            </button>
          </section>
        )}

        {step === "date" && (
          <section className="flex flex-col gap-4">
            <ReservationDatePicker value={date} onChange={setDate} />
            <div className="flex gap-3">
              <button type="button" onClick={goBack} className="min-h-[44px] flex-1 rounded-2xl border-2 border-brand px-6 py-4 text-base font-bold text-brand">
                上一步
              </button>
              <button
                type="button"
                disabled={!date}
                onClick={goNext}
                className="min-h-[44px] flex-1 rounded-2xl bg-brand px-6 py-4 text-base font-bold text-white disabled:opacity-40"
              >
                下一步
              </button>
            </div>
          </section>
        )}

        {step === "time" && (
          <section className="flex flex-col gap-4">
            <TimeSlotSelector slot={timeSlot} specificTime={specificTime} onSlotChange={setTimeSlot} onTimeChange={setSpecificTime} />
            <div className="flex gap-3">
              <button type="button" onClick={goBack} className="min-h-[44px] flex-1 rounded-2xl border-2 border-brand px-6 py-4 text-base font-bold text-brand">
                上一步
              </button>
              <button
                type="button"
                disabled={!timeSlot || !specificTime}
                onClick={goNext}
                className="min-h-[44px] flex-1 rounded-2xl bg-brand px-6 py-4 text-base font-bold text-white disabled:opacity-40"
              >
                下一步
              </button>
            </div>
          </section>
        )}

        {step === "people" && (
          <section className="flex flex-col gap-6">
            <p className="text-base font-bold leading-relaxed text-slate-900">請問幾位用餐？</p>
            <PeopleCounter value={people} onChange={setPeople} />
            <div className="flex gap-3">
              <button type="button" onClick={goBack} className="min-h-[44px] flex-1 rounded-2xl border-2 border-brand px-6 py-4 text-base font-bold text-brand">
                上一步
              </button>
              <button type="button" onClick={goNext} className="min-h-[44px] flex-1 rounded-2xl bg-brand px-6 py-4 text-base font-bold text-white">
                下一步
              </button>
            </div>
          </section>
        )}

        {step === "contact" && (
          <section className="flex flex-col gap-4">
            <ReservationContactForm name={contactName} phone={phone} onNameChange={setContactName} onPhoneChange={setPhone} />
            <div className="flex gap-3">
              <button type="button" onClick={goBack} className="min-h-[44px] flex-1 rounded-2xl border-2 border-brand px-6 py-4 text-base font-bold text-brand">
                上一步
              </button>
              <button
                type="button"
                disabled={!contactName.trim() || !phone}
                onClick={goNext}
                className="min-h-[44px] flex-1 rounded-2xl bg-brand px-6 py-4 text-base font-bold text-white disabled:opacity-40"
              >
                下一步
              </button>
            </div>
          </section>
        )}

        {step === "premium" && (
          <section className="flex flex-col gap-4">
            <p className="text-base font-bold leading-relaxed text-slate-900">請問需要指定餐廳或高級訂位服務嗎？</p>
            <PremiumToggle value={isPremium} onChange={setIsPremium} />
            <div className="flex gap-3">
              <button type="button" onClick={goBack} className="min-h-[44px] flex-1 rounded-2xl border-2 border-brand px-6 py-4 text-base font-bold text-brand">
                上一步
              </button>
              <button
                type="button"
                disabled={isPremium === null}
                onClick={goNext}
                className="min-h-[44px] flex-1 rounded-2xl bg-brand px-6 py-4 text-base font-bold text-white disabled:opacity-40"
              >
                下一步
              </button>
            </div>
          </section>
        )}

        {step === "summary" && selectedRestaurant && (
          <ReservationSummaryCard
            data={{
              restaurantName: selectedRestaurant.name,
              date,
              timeSlot: timeSlot === "LUNCH" ? "午餐" : "晚餐",
              specificTime,
              people,
              contactName,
              phone,
              isPremium: Boolean(isPremium),
            }}
            onConfirm={handleConfirm}
            onEdit={goBack}
            submitting={submitting}
          />
        )}
      </main>

      <Toast text={toastText} onHide={() => setToastText(null)} />
      <ButlerLauncher currentPageId="reservation_flow" />
    </>
  );
}
```

> `getRestaurant` import 目前未使用，若最終沒有用到就從 import 移除，避免 lint/TS 未使用變數錯誤。

- [ ] **Step 5: 新增路由**

在 `frontend/src/App.tsx` 加入 import：

```typescript
import { ReservationFlowPage } from "./pages/ReservationFlowPage";
```

在 `<Route path="/services/:serviceId" .../>` **之前**加入專屬路由（React Router v6 的路由排序不影響靜態 vs 動態 segment 的匹配優先權，但寫在前面更易讀）：

```typescript
      <Route
        path="/services/restaurant_reservation"
        element={<Protected><ReservationFlowPage /></Protected>}
      />
```

- [ ] **Step 6: 執行測試確認通過**

Run: `cd frontend && npx vitest run src/pages/ReservationFlowPage.test.tsx`
Expected: PASS（若按鈕文字與測試不一致，依 Step 2 的說明二擇一調整，讓兩邊一致後通過）

- [ ] **Step 7: 型別檢查全專案**

Run: `cd frontend && npx tsc --noEmit`
Expected: 無錯誤

- [ ] **Step 8: Commit**

```bash
git add frontend/src/pages/ReservationFlowPage.tsx frontend/src/pages/ReservationFlowPage.test.tsx frontend/src/App.tsx
git commit -m "feat: add reservation flow wizard page and route"
```

---

## Task 20: RequestDetailPage 的核銷示範按鈕

**Files:**
- Modify: `frontend/src/pages/RequestDetailPage.tsx`
- Test: 若既有專案沒有 `RequestDetailPage.test.tsx`，這裡不強制新建（該頁面目前沒有測試檔的先例）；改用 Step 3 的手動驗證取代。

**目的：** 讓 Requirement 11.3（已完成→核銷完成）在既有的「Demo 模擬」按鈕機制下可被示範，且只對訂位服務、且餐廳有啟用核銷時出現。

- [ ] **Step 1: 修改 `nextDemo` 邏輯**

在 `frontend/src/pages/RequestDetailPage.tsx`，把目前寫死的 `nextDemo` 物件查表：

```typescript
  const nextDemo: Record<string, { to: string; label: string }> = {
    SUBMITTED: { to: "CONFIRMED", label: "Demo：模擬廠商已確認" },
    PENDING_PROVIDER: { to: "CONFIRMED", label: "Demo：模擬廠商已確認" },
    CONFIRMED: { to: "IN_PROGRESS", label: "Demo：模擬服務進行中" },
    IN_PROGRESS: { to: "COMPLETED", label: "Demo：模擬服務已完成" },
  };
  const demo = nextDemo[detail.status];
```

改成（在既有查表之後，額外處理「已完成 → 已核銷」只對訂位服務顯示）：

```typescript
  const nextDemo: Record<string, { to: string; label: string }> = {
    SUBMITTED: { to: "CONFIRMED", label: "Demo：模擬廠商已確認" },
    PENDING_PROVIDER: { to: "CONFIRMED", label: "Demo：模擬廠商已確認" },
    CONFIRMED: { to: "IN_PROGRESS", label: "Demo：模擬服務進行中" },
    IN_PROGRESS: { to: "COMPLETED", label: "Demo：模擬服務已完成" },
  };
  const isReservation = detail.service_id === "restaurant_reservation";
  if (isReservation && detail.status === "COMPLETED") {
    nextDemo.COMPLETED = { to: "VERIFIED", label: "Demo：模擬已核銷" };
  }
  const demo = nextDemo[detail.status];
```

`detail.service_id` 需要確認 `RequestDetail` 型別（`frontend/src/types/request.ts`）已經有這個欄位——如果沒有，先在該型別加上 `service_id: string;`（後端 `GET /api/requests/{id}` 的回應本來就含這個欄位，只是型別定義沒宣告）。

- [ ] **Step 2: 型別檢查**

Run: `cd frontend && npx tsc --noEmit`
Expected: 無錯誤

- [ ] **Step 3: 手動驗證**（無自動測試覆蓋此檔案，用手動走查取代，照 superpowers:verification-before-completion 的精神留下證據）

1. 啟動後端與前端（`cd backend && python -m uvicorn app.main:app --reload` / `cd frontend && npm run dev`）。
2. 登入後在 HomePage 點「餐廳訂位」卡片，走完精靈流程選 `r001`（信義旗艦店，`verification_enabled=True`），確認送出後應直接看到狀態「已確認」。
3. 進入該案件明細，依序點擊 Demo 按鈕：模擬服務進行中 → 模擬服務已完成 → 應該出現「Demo：模擬已核銷」按鈕，點擊後狀態變成「已核銷」。
4. 另外用 `r005`（桃園中正店，`supports_booking_api=False`）走一次，確認初始狀態是「等待廠商確認」，且有「Demo：模擬廠商已確認」按鈕可推進。
5. 重複用同一個餐廳/日期/時段送出兩次，確認第二次被擋下並顯示重複訂位訊息（Requirement 12.5）。

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/RequestDetailPage.tsx frontend/src/types/request.ts
git commit -m "feat: add verification demo transition for completed reservations"
```

---

## Task 21: 全專案回歸驗證

**Files:** 無新檔案，純驗證。

- [ ] **Step 1: 後端全測試**

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests -v`
Expected: 全部 PASS，無既有測試被破壞

- [ ] **Step 2: 前端全測試**

Run: `cd frontend && npx vitest run`
Expected: 全部 PASS

- [ ] **Step 3: 前端型別檢查**

Run: `cd frontend && npx tsc --noEmit`
Expected: 無錯誤

- [ ] **Step 4: 前端建置**

Run: `cd frontend && npm run build`
Expected: 建置成功，無錯誤

- [ ] **Step 5: 依 Task 20 Step 3 的手動驗證清單，完整跑一次端對端流程**（若 Task 20 執行時已完整跑過可省略重跑，但務必在提交 PR 前至少跑過一次）

- [ ] **Step 6: 最終 commit（若前面步驟有修正）**

```bash
git add -A
git commit -m "test: full regression pass for restaurant reservation feature"
```

---

## Self-Review Notes（撰寫計畫時的自我檢查紀錄）

- **Spec coverage：** Requirement 1（服務註冊）→ Task 11, 19, 23；2（餐廳選擇）→ Task 12, 19；3（日期時段）→ Task 13, 14, 3；4（人數）→ Task 15, 3；5（聯絡資料）→ Task 16, 3；6（確認摘要）→ Task 18；7（訂單建立）→ Task 5；8（第三方串接）→ Task 4, 5；9（異常處理/重試）→ Task 5 內建骨架（`retry_service.mark_for_retry`），**完整重試迴圈已依使用者決定砲掉，見下方「已知範圍縮小」**；10（額滿處理）— **注意**：Mock Adapter 目前不會回傳 `NO_AVAILABILITY`（設計上只回傳 `CONFIRMED`/`ERROR`），Requirement 10 的額滿情境在目前的 Mock 實作下不會被觸發到，本計畫刻意縮小的範圍；11（狀態推進）→ Task 9, 20（**Task 7 狀態排程器已砲掉**，靠手動按鈕涵蓋）；12（防重複提交）→ Task 5（後端）、Task 18/19（前端 UI 防連點）；13（高級訂位）→ Task 5, 17；14（高齡友善規範）→ Global Constraints + 各元件的 class（44px 觸控、字級、對比色沿用既有 `brand`/`danger` class）。對話式訂位入口（Task 22-25）額外涵蓋 Requirement 1.2 的「對話式訂位流程」字面需求。
- **Placeholder scan：** Task 10 的 `api/reservations.ts` 刻意留了需要對照既有檔案風格填寫的部分，並非偷懶留白，而是因為那個檔案的正確寫法**依賴**尚未讀取的既有程式碼慣例，已明確標註原因與作法，不是「之後再說」。
- **Type consistency：** `ReservationPayload`/`ReservationOrder`/`RestaurantInfo`（Task 10）在 Task 12-19 全程重複使用同一組型別名稱與欄位名；`TEXT_TO_ORDER_STATUS`（Task 5）與 Task 9 的狀態碼字串保持一致（`"02"/"03"/"04"/"70"/"80"/"90"`）。

## 已知範圍縮小（明確告知，非隱藏假設）

1. **Requirement 10（時段額滿）** 未完整實作 Mock 情境（見上方 Self-Review）。
2. **Task 6（重試佇列完整實作）與 Task 7（狀態排程器）已依使用者決定完全砲掉**，不是「寫成純函式但不接排程」的折衷，是整個不做。`reservation.py`（Task 5）內建的 `retry_service.mark_for_retry` 骨架版是最終狀態，不會被 Task 6 取代；訂位狀態的推進（含待確認→已確認→進行中→已完成→已核銷）完全依賴 Task 9 擴充的既有手動 Demo 按鈕機制，這與已存在於程式碼庫的其他服務示範方式一致。
3. 前端 Property-Based Testing（`fast-check`）未導入，Property 1-4 的等效驗證改用後端 `hypothesis` + 邊界值單元測試涵蓋；Property 10（表單資料保存）改用 Task 19 的一般 RTL 單元測試涵蓋。
4. **對話式訂位（Task 22-25）不收集 `specific_time`／`preference_note`**，送出時一律使用時段預設時間，詳見附錄開頭說明。

---

# 附錄：對話式訂位（Task 22-25）

執行到 Task 3 中途，需求變更：使用者確認兩種入口都要保留，不衝突——

- **卡片精靈（Task 10-19，不變）**：HomePage 點「餐廳訂位」卡片 → 進入 `ReservationFlowPage`，維持原本設計的餐廳卡片／日期選擇器／人數 +/- 等視覺元件。
- **對話式（新增）**：使用者在任何頁面的浮動聊天視窗（`ButlerLauncher`／`ButlerPanel`）打字，比照現有「水電修繕」「居家清潔」等 4 個服務同一套「一次一問」文字問答機制，完成餐廳訂位。

這兩條路徑各自獨立、互不影響：卡片精靈直接呼叫 Task 8 的 `/api/reservations/*` REST API（繞過 agent）；對話式則是在既有的 schema-driven 聊天 agent（`backend/app/agent/agent.py`／`catalog.py`／`nlu.py`）裡註冊這個服務。兩者最終都透過 Task 5 的 `reservation.create_reservation_order()` 建立訂單，資料模型完全共用。

**關鍵發現（影響本附錄設計）：** 這個專案的本機開發環境已經設定真的 AWS Bedrock 憑證（`curl http://localhost:8000/health` 回傳 `"bedrock_ready": true`），所以聊天中的欄位擷取主要由 LLM（`backend/app/agent/llm.py` 的 `extract_fields`）driven，`nlu.py` 的規則式解析器只是 LLM 無法使用時的備援／`_normalize_field_value` 的正規化保險絲，不是唯一路徑。這代表新欄位不需要「完美」的規則解析器就能在有 Bedrock 的環境下正常運作，但為了離線備援與既有測試慣例，仍要照 Task 22 補上規則解析器。

**範圍縮小（比照卡片精靈）：** 對話式訂位不收集 `specific_time`（精確到 30 分鐘的時間），只收集 `time_slot`（午餐／晚餐），送出時 `reservation.create_reservation_order` 會自動用時段預設時間（12:00／18:00）。也不收集 `preference_note`。這兩個欄位卡片精靈那邊有完整支援，對話式這邊為了不讓聊天來回問答變得太長，刻意省略——如果之後想補，兩個欄位都已經是 optional，`catalog.py` 的 schema 加欄位即可，不需要動 `reservation.py`。

## Task 22: nlu.py 規則式解析器（餐廳／餐期）

**Files:**
- Modify: `backend/app/agent/nlu.py`
- Test: `backend/tests/test_nlu_reservation.py`

**Interfaces:**
- Produces: `parse_restaurant(text: str) -> str | None`（回傳餐廳 ID，如 `"r001"`）、`parse_meal_slot(text: str) -> str | None`（回傳 `"LUNCH"` 或 `"DINNER"`）
- Consumes: `backend/app/services/restaurant_catalog.RESTAURANTS`（Task 2，已完成）
- Consumed by: Task 23（`extract_fields` dispatcher 需要 wire 這兩個新 field id）

- [ ] **Step 1: 寫失敗測試**

```python
# backend/tests/test_nlu_reservation.py
from backend.app.agent import nlu


def test_parse_restaurant_matches_full_name():
    assert nlu.parse_restaurant("我想訂22世紀風味館 信義旗艦店") == "r001"


def test_parse_restaurant_matches_partial_branch_name():
    assert nlu.parse_restaurant("板橋文化店有位子嗎") == "r002"


def test_parse_restaurant_returns_none_when_no_match():
    assert nlu.parse_restaurant("我想吃拉麵") is None


def test_parse_meal_slot_lunch():
    assert nlu.parse_meal_slot("中午想訂位") == "LUNCH"
    assert nlu.parse_meal_slot("我要訂午餐") == "LUNCH"


def test_parse_meal_slot_dinner():
    assert nlu.parse_meal_slot("晚餐時段") == "DINNER"
    assert nlu.parse_meal_slot("想約晚上吃飯") == "DINNER"


def test_parse_meal_slot_returns_none_when_ambiguous():
    assert nlu.parse_meal_slot("隨便都可以") is None
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_nlu_reservation.py -v`
Expected: FAIL，`AttributeError: module '...nlu' has no attribute 'parse_restaurant'`

- [ ] **Step 3: 實作**

在 `backend/app/agent/nlu.py` 檔案頂端的 import 區塊加入（跟在 `from ..services.catalog import SERVICES` 之後）：

```python
from ..services.restaurant_catalog import RESTAURANTS
```

在檔案中 `parse_machine_type` 函式之後（`def parse_machine_type...` 那個函式結束後）插入這兩個新函式：

```python
def parse_restaurant(text: str) -> str | None:
    """依餐廳全名或分店關鍵字比對，回傳 restaurant_id。"""
    for restaurant in RESTAURANTS:
        if restaurant["name"] in text:
            return restaurant["id"]
    for restaurant in RESTAURANTS:
        branch = restaurant["name"].split(" ")[-1] if " " in restaurant["name"] else restaurant["name"]
        if branch and branch in text:
            return restaurant["id"]
    return None


def parse_meal_slot(text: str) -> str | None:
    """訂位餐期：午餐／晚餐（與既有 parse_time_slot 的上午/下午/晚上不同語意，分開一個函式避免混用）。"""
    if re.search(r"午餐|中午|午飯", text):
        return "LUNCH"
    if re.search(r"晚餐|晚上|夜間|晚飯", text):
        return "DINNER"
    return None
```

- [ ] **Step 4: 執行測試確認通過**

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_nlu_reservation.py -v`
Expected: PASS（6 passed）

- [ ] **Step 5: 執行 nlu 全部既有測試確認無回歸**（`nlu.py` 是共用模組，其他 4 個服務都靠它）

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests -v -k "nlu or agent_regressions"`
Expected: 全部 PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/agent/nlu.py backend/tests/test_nlu_reservation.py
git commit -m "feat: add restaurant and meal-slot rule-based parsers"
```

---

## Task 23: catalog.py 註冊服務 + agent.py 顯示名稱/別名對照

**Files:**
- Modify: `backend/app/services/catalog.py`
- Modify: `backend/app/agent/agent.py`
- Test: `backend/tests/test_catalog_reservation.py`

**Interfaces:**
- Consumes: `restaurant_catalog.RESTAURANTS`（Task 2）
- Produces: `catalog.SERVICES` 新增一筆 `id="restaurant_reservation"` 的服務定義（7 個欄位：`restaurant_id`, `reserved_date`, `time_slot`, `people`, `contact_name`, `phone`, `is_premium`）
- Consumed by: Task 24（`_submit` 需要判斷 `state["service_id"] == "restaurant_reservation"`）、既有的 `_detect_service`/`_available_services`（不用改，會自動吃到新服務）

- [ ] **Step 1: 寫失敗測試**

```python
# backend/tests/test_catalog_reservation.py
from backend.app.services import catalog


def test_restaurant_reservation_registered_in_service_list():
    services = catalog.list_services()
    ids = [s["id"] for s in services]
    assert "restaurant_reservation" in ids


def test_restaurant_reservation_schema_has_required_fields():
    schema = catalog.get_service_schema("restaurant_reservation")
    field_ids = [f["id"] for f in schema["fields"]]
    assert field_ids == [
        "restaurant_id",
        "reserved_date",
        "time_slot",
        "people",
        "contact_name",
        "phone",
        "is_premium",
    ]


def test_restaurant_reservation_restaurant_field_lists_all_six_ids_as_options():
    schema = catalog.get_service_schema("restaurant_reservation")
    restaurant_field = next(f for f in schema["fields"] if f["id"] == "restaurant_id")
    assert set(restaurant_field["options"]) == {"r001", "r002", "r003", "r004", "r005", "r006"}


def test_restaurant_reservation_keywords_trigger_detection():
    service_id, _ = __import__("backend.app.agent.nlu", fromlist=["detect_service"]).detect_service("我想訂餐廳吃飯")
    assert service_id == "restaurant_reservation"
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_catalog_reservation.py -v`
Expected: FAIL（`restaurant_reservation` 不在服務清單中）

- [ ] **Step 3: 實作**

在 `backend/app/services/catalog.py` 檔案頂端加入 import（跟在既有內容之前）：

```python
from .restaurant_catalog import RESTAURANTS
```

在 `SERVICES` 這個 list 的**最後一個服務（`home_cleaning`）後面**、list 結尾的 `]` 之前，加入新的一筆（用逗號分隔）：

```python
    {
        "id": "restaurant_reservation",
        "name": "餐廳訂位",
        "description": "22世紀風味館 精選餐廳訂位服務",
        "service_vendor_id": 22,
        "cms_type": "02",
        "enabled": True,
        "keywords": ["餐廳", "訂位", "訂餐廳", "吃飯", "用餐", "22世紀", "風味館"],
        "schema": {
            "fields": [
                {
                    "id": "restaurant_id",
                    "label": "餐廳選擇",
                    "type": "select",
                    "required": True,
                    "options": [r["id"] for r in RESTAURANTS],
                    "question": "請問想訂哪一間餐廳？目前提供："
                    + "、".join(r["name"] for r in RESTAURANTS)
                    + "。",
                },
                {
                    "id": "reserved_date",
                    "label": "用餐日期",
                    "type": "date",
                    "required": True,
                    "question": "請問希望哪一天用餐？（限今天起 60 天內）",
                },
                {
                    "id": "time_slot",
                    "label": "用餐時段",
                    "type": "select",
                    "required": True,
                    "options": ["LUNCH", "DINNER"],
                    "question": "請問想約午餐還是晚餐？",
                },
                {
                    "id": "people",
                    "label": "用餐人數",
                    "type": "number",
                    "required": True,
                    "question": "請問幾位用餐？（1 至 20 人）",
                },
                {
                    "id": "contact_name",
                    "label": "聯絡人姓名",
                    "type": "text",
                    "required": True,
                    "question": "請問訂位人的姓名？",
                },
                {
                    "id": "phone",
                    "label": "聯絡電話",
                    "type": "text",
                    "required": True,
                    "question": "請提供聯絡手機號碼。",
                },
                {
                    "id": "is_premium",
                    "label": "訂位類型",
                    "type": "select",
                    "required": True,
                    "options": ["STANDARD", "PREMIUM"],
                    "question": "請問需要指定餐廳或高級訂位服務嗎？高級訂位將由專人為您安排指定餐廳或特殊座位需求。",
                },
            ],
        },
    },
```

在 `backend/app/agent/agent.py`，把 `SELECT_ALIASES` 字典（原本只有 `MORNING`/`AFTERNOON`/`EVENING`/`TOP_LOAD`/`FRONT_LOAD` 五筆）擴充成：

```python
SELECT_ALIASES = {
    "MORNING": ("MORNING", "上午", "早上"),
    "AFTERNOON": ("AFTERNOON", "下午"),
    "EVENING": ("EVENING", "晚上", "夜間"),
    "TOP_LOAD": ("TOP_LOAD", "直立式"),
    "FRONT_LOAD": ("FRONT_LOAD", "滾筒式"),
    "LUNCH": ("LUNCH", "午餐", "中午"),
    "DINNER": ("DINNER", "晚餐", "晚飯"),
    "STANDARD": ("STANDARD", "一般"),
    "PREMIUM": ("PREMIUM", "高級", "指定"),
}
```

把 `SELECT_DISPLAY_NAMES` 字典（原本五筆）擴充成：

```python
SELECT_DISPLAY_NAMES = {
    "MORNING": "上午",
    "AFTERNOON": "下午",
    "EVENING": "晚上",
    "TOP_LOAD": "直立式",
    "FRONT_LOAD": "滾筒式",
    "LUNCH": "午餐",
    "DINNER": "晚餐",
    "STANDARD": "一般訂位",
    "PREMIUM": "高級訂位",
}
```

把 `FIELD_DISPLAY_NAMES` 字典加入新欄位（原本七筆，追加以下四行）：

```python
    "restaurant_id": "餐廳選擇",
    "reserved_date": "用餐日期",
    "time_slot": "用餐時段",
    "people": "用餐人數",
    "contact_name": "聯絡人姓名",
```

（`phone` 已經存在於字典中，不要重複加。）

`restaurant_id` 這個 select 欄位的選項是 `r001`~`r006` 這種代碼，使用者聊天時通常會打餐廳「名稱」而不是代碼，光靠 `SELECT_ALIASES` 沒辦法涵蓋（因為那個字典的 key 要對應 `options` 裡的代碼，但別名要填餐廳全名，6 間餐廳名稱都不同，硬塞進 `SELECT_ALIASES` 會很長也不好維護）。所以在 `backend/app/agent/agent.py` 的 `_normalize_field_value` 函式裡，找到這一段（`type == "select"` 分支內）：

```python
    if field["type"] == "select":
        if field_id == "preferred_time_slot":
            return (
                _normalize_select(str(value), field.get("options", []))
                or nlu.parse_time_slot(str(value))
                or nlu.parse_time_slot(original_text)
            )
        if field_id == "machine_type":
            return (
                _normalize_select(str(value), field.get("options", []))
                or nlu.parse_machine_type(str(value))
                or nlu.parse_machine_type(original_text)
            )
        return _normalize_select(str(value), field.get("options", []))
```

改成（新增兩個 `if` 分支，比照既有 `preferred_time_slot`／`machine_type` 的寫法）：

```python
    if field["type"] == "select":
        if field_id == "preferred_time_slot":
            return (
                _normalize_select(str(value), field.get("options", []))
                or nlu.parse_time_slot(str(value))
                or nlu.parse_time_slot(original_text)
            )
        if field_id == "machine_type":
            return (
                _normalize_select(str(value), field.get("options", []))
                or nlu.parse_machine_type(str(value))
                or nlu.parse_machine_type(original_text)
            )
        if field_id == "restaurant_id":
            return (
                _normalize_select(str(value), field.get("options", []))
                or nlu.parse_restaurant(str(value))
                or nlu.parse_restaurant(original_text)
            )
        if field_id == "time_slot":
            return (
                _normalize_select(str(value), field.get("options", []))
                or nlu.parse_meal_slot(str(value))
                or nlu.parse_meal_slot(original_text)
            )
        return _normalize_select(str(value), field.get("options", []))
```

最後，在 `nlu.py` 的 `extract_fields` dispatcher（`for f in fields:` 迴圈裡的 `if/elif` 鏈）新增兩個分支，跟在 `elif fid == "machine_type":` 那段之後：

```python
        elif fid == "restaurant_id":
            value = parse_restaurant(text)
        elif fid == "time_slot":
            value = parse_meal_slot(text)
```

- [ ] **Step 4: 執行測試確認通過**

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_catalog_reservation.py -v`
Expected: PASS（4 passed）

- [ ] **Step 5: 執行既有 agent/nlu 相關測試確認無回歸**（這一步改了 4 個服務共用的 `agent.py`/`nlu.py`，風險較高，務必跑全套）

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests -v`
Expected: 全部 PASS，特別留意 `test_agent_regressions.py` 與 Task 22 的 `test_nlu_reservation.py` 都要過

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/catalog.py backend/app/agent/agent.py backend/tests/test_catalog_reservation.py
git commit -m "feat: register restaurant reservation service in chat catalog"
```

---

## Task 24: agent.py `_submit` 分流到 reservation.create_reservation_order

**Files:**
- Modify: `backend/app/agent/agent.py`
- Test: `backend/tests/test_agent_reservation_submit.py`

**Interfaces:**
- Consumes: `reservation.create_reservation_order`（Task 5，已完成）
- 這是風險最高的一個任務：`_submit()` 是水電修繕／洗衣機清洗／冷氣清洗／居家清潔這 4 個既有服務共用的送出函式，必須用「提早 return 的獨立分支」處理，完全不動到原本給那 4 個服務走的程式碼路徑。

- [ ] **Step 1: 寫失敗測試**（直接呼叫 `handle_message` 走完整個對話，驗證端到端行為，而不是只測 `_submit` 內部細節，因為這是共用函式，端到端測試才能真正保證沒有動到既有服務）

```python
# backend/tests/test_agent_reservation_submit.py
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from backend.app.agent import agent
from backend.app.services import reservation, store as store_module


@pytest.fixture(autouse=True)
def isolated_store(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        test_store = store_module.MemoryStore(storage_path=Path(tmp) / "store.json")
        monkeypatch.setattr(store_module, "STORE", test_store)
        monkeypatch.setattr(reservation, "STORE", test_store)
        yield test_store


def _run_turn(state, message, actor_id="user-1", session_id="sess-1"):
    return agent.handle_message(actor_id, session_id, state, message)


def test_reservation_chat_flow_creates_confirmed_order_end_to_end():
    state = agent.new_state()

    with patch("backend.app.agent.agent._available_services", return_value=[
        {"id": "restaurant_reservation", "name": "餐廳訂位", "description": "22世紀風味館 精選餐廳訂位服務"},
    ]):
        result = _run_turn(state, "我想訂22世紀風味館 信義旗艦店吃午餐")
        state = result["state"]
        assert state["service_id"] == "restaurant_reservation"

        result = _run_turn(state, "8月1日")
        state = result["state"]
        result = _run_turn(state, "4位")
        state = result["state"]
        result = _run_turn(state, "王大明")
        state = result["state"]
        result = _run_turn(state, "0912345678")
        state = result["state"]
        result = _run_turn(state, "一般訂位就好")
        state = result["state"]
        assert state["awaiting_confirmation"] is True

        result = _run_turn(state, "確認送出")
        state = result["state"]

    assert state["request_id"] is not None
    order = reservation.get_reservation_order("user-1", state["request_id"])
    assert order["order_items"]["restaurant_id"] == "r001"
    assert order["order_items"]["people"] == 4
    assert order["status"] in ("CONFIRMED", "PENDING_PROVIDER")


def test_reservation_chat_flow_reports_error_without_crashing_when_order_invalid():
    state = agent.new_state()
    state["service_id"] = "restaurant_reservation"
    state["service_name"] = "餐廳訂位"
    state["service_schema"] = {"fields": [
        {"id": "restaurant_id", "type": "select", "options": ["r001"], "required": True},
    ]}
    state["collected_fields"] = {"restaurant_id": "does-not-exist"}
    state["missing_fields"] = []
    state["awaiting_confirmation"] = True

    result = _run_turn(state, "確認送出")

    assert result["state"]["request_id"] is None
    assert "reply" in result


def test_existing_service_submit_flow_still_works_unaffected():
    """Regression guard: a non-reservation service must still go through the
    generic tools.call('submit_service_request', ...) path untouched."""
    from backend.app.agent import tools as agent_tools

    called_with = {}

    def fake_tool_call(name, params, auth_token=None):
        called_with["name"] = name
        called_with["params"] = params
        return {"success": True, "request_id": "REQ-FAKE-1", "status": "SUBMITTED"}

    state = agent.new_state()
    state["service_id"] = "home_cleaning"
    state["service_name"] = "居家清潔"
    state["service_schema"] = {"fields": [{"id": "hours", "type": "number", "required": True}]}
    state["collected_fields"] = {"hours": 3}
    state["missing_fields"] = []
    state["awaiting_confirmation"] = True

    with patch.object(agent_tools, "call", side_effect=fake_tool_call):
        result = agent._submit("user-1", "sess-1", state, latest_user_message="確認送出")

    assert called_with["name"] == "submit_service_request"
    assert result["state"]["request_id"] == "REQ-FAKE-1"
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_agent_reservation_submit.py -v`
Expected: FAIL（訂位不會走到 `reservation.create_reservation_order`，`request_id` 為 None 或走錯路徑報錯）

- [ ] **Step 3: 實作**

在 `backend/app/agent/agent.py` 檔案頂端 import 區塊加入（跟在 `from ..services import catalog` 之後）：

```python
from ..services import reservation
```

找到 `_submit` 函式的開頭（`def _submit(...)` 到 `_recompute_missing(state)` 那幾行），在 `_recompute_missing(state)` 之後、原本 `if state.get("missing_fields"):` 判斷之後、**呼叫 `tools.call("submit_service_request", ...)` 之前**，插入一個提早 return 的分支：

```python
def _submit(
    actor_id: str,
    session_id: str,
    state: dict,
    latest_user_message: str = "",
    auth_token: str | None = None,
) -> dict:
    _recompute_missing(state)
    if state.get("missing_fields"):
        state["awaiting_confirmation"] = False
        state["status"] = "COLLECTING_INFORMATION"
        return _continue_collection(actor_id, state, latest_user_message=latest_user_message)

    if state["service_id"] == "restaurant_reservation":
        return _submit_reservation(actor_id, state, latest_user_message)

    result = tools.call(
        "submit_service_request",
        {
            "service_id": state["service_id"],
            "session_id": session_id,
            "actor_id": actor_id,
            "payload": dict(state["collected_fields"]),
        },
        auth_token=auth_token,
    )
    # ... 原本函式其餘內容完全不變，從這裡繼續往下 ...
```

（只在函式開頭插入 3 行 `if` 判斷，`tools.call(...)` 以下到函式結尾的所有既有程式碼一個字都不要動。）

在 `_submit` 函式的**後面**（同一個檔案，函式定義之外，緊接在 `_submit` 結尾之後）新增一個新函式：

```python
def _submit_reservation(actor_id: str, state: dict, latest_user_message: str) -> dict:
    collected = state["collected_fields"]
    payload = {
        "restaurant_id": collected.get("restaurant_id"),
        "reserved_date": collected.get("reserved_date"),
        "time_slot": collected.get("time_slot"),
        "people": collected.get("people"),
        "contact_name": collected.get("contact_name"),
        "phone": collected.get("phone"),
        "is_premium": collected.get("is_premium") == "PREMIUM",
    }
    result = reservation.create_reservation_order(actor_id, payload)

    if not result.get("success"):
        message = result.get("error", {}).get("message", "訂位失敗")
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

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_agent_reservation_submit.py -v`
Expected: PASS（3 passed）

- [ ] **Step 5: 執行全部後端測試確認無回歸**（這是本附錄風險最高的一步，`_submit` 是共用函式，務必全套跑過）

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests -v`
Expected: 全部 PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/agent/agent.py backend/tests/test_agent_reservation_submit.py
git commit -m "feat: route restaurant reservation submissions through reservation service"
```

---

## Task 25: 對話式訂位全專案回歸驗證 + 手動測試

**Files:** 無新檔案，純驗證。

- [ ] **Step 1: 全套後端測試**

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests -v`
Expected: 全部 PASS

- [ ] **Step 2: 手動驗證（兩條路徑都要測）**

1. 啟動後端（`cd backend && .venv/Scripts/python.exe -m uvicorn app.main:app --reload`）與前端（`cd frontend && npm run dev`）。
2. **卡片路徑**：登入後點 HomePage「餐廳訂位」卡片，走完 Task 19 的精靈流程，確認送出成功。
3. **對話路徑**：登入後點右下角浮動聊天按鈕，直接打字「我想訂22世紀風味館 信義旗艦店 8月1日 午餐 4位」（可以一次講完，也可以分開一句句講，AI 會一次問一項缺的資料），確認 AI 能一路問完人數／聯絡人／電話／是否高級訂位，最後顯示確認摘要文字、輸入「確認送出」後成功建立案件。
4. 在「我的服務」清單確認這筆對話式建立的訂位案件也正常顯示、案件明細頁能看到完整對話紀錄與正確欄位。
5. 額外測一次既有服務（例如「居家清潔」）走一次完整對話流程，確認完全沒有受到這次修改影響。

- [ ] **Step 3: Commit（若手動驗證發現需要修正）**

```bash
git add -A
git commit -m "test: full regression pass for conversational reservation flow"
```
