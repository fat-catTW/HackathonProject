# 廠商後台完整案件生命週期 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把通用服務案件、美食外送、商城實體商品三種訂單的狀態推進動作，從「使用者自己按按鈕模擬」移到「登入對應廠商帳號後，經狀態機與樂觀鎖驗證才能推進」，並拿掉三個使用者端的 Demo 模擬端點。

**Architecture:** 三種案件共用既有的廠商驗證（`get_current_vendor`）、`VENDOR#{id}` 索引查詢與樂觀鎖寫入（`save_request_if_version`）機制。通用案件延伸既有 `vendor.py` 的狀態機；外送與商城因為狀態欄位形狀不同，各自開一組新的 `/api/vendor/delivery-orders`、`/api/vendor/shop-orders` 端點，但沿用同樣的驗證與儲存機制，不重複發明。前端三種案件共用同一套廠商後台頁面元件，只是依登入的 `vendor_id` 決定要打哪一組 API。

**Tech Stack:** FastAPI（Python 3.12）＋ pytest／TestClient；React ＋ TypeScript ＋ Vitest／Testing Library。

## Global Constraints

- 廠商帳號密碼一律沿用既有 demo 帳號慣例：`vendor1234`
- 所有新端點都掛在 `/api/vendor/` 前綴下，用 `get_current_vendor` 驗證身分
- 案件歸屬一律靠 `VENDOR#{vendor.vendor_id}` 索引查詢決定，不寫死特定 vendor_id 的檢查
- 樂觀鎖寫入一律用 `STORE.save_request_if_version`，衝突回 409 並帶回案件現況（沿用 `vendor.py` 既有的 `_fail` 回應格式：`{"success": false, "error": {"code", "message", ...現況欄位}}`）
- 每個 task 完成後才進下一個 task；每個 task 結尾都要跑對應測試全綠才能 commit

---

## Task 1：通用服務案件狀態機補完（開始／完成／核銷）

**Files:**
- Modify: `backend/app/services/statuses.py`
- Modify: `backend/app/api/vendor.py`
- Modify: `backend/app/config.py`
- Test: `backend/tests/test_vendor_portal.py`

**Interfaces:**
- Produces: `VENDOR_TRANSITIONS` 新增 `start`／`complete`／`verify` 三個 key；`VendorTransition` 多一個 `applicable_services: frozenset[str] | None = None` 欄位；`vendor.py` 的 `_available_actions(status: str, service_id: str) -> list[str]` 簽章改變（後面所有 task 都不會再呼叫這個函式，此改動只影響 task 內部）

- [ ] **Step 1: 寫失敗測試**

在 `backend/tests/test_vendor_portal.py` 檔案最上方新增一個帳號常數（緊接在既有 `VENDOR_PLUMBING` 後面）：

```python
VENDOR_RESERVATION = ("vendor22@demo.local", "vendor1234")  # service_vendor_id = 22
```

把既有的 `test_unknown_action_is_rejected` 改成用一個不會被新狀態機吃到的動作名稱（原本用 `"complete"` 測試「未知動作」，但這個 task 之後 `complete` 會變成合法動作）：

```python
def test_unknown_action_is_rejected(client):
    request_id = submit_air_conditioner_request(client)
    token = vendor_token(client, VENDOR_CLEANING)
    res = vendor_act(client, token, request_id, "explode", 1)
    assert res.status_code == 422
```

在檔案最後追加三個新測試：

```python
def test_vendor_advances_full_lifecycle_for_generic_service(client):
    request_id = submit_air_conditioner_request(client)
    token = vendor_token(client, VENDOR_CLEANING)

    accept = vendor_act(client, token, request_id, "accept", vendor_detail(client, token, request_id)["version"])
    assert accept.status_code == 200, accept.text
    assert accept.json()["available_actions"] == ["start"]

    start = vendor_act(client, token, request_id, "start", accept.json()["version"])
    assert start.status_code == 200, start.text
    assert start.json()["status"] == "IN_PROGRESS"
    assert start.json()["available_actions"] == ["complete"]

    complete = vendor_act(client, token, request_id, "complete", start.json()["version"])
    assert complete.status_code == 200, complete.text
    assert complete.json()["status"] == "COMPLETED"
    # 冷氣清洗沒有核銷概念，完工後沒有可再做的動作
    assert complete.json()["available_actions"] == []


def test_verify_action_is_only_available_for_restaurant_reservation(client):
    request_id = submit_air_conditioner_request(client)
    token = vendor_token(client, VENDOR_CLEANING)
    version = vendor_detail(client, token, request_id)["version"]

    for action in ("accept", "start", "complete"):
        res = vendor_act(client, token, request_id, action, version)
        assert res.status_code == 200, res.text
        version = res.json()["version"]

    verify = vendor_act(client, token, request_id, "verify", version)
    assert verify.status_code == 409
    assert verify.json()["detail"]["error"]["code"] == "REQUEST_STATUS_CONFLICT"


def test_reservation_vendor_can_verify_after_completion(client):
    submitted = client.post(
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
        headers=auth(RESIDENT_TOKEN),
    ).json()
    assert submitted["status"] == "PENDING_PROVIDER"
    request_id = submitted["request_id"]

    token = vendor_token(client, VENDOR_RESERVATION)
    version = vendor_detail(client, token, request_id)["version"]
    for action, expected_order_status in (("accept", "03"), ("start", "04"), ("complete", "70")):
        step = vendor_act(client, token, request_id, action, version)
        assert step.status_code == 200, step.text
        version = step.json()["version"]

    verify = vendor_act(client, token, request_id, "verify", version)
    assert verify.status_code == 200, verify.text
    assert verify.json()["status"] == "VERIFIED"
    assert verify.json()["available_actions"] == []

    order = client.get(f"/api/reservations/{request_id}", headers=auth(RESIDENT_TOKEN)).json()
    assert order["order_status"] == "80"
    assert order["status_history"][-1]["status"] == "80"
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `cd backend && python -m pytest tests/test_vendor_portal.py -v`
Expected: `test_vendor_advances_full_lifecycle_for_generic_service`、`test_verify_action_is_only_available_for_restaurant_reservation`、`test_reservation_vendor_can_verify_after_completion` 都因為 `start`/`complete`/`verify` 還不是合法動作而回 422，斷言失敗；`test_reservation_vendor_can_verify_after_completion` 另外會在 `vendor_token(client, VENDOR_RESERVATION)` 這一步就先失敗（401，因為 vendor22 帳號還不存在）

- [ ] **Step 3: 實作**

在 `backend/app/config.py` 的 `_BUILTIN_VENDOR_ACCOUNTS` 字典（第 29-45 行）新增一筆帳號：

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
    "vendor22@demo.local": {
        "vendor_id": 22,
        "name": "22世紀風味館",
        "password": "vendor1234",
    },
}
```

在 `backend/app/services/statuses.py` 把 `VendorTransition` 與 `VENDOR_TRANSITIONS` 改成：

```python
class VendorTransition(NamedTuple):
    """廠商後台允許的一次狀態切換。"""

    sources: frozenset[str]
    target: str
    label: str
    # None 代表所有服務都適用；非 None 時只有列出的 service_id 能做這個動作。
    applicable_services: frozenset[str] | None = None


# 廠商端的狀態機：只有列在這裡的 (動作, 來源狀態) 組合可以切換，其餘一律 409。
# 住戶已取消、已完工、或別的廠商動作先落地時，來源狀態就對不上了。
VENDOR_TRANSITIONS: dict[str, VendorTransition] = {
    "accept": VendorTransition(frozenset(VENDOR_PENDING_STATUSES), "CONFIRMED", "接單"),
    "reject": VendorTransition(frozenset(VENDOR_PENDING_STATUSES), "REJECTED", "拒單"),
    "start": VendorTransition(frozenset({"CONFIRMED"}), "IN_PROGRESS", "開始服務"),
    "complete": VendorTransition(frozenset({"IN_PROGRESS"}), "COMPLETED", "完成服務"),
    # 核銷只有餐廳訂位有意義（現場核對已到店用餐），其餘服務完工即結案，不會變成 VERIFIED。
    "verify": VendorTransition(
        frozenset({"COMPLETED"}), "VERIFIED", "核銷", frozenset({"restaurant_reservation"})
    ),
}
```

在 `backend/app/api/vendor.py`：

把 import 那行（第 26 行）：
```python
from ..services.store import STORE, vendor_id_of, version_of
```
改成：
```python
from ..services.store import STORE, now_iso, vendor_id_of, version_of
```

把 `_available_actions`（第 84-86 行）改成：

```python
def _available_actions(status: str, service_id: str) -> list[str]:
    """這個狀態現在可以做的動作；前端不必自己複製一份狀態機。"""
    return [
        name
        for name, t in VENDOR_TRANSITIONS.items()
        if status in t.sources and (t.applicable_services is None or service_id in t.applicable_services)
    ]
```

`_to_list_item`（第 89-104 行）裡的這一行：
```python
        "available_actions": _available_actions(status),
```
改成：
```python
        "available_actions": _available_actions(status, item.get("service_id", "")),
```

`_detail_payload`（第 187-205 行）裡同樣的一行：
```python
        "available_actions": _available_actions(status),
```
改成：
```python
        "available_actions": _available_actions(status, request.get("service_id", "")),
```

`act_on_vendor_request`（第 214-245 行）整個改成：

```python
@router.post("/requests/{request_id}/{action}")
def act_on_vendor_request(
    body: VendorActionIn,
    request_id: str,
    action: str = Path(pattern="^(accept|reject|start|complete|verify)$"),
    vendor: CurrentUser = Depends(get_current_vendor),
):
    """接單／拒單／開始／完成／核銷：狀態機決定能不能切，樂觀鎖確保沒有人搶先改過。"""
    owner_id, request = _load_case_or_404(vendor.vendor_id, request_id)
    transition = VENDOR_TRANSITIONS[action]
    status = request.get("status", "")
    service_id = request.get("service_id", "")
    eligible = status in transition.sources and (
        transition.applicable_services is None or service_id in transition.applicable_services
    )

    if not eligible:
        # 例如住戶已取消、另一位同事剛按過接單、或這個服務根本沒有核銷這個動作。
        raise _fail(
            409,
            "REQUEST_STATUS_CONFLICT",
            f"案件目前是「{status_label(status)}」，無法{transition.label}。",
            _detail_payload(owner_id, request),
        )

    updated = dict(request) | {"status": transition.target}
    if "order_items" in updated:
        # 餐廳訂位案件另外維護一份兩位數 order_status／歷程，要跟 status 同步推進，
        # 否則住戶端看到的 order_status 會卡在舊狀態（沿用原本 simulate 端點的邏輯）。
        from ..services.reservation import TEXT_TO_ORDER_STATUS

        order_status = TEXT_TO_ORDER_STATUS.get(transition.target)
        if order_status:
            updated["order_status"] = order_status
            updated.setdefault("status_history", []).append({"status": order_status, "at": now_iso()})

    if not STORE.save_request_if_version(owner_id, updated, body.version):
        # 版本對不上：狀態檢查到寫入之間有人改過，或這是重複送出的同一個按鈕。
        _, current = _load_case_or_404(vendor.vendor_id, request_id)
        raise _fail(
            409,
            "REQUEST_VERSION_CONFLICT",
            "案件已被更新，請重新整理後再操作。",
            _detail_payload(owner_id, current),
        )
    return {"success": True, **_detail_payload(owner_id, updated)}
```

- [ ] **Step 4: 跑測試確認通過**

Run: `cd backend && python -m pytest tests/test_vendor_portal.py -v`
Expected: 全部通過（含既有的 20 個測試與新增的 3 個）

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/statuses.py backend/app/api/vendor.py backend/app/config.py backend/tests/test_vendor_portal.py
git commit -m "feat: complete vendor state machine with start/complete/verify transitions"
```

---

## Task 2：拿掉通用案件的使用者端模擬端點

**Files:**
- Modify: `backend/app/api/requests.py`
- Modify: `backend/tests/test_vendor_portal.py`
- Modify: `backend/tests/test_requests_simulate_reservation.py`

**Interfaces:**
- Consumes: Task 1 的 `POST /api/vendor/requests/{id}/accept`
- Produces: `POST /api/requests/{id}/simulate/{status}` 端點不再存在（回 404）

- [ ] **Step 1: 寫失敗測試**

把 `backend/tests/test_vendor_portal.py` 裡的 `test_status_change_propagates_to_vendor_list` 改成用廠商接單觸發狀態變化，而不是呼叫即將刪除的模擬端點：

```python
def test_status_change_propagates_to_vendor_list(client):
    request_id = submit_air_conditioner_request(client)
    token = vendor_token(client, VENDOR_CLEANING)

    pending = client.get("/api/vendor/requests?scope=pending", headers=auth(token))
    assert request_id in [i["request_id"] for i in pending.json()["items"]]

    version = vendor_detail(client, token, request_id)["version"]
    confirmed = vendor_act(client, token, request_id, "accept", version)
    assert confirmed.status_code == 200

    orders = client.get("/api/vendor/requests?scope=orders", headers=auth(token))
    order = next(i for i in orders.json()["items"] if i["request_id"] == request_id)
    assert order["status"] == "CONFIRMED"
    pending_after = client.get("/api/vendor/requests?scope=pending", headers=auth(token))
    assert request_id not in [i["request_id"] for i in pending_after.json()["items"]]
```

把整份 `backend/tests/test_requests_simulate_reservation.py` 換成：

```python
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services import reservation, store as store_module
from backend.app.api import requests as requests_module
from backend.app.api import vendor as vendor_module


@pytest.fixture(autouse=True)
def isolated_store(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        test_store = store_module.MemoryStore(storage_path=Path(tmp) / "store.json")
        monkeypatch.setattr(store_module, "STORE", test_store)
        monkeypatch.setattr(reservation, "STORE", test_store)
        monkeypatch.setattr(requests_module, "STORE", test_store)
        # test_vendor_accept_syncs_order_status_for_reservation 會打 /api/vendor/requests/...，
        # vendor.py 也直接引用 STORE，同樣要換成隔離的測試用 store。
        monkeypatch.setattr(vendor_module, "STORE", test_store)
        yield test_store


def _submit_reservation(client: TestClient, headers: dict) -> dict:
    return client.post(
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


def test_customer_simulate_endpoint_is_removed():
    client = TestClient(app)
    accounts = client.get("/api/auth/demo-accounts").json()["accounts"]
    headers = {"Authorization": f"Bearer {accounts[0]['token']}"}

    created = _submit_reservation(client, headers)
    response = client.post(f"/api/requests/{created['request_id']}/simulate/CONFIRMED", headers=headers)
    assert response.status_code == 404


def test_vendor_accept_syncs_order_status_for_reservation():
    client = TestClient(app)
    accounts = client.get("/api/auth/demo-accounts").json()["accounts"]
    headers = {"Authorization": f"Bearer {accounts[0]['token']}"}

    created = _submit_reservation(client, headers)
    assert created["status"] == "PENDING_PROVIDER"

    vendor_login = client.post(
        "/api/vendor/login", json={"email": "vendor22@demo.local", "password": "vendor1234"}
    ).json()
    vendor_headers = {"Authorization": f"Bearer {vendor_login['token']}"}

    detail = client.get(
        f"/api/vendor/requests/{created['request_id']}", headers=vendor_headers
    ).json()
    accept = client.post(
        f"/api/vendor/requests/{created['request_id']}/accept",
        json={"version": detail["version"]},
        headers=vendor_headers,
    )
    assert accept.status_code == 200, accept.text

    order = client.get(f"/api/reservations/{created['request_id']}", headers=headers).json()
    assert order["status"] == "CONFIRMED"
    assert order["order_status"] == "03"
    assert order["status_history"][-1]["status"] == "03"
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `cd backend && python -m pytest tests/test_vendor_portal.py tests/test_requests_simulate_reservation.py -v`
Expected: `test_status_change_propagates_to_vendor_list` 通過（端點還沒刪，`accept` 已經在 Task 1 實作好了，這步其實不會紅——這是把測試改成更正確的驅動方式，不是紅燈重構）；`test_customer_simulate_endpoint_is_removed` 失敗，因為端點還在（回 200 不是 404）

- [ ] **Step 3: 實作**

在 `backend/app/api/requests.py`，刪掉第 106～131 行（`simulate_status` 函式與它前面的空行，到檔案結尾），讓檔案在 `cancel_request` 函式（結束於第 104 行）後直接結束。

- [ ] **Step 4: 跑測試確認通過**

Run: `cd backend && python -m pytest tests/test_vendor_portal.py tests/test_requests_simulate_reservation.py -v`
Expected: 全部通過

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/requests.py backend/tests/test_vendor_portal.py backend/tests/test_requests_simulate_reservation.py
git commit -m "fix: remove customer-facing status-simulation endpoint for generic requests"
```

---

## Task 3：前端拿掉通用案件的模擬按鈕

**Files:**
- Modify: `frontend/src/api/requests.ts`
- Modify: `frontend/src/pages/RequestDetailPage.tsx`

**Interfaces:**
- Consumes: 無（純移除）

- [ ] **Step 1: 移除 API 函式**

在 `frontend/src/api/requests.ts` 刪掉 `simulateStatus` 函式（第 19-24 行）：

```typescript
export function simulateStatus(requestId: string, next: string) {
  return api<{ success: boolean; status: string }>(
    `/api/requests/${requestId}/simulate/${next}`,
    { method: "POST" },
  );
}
```

- [ ] **Step 2: 移除前端按鈕**

在 `frontend/src/pages/RequestDetailPage.tsx`：

把 import 那行（第 4 行）：
```typescript
import { cancelRequest, getRequest, simulateStatus } from "../api/requests";
```
改成：
```typescript
import { cancelRequest, getRequest } from "../api/requests";
```

刪掉 `nextDemo`／`isReservation`／`demo` 這段（第 82-93 行）：
```typescript
  const nextDemo: Record<string, { to: string; label: string }> = {
    SUBMITTED: { to: "CONFIRMED", label: "Demo：模擬廠商已確認" },
    PENDING_PROVIDER: { to: "CONFIRMED", label: "Demo：模擬廠商已確認" },
    AWAITING_QUOTE: { to: "CONFIRMED", label: "Demo：模擬廠商已報價確認" },
    CONFIRMED: { to: "IN_PROGRESS", label: "Demo：模擬服務進行中" },
    IN_PROGRESS: { to: "COMPLETED", label: "Demo：模擬服務已完成" },
  };
  const isReservation = detail.service_id === "restaurant_reservation";
  if (isReservation && detail.status === "COMPLETED") {
    nextDemo.COMPLETED = { to: "VERIFIED", label: "Demo：模擬已核銷" };
  }
  const demo = nextDemo[detail.status];
```

刪掉渲染模擬按鈕的區塊（第 215-223 行）：
```tsx
            {demo && (
              <button
                type="button"
                onClick={() => simulateStatus(detail.request_id, demo.to).then(load)}
                className="w-full rounded-2xl border-2 border-brand px-6 py-3.5 font-bold text-brand"
              >
                {demo.label}
              </button>
            )}
```

- [ ] **Step 3: 跑前端型別檢查與建置確認沒有殘留參照**

Run: `cd frontend && npm run build`
Expected: 建置成功，沒有 `simulateStatus` 未定義或未使用的錯誤

- [ ] **Step 4: Commit**

```bash
git add frontend/src/api/requests.ts frontend/src/pages/RequestDetailPage.tsx
git commit -m "fix: remove customer-facing demo status button from request detail page"
```

---

## Task 4：廠商後台動作按鈕改成動態渲染

**Files:**
- Modify: `frontend/src/types/vendor.ts`
- Modify: `frontend/src/pages/VendorRequestDetailPage.tsx`

**Interfaces:**
- Consumes: Task 1 產生的 `available_actions` 內容（現在可能是 `accept`/`reject`/`start`/`complete`/`verify` 任意組合）
- Produces: `VendorAction` 型別擴充為涵蓋全部三種案件動作的聯集，供 Task 7、Task 10 沿用

- [ ] **Step 1: 擴充型別**

在 `frontend/src/types/vendor.ts` 把：
```typescript
export type VendorAction = "accept" | "reject";
```
改成：
```typescript
export type VendorAction =
  | "accept"
  | "reject"
  | "start"
  | "complete"
  | "verify"
  | "prepare"
  | "pickup"
  | "dispatch"
  | "deliver"
  | "confirm"
  | "ship";
```

- [ ] **Step 2: 動態渲染動作按鈕**

在 `frontend/src/pages/VendorRequestDetailPage.tsx` 把：
```typescript
const ACTION_LABELS: Record<VendorAction, string> = {
  accept: "接單",
  reject: "婉拒",
};

const DONE_MESSAGES: Record<VendorAction, string> = {
  accept: "已接下這張單，狀態更新為「已確認」。",
  reject: "已婉拒這張單。",
};
```
改成：
```typescript
const ACTION_LABELS: Record<VendorAction, string> = {
  accept: "接單",
  reject: "婉拒",
  start: "開始服務",
  complete: "完成服務",
  verify: "核銷",
  prepare: "開始備餐",
  pickup: "外送員已取餐",
  dispatch: "開始配送",
  deliver: "送達",
  confirm: "確認訂單",
  ship: "出貨",
};

const DONE_MESSAGES: Record<VendorAction, string> = {
  accept: "已接下這張單，狀態更新為「已確認」。",
  reject: "已婉拒這張單。",
  start: "已標記開始服務。",
  complete: "已標記完成服務。",
  verify: "已完成核銷。",
  prepare: "已標記開始備餐。",
  pickup: "已標記外送員取餐。",
  dispatch: "已標記開始配送。",
  deliver: "已標記送達。",
  confirm: "已確認訂單。",
  ship: "已標記出貨。",
};

// 拒絕／婉拒類動作破壞性較高，按下前要跳確認彈窗；其餘動作直接執行。
const DESTRUCTIVE_ACTIONS: VendorAction[] = ["reject"];
```

把渲染動作按鈕的區塊（第 175-202 行，從 `{detail.available_actions.length > 0 ? (` 到對應的 `)}`）整個改成：

```tsx
          {detail.available_actions.length > 0 ? (
            <section className="mt-5 flex flex-col gap-3 sm:flex-row">
              {detail.available_actions.map((action) =>
                DESTRUCTIVE_ACTIONS.includes(action) ? (
                  <button
                    key={action}
                    type="button"
                    onClick={() => setConfirmingReject(true)}
                    disabled={acting !== null}
                    className="flex-1 rounded-2xl border-2 border-[var(--color-border)] bg-[var(--color-surface)] px-6 py-4 text-lg font-bold text-[var(--color-muted-foreground)] transition hover:border-danger hover:text-danger disabled:opacity-50"
                  >
                    {acting === action ? "處理中…" : ACTION_LABELS[action]}
                  </button>
                ) : (
                  <button
                    key={action}
                    type="button"
                    onClick={() => runAction(action)}
                    disabled={acting !== null}
                    className="flex-1 rounded-2xl bg-brand px-6 py-4 text-lg font-black text-white shadow-sm transition hover:brightness-105 disabled:opacity-50"
                  >
                    {acting === action ? "處理中…" : ACTION_LABELS[action]}
                  </button>
                ),
              )}
            </section>
          ) : (
            <p className="mt-5 text-center text-sm text-[var(--color-muted-foreground)]">
              這張單目前是「{detail.status_label}」，沒有可以執行的動作。
            </p>
          )}
```

把確認彈窗（第 206-216 行）裡寫死的 `reject` 文案改成引用 `ACTION_LABELS.reject`（已經是這樣寫，不用改），但要把 `onConfirm` 改成呼叫目前正在確認的動作而不是寫死 `"reject"`——因為 `DESTRUCTIVE_ACTIONS` 目前只有一個成員，先簡化維持寫死 `"reject"` 沒有行為差異，不用改這段。

- [ ] **Step 3: 跑前端建置與既有測試**

Run: `cd frontend && npm run build && npx vitest run src/pages/VendorPages.visual.test.tsx`
Expected: 建置成功；`VendorPages.visual.test.tsx` 全部通過（該檔案 mock 的 `available_actions` 是空陣列，不受動態渲染影響）

- [ ] **Step 4: Commit**

```bash
git add frontend/src/types/vendor.ts frontend/src/pages/VendorRequestDetailPage.tsx
git commit -m "feat: render vendor action buttons dynamically from available_actions"
```

---

## Task 5：外送廠商帳號與可重用的狀態套用函式

**Files:**
- Modify: `backend/app/config.py`
- Modify: `backend/app/services/delivery.py`
- Test: `backend/tests/test_delivery_service.py`

**Interfaces:**
- Produces: `delivery.apply_vendor_status(order: dict, vendor_status: int, delivery_info: dict | None = None) -> dict | None`——純函式，回傳套用後的訂單 dict（不寫入 STORE），代碼不合法回 `None`。Task 6 的新端點會用它 + `save_request_if_version`。

- [ ] **Step 1: 寫失敗測試**

在 `backend/tests/test_delivery_service.py` 新增（若檔案不存在就新建，並加上跟其他 service 測試一致的 import：`from backend.app.services import delivery`）：

```python
def test_apply_vendor_status_returns_updated_order_without_saving():
    order = {
        "request_id": "REQ-1",
        "status": "PENDING",
        "order_status": "01",
        "vendor_data": {"delivery": None, "order_status": None},
        "status_history": [{"status": "01", "at": "2026-08-01T00:00:00+08:00"}],
    }
    updated = delivery.apply_vendor_status(order, 1)
    assert updated is not None
    assert updated["order_status"] == "02"
    assert updated["status"] == "IN_PROGRESS"
    assert updated["status_history"][-1]["status"] == "02"
    # 原始 dict 不能被動到，呼叫端才能安全地拿它跟 STORE 裡的版本比較
    assert order["order_status"] == "01"
    assert order["status_history"] == [{"status": "01", "at": "2026-08-01T00:00:00+08:00"}]


def test_apply_vendor_status_marks_completed_on_delivered():
    order = {"request_id": "REQ-1", "status": "PENDING", "order_status": "05", "vendor_data": {}}
    updated = delivery.apply_vendor_status(order, 5)
    assert updated["order_status"] == "70"
    assert updated["status"] == "COMPLETED"


def test_apply_vendor_status_rejects_unknown_code():
    order = {"request_id": "REQ-1", "status": "PENDING", "order_status": "01", "vendor_data": {}}
    assert delivery.apply_vendor_status(order, 99) is None
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `cd backend && python -m pytest tests/test_delivery_service.py -v`
Expected: `AttributeError: module 'delivery' has no attribute 'apply_vendor_status'`

- [ ] **Step 3: 實作**

在 `backend/app/config.py` 的 `_BUILTIN_VENDOR_ACCOUNTS` 新增（緊接在 Task 1 加的 `vendor22@demo.local` 後面）：

```python
    "vendor30@demo.local": {
        "vendor_id": 30,
        "name": "美食外送物流中心",
        "password": "vendor1234",
    },
```

在 `backend/app/services/delivery.py` 把 `update_delivery_status_from_vendor` 函式（第 221-256 行）拆成一個純函式加一個薄包裝：

```python
def apply_vendor_status(order: dict, vendor_status: int, delivery_info: dict | None = None) -> dict | None:
    """算出套用第三方狀態碼後的訂單，不寫入 STORE——由呼叫端決定要不要帶樂觀鎖版本寫入。

    vendor_status 不是已知代碼時回傳 None，呼叫端自行決定怎麼回應錯誤。
    """
    platform_status = VENDOR_STATUS_MAP.get(vendor_status)
    if not platform_status:
        return None

    updated = dict(order)
    updated["order_status"] = platform_status
    updated["vendor_data"] = dict(order.get("vendor_data") or {})
    updated["vendor_data"]["order_status"] = vendor_status

    if delivery_info:
        updated["vendor_data"]["delivery"] = delivery_info

    if platform_status == "70":
        updated["status"] = "COMPLETED"
    elif platform_status == "90":
        updated["status"] = "CANCELLED"
        updated["cancel_reason"] = "STORE_CANCEL"
    else:
        updated["status"] = "IN_PROGRESS"

    updated["status_history"] = list(order.get("status_history") or [])
    updated["status_history"].append({"status": platform_status, "at": now_iso()})
    return updated


def update_delivery_status_from_vendor(
    actor_id: str, request_id: str, vendor_status: int, delivery_info: dict | None = None
) -> dict:
    """第三方外送系統 webhook 回呼用：沒有廠商登入身分，直接信任呼叫來源、無條件寫入。"""
    order = STORE.get_request(actor_id, request_id)
    if not order:
        return _error("REQUEST_NOT_FOUND", "找不到對應的外送訂單。")

    updated = apply_vendor_status(order, vendor_status, delivery_info)
    if updated is None:
        return _error("INVALID_VENDOR_STATUS", f"未知的第三方狀態碼: {vendor_status}")

    STORE.save_request(actor_id, updated)
    return {
        "success": True,
        "request_id": request_id,
        "order_status": updated["order_status"],
        "order_status_label": ORDER_STATUS_LABEL.get(updated["order_status"], ""),
    }
```

- [ ] **Step 4: 跑測試確認通過**

Run: `cd backend && python -m pytest tests/test_delivery_service.py tests/test_delivery_api.py -v`
Expected: 全部通過（`test_delivery_api.py` 的既有 webhook／simulate 測試行為不變，因為 `update_delivery_status_from_vendor` 對外行為沒變）

- [ ] **Step 5: Commit**

```bash
git add backend/app/config.py backend/app/services/delivery.py backend/tests/test_delivery_service.py
git commit -m "refactor: extract pure apply_vendor_status from delivery status update, add vendor30 account"
```

---

## Task 6：外送廠商後台端點

**Files:**
- Create: `backend/app/api/vendor_delivery.py`
- Modify: `backend/app/main.py`
- Modify: `backend/tests/test_delivery_api.py`
- Modify: `backend/app/services/store.py`
- Create: `backend/tests/test_vendor_delivery_orders.py`

**Interfaces:**
- Consumes: `delivery.apply_vendor_status`（Task 5）、`get_current_vendor`、`STORE.list_vendor_requests`／`get_vendor_request`／`save_request_if_version`
- Produces: `GET /api/vendor/delivery-orders`、`GET /api/vendor/delivery-orders/{id}`、`POST /api/vendor/delivery-orders/{id}/{action}`（`action` ∈ accept／prepare／pickup／dispatch／deliver／reject）

- [ ] **Step 1: 寫失敗測試**

先修正 `backend/tests/test_delivery_api.py`：把 `test_simulate_delivery_status_advances_order_status_and_driver_info` 與 `test_simulate_delivery_status_returns_404_for_missing_order`（第 44-76 行）整段換成：

```python
def test_customer_can_no_longer_advance_delivery_status_directly():
    """使用者端的模擬端點已經移除，狀態推進只能透過廠商後台。"""
    client = TestClient(app)
    headers = _auth_headers(client)
    created = _create_order(client, headers)

    response = client.post(
        f"/api/delivery/orders/{created['request_id']}/simulate",
        json={"vendor_status": 1},
        headers=headers,
    )
    assert response.status_code == 404
```

新增 `backend/tests/test_vendor_delivery_orders.py`：

```python
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.api import vendor_delivery
from backend.app.services import delivery, store as store_module


@pytest.fixture(autouse=True)
def isolated_store(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        test_store = store_module.MemoryStore(storage_path=Path(tmp) / "store.json")
        monkeypatch.setattr(store_module, "STORE", test_store)
        monkeypatch.setattr(delivery, "STORE", test_store)
        # vendor_delivery.py 直接引用 STORE（不是全部透過 delivery.py 的 service 函式），
        # 這個名字也要單獨換掉，否則廠商端點還是打到沒被隔離的預設 STORE。
        monkeypatch.setattr(vendor_delivery, "STORE", test_store)
        yield test_store


def _resident_headers(client: TestClient) -> dict:
    accounts = client.get("/api/auth/demo-accounts").json()["accounts"]
    return {"Authorization": f"Bearer {accounts[0]['token']}"}


def _vendor_headers(client: TestClient) -> dict:
    login = client.post(
        "/api/vendor/login", json={"email": "vendor30@demo.local", "password": "vendor1234"}
    ).json()
    return {"Authorization": f"Bearer {login['token']}"}


def _create_order(client: TestClient, headers: dict) -> dict:
    return client.post(
        "/api/delivery/submit",
        json={
            "address": {
                "lat": 25.033, "lng": 121.565,
                "city": "台北市", "area": "大安區", "street": "忠孝東路四段100號",
                "remark": "", "contact_name": "王小明", "phone": "0912345678",
            },
            "goods": [{"id": "item-001", "title": "招牌雞腿便當", "price": 110, "quantity": 1}],
            "store_id": "store-001",
            "store_name": "好味道便當",
            "store_address": "台北市大安區忠孝東路四段100號",
        },
        headers=headers,
    ).json()


def test_new_delivery_order_is_visible_in_pending_scope():
    client = TestClient(app)
    headers = _resident_headers(client)
    created = _create_order(client, headers)
    vendor_headers = _vendor_headers(client)

    res = client.get("/api/vendor/delivery-orders?scope=pending", headers=vendor_headers)
    assert res.status_code == 200
    assert created["request_id"] in [i["request_id"] for i in res.json()["items"]]


def test_vendor_advances_delivery_order_through_full_lifecycle():
    client = TestClient(app)
    headers = _resident_headers(client)
    created = _create_order(client, headers)
    vendor_headers = _vendor_headers(client)

    detail = client.get(
        f"/api/vendor/delivery-orders/{created['request_id']}", headers=vendor_headers
    ).json()
    assert detail["available_actions"] == ["accept", "reject"]
    version = detail["version"]

    for action in ("accept", "prepare", "pickup", "dispatch", "deliver"):
        res = client.post(
            f"/api/vendor/delivery-orders/{created['request_id']}/{action}",
            json={"version": version},
            headers=vendor_headers,
        )
        assert res.status_code == 200, res.text
        version = res.json()["version"]

    final = client.get(
        f"/api/vendor/delivery-orders/{created['request_id']}", headers=vendor_headers
    ).json()
    assert final["status_label"] == "已送達"
    assert final["available_actions"] == []

    order = client.get(f"/api/delivery/orders/{created['request_id']}", headers=headers).json()
    assert order["status"] == "COMPLETED"
    assert order["order_status"] == "70"


def test_reject_is_blocked_after_pickup():
    client = TestClient(app)
    headers = _resident_headers(client)
    created = _create_order(client, headers)
    vendor_headers = _vendor_headers(client)

    version = client.get(
        f"/api/vendor/delivery-orders/{created['request_id']}", headers=vendor_headers
    ).json()["version"]
    for action in ("accept", "prepare", "pickup"):
        res = client.post(
            f"/api/vendor/delivery-orders/{created['request_id']}/{action}",
            json={"version": version},
            headers=vendor_headers,
        )
        assert res.status_code == 200, res.text
        version = res.json()["version"]

    reject = client.post(
        f"/api/vendor/delivery-orders/{created['request_id']}/reject",
        json={"version": version},
        headers=vendor_headers,
    )
    assert reject.status_code == 409
    assert reject.json()["detail"]["error"]["code"] == "REQUEST_STATUS_CONFLICT"


def test_customer_token_is_rejected_by_delivery_vendor_api():
    client = TestClient(app)
    res = client.get("/api/vendor/delivery-orders", headers=_resident_headers(client))
    assert res.status_code == 403
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `cd backend && python -m pytest tests/test_vendor_delivery_orders.py tests/test_delivery_api.py -v`
Expected: `test_vendor_delivery_orders.py` 全部 404（路由不存在）；`test_customer_can_no_longer_advance_delivery_status_directly` 因為端點還沒刪除而失敗（回 200 不是 404）

- [ ] **Step 3: 實作**

在 `backend/app/services/store.py` 的 `_save_vendor_index`（第 127-158 行）裡的字典新增一個欄位，讓外送訂單的細粒度狀態代碼也被鏡射進索引（否則廠商後台清單查不到 `order_status`）。在 `"status": request.get("status", ""),` 這行後面加一行：

```python
                    "status": request.get("status", ""),
                    "order_status": request.get("order_status"),
```

在 `backend/app/api/delivery.py` 刪掉 `simulate_delivery_status` 端點（第 71-87 行）。

新增 `backend/app/api/vendor_delivery.py`：

```python
"""廠商後台：美食外送訂單清單與狀態推進（vendor_id 30，唯一的外送物流廠商帳號）。

跟通用案件（vendor.py）共用同一套廠商驗證與 VENDOR# 索引查詢機制，但外送訂單的
狀態欄位形狀不一樣——粗粒度 status（PENDING／IN_PROGRESS／COMPLETED／CANCELLED）
決定廠商後台分頁，細粒度 order_status（01～90 兩位數代碼）決定廠商當下能按哪個
動作，兩者不是同一回事，所以另外開一份轉換規則，不硬塞進 vendor.py 的
VENDOR_TRANSITIONS。
"""
from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import BaseModel, Field

from ..auth.cognito import CurrentUser, get_current_vendor
from ..services import delivery
from ..services.delivery import ORDER_STATUS_LABEL
from ..services.store import STORE, version_of

router = APIRouter(prefix="/api/vendor/delivery-orders")

_PENDING_STATUSES = ("PENDING",)
_ORDER_STATUSES = ("IN_PROGRESS", "COMPLETED")
_CLOSED_STATUSES = ("CANCELLED",)
_VISIBLE_STATUSES = frozenset(_PENDING_STATUSES + _ORDER_STATUSES + _CLOSED_STATUSES)

_SCOPES = {
    "pending": frozenset(_PENDING_STATUSES),
    "orders": frozenset(_ORDER_STATUSES),
    "all": _VISIBLE_STATUSES,
}

# 動作 → (要求的來源 order_status 代碼, 要送給 apply_vendor_status 的 vendor_status 數字)。
_PROGRESS_ACTIONS: dict[str, tuple[str, int]] = {
    "accept": ("01", 1),
    "prepare": ("02", 2),
    "pickup": ("03", 3),
    "dispatch": ("04", 4),
    "deliver": ("05", 5),
}
_ACTION_LABELS = {
    "accept": "商家已接單",
    "prepare": "開始備餐",
    "pickup": "外送員已取餐",
    "dispatch": "開始配送",
    "deliver": "已送達",
    "reject": "無法接單",
}
# reject 只能在正式出餐前喊停；已經被外送員取走就不能再拒。
_REJECTABLE_ORDER_STATUSES = frozenset({"01", "02", "03"})
_REJECT_VENDOR_STATUS = 9


def _fail(status: int, code: str, message: str, extra: dict | None = None) -> HTTPException:
    return HTTPException(
        status_code=status,
        detail={"success": False, "error": {"code": code, "message": message} | (extra or {})},
    )


def _available_actions(order_status: str) -> list[str]:
    actions = [name for name, (source, _) in _PROGRESS_ACTIONS.items() if source == order_status]
    if order_status in _REJECTABLE_ORDER_STATUSES:
        actions.append("reject")
    return actions


def _to_list_item(item: dict) -> dict:
    order_status = item.get("order_status") or ""
    form_data = item.get("form_data") or {}
    address = form_data.get("address") or {}
    return {
        "request_id": item["request_id"],
        "service_id": "food_delivery",
        "service_name": item.get("service_name", "美食外送"),
        "status": item.get("status", ""),
        "status_label": ORDER_STATUS_LABEL.get(order_status, item.get("status", "")),
        "customer_name": address.get("contact_name", ""),
        "summary": form_data.get("store_name", ""),
        "version": version_of(item),
        "available_actions": _available_actions(order_status),
        "created_at": item.get("created_at", ""),
        "updated_at": item.get("updated_at", ""),
    }


def _load_order_or_404(vendor_id: int, request_id: str) -> tuple[str, dict]:
    index = STORE.get_vendor_request(vendor_id, request_id)
    owner_id = str((index or {}).get("owner_id") or "")
    order = STORE.get_request(owner_id, request_id) if owner_id else None
    if not order or order.get("service_id") != "food_delivery" or order.get("status") not in _VISIBLE_STATUSES:
        raise _fail(404, "REQUEST_NOT_FOUND", "找不到對應的外送訂單。")
    return owner_id, order


def _to_fields(order: dict) -> list[dict]:
    form_data = order.get("form_data") or {}
    address = form_data.get("address") or {}
    goods = form_data.get("goods") or []
    goods_summary = "、".join(f"{g.get('title', '')} x{g.get('quantity', 1)}" for g in goods)
    rows = [
        {"id": "store_name", "label": "店家", "value": form_data.get("store_name", "")},
        {"id": "goods", "label": "餐點", "value": goods_summary},
        {"id": "contact_name", "label": "收件人", "value": address.get("contact_name", "")},
        {"id": "phone", "label": "聯絡電話", "value": address.get("phone", "") or ""},
        {
            "id": "address",
            "label": "外送地址",
            "value": f"{address.get('city', '')}{address.get('area', '')}{address.get('street', '')}",
        },
    ]
    if form_data.get("note"):
        rows.append({"id": "note", "label": "備註", "value": form_data["note"]})
    return [row for row in rows if row["value"]]


def _detail_payload(order: dict) -> dict:
    order_status = order.get("order_status") or ""
    return {
        "request_id": order["request_id"],
        "service_id": "food_delivery",
        "service_name": order.get("service_name", "美食外送"),
        "status": order.get("status", ""),
        "status_label": ORDER_STATUS_LABEL.get(order_status, order.get("status", "")),
        "customer_name": ((order.get("form_data") or {}).get("address") or {}).get("contact_name", ""),
        "version": version_of(order),
        "available_actions": _available_actions(order_status),
        "fields": _to_fields(order),
        "created_at": order.get("created_at", ""),
        "updated_at": order.get("updated_at", ""),
    }


class VendorDeliveryActionIn(BaseModel):
    version: int = Field(..., ge=0)


@router.get("")
def list_vendor_delivery_orders(scope: str = "all", vendor: CurrentUser = Depends(get_current_vendor)):
    if scope not in _SCOPES:
        raise _fail(422, "INVALID_SCOPE", "scope 參數不合法。")
    stored = STORE.list_vendor_requests(vendor.vendor_id)
    items = [_to_list_item(i) for i in stored if i.get("status") in _SCOPES[scope]]
    counts = {name: sum(1 for i in stored if i.get("status") in statuses) for name, statuses in _SCOPES.items()}
    return {"items": items, "counts": counts}


@router.get("/{request_id}")
def get_vendor_delivery_order(request_id: str, vendor: CurrentUser = Depends(get_current_vendor)):
    _, order = _load_order_or_404(vendor.vendor_id, request_id)
    return _detail_payload(order)


@router.post("/{request_id}/{action}")
def act_on_vendor_delivery_order(
    body: VendorDeliveryActionIn,
    request_id: str,
    action: str = Path(pattern="^(accept|prepare|pickup|dispatch|deliver|reject)$"),
    vendor: CurrentUser = Depends(get_current_vendor),
):
    owner_id, order = _load_order_or_404(vendor.vendor_id, request_id)
    current_order_status = order.get("order_status") or ""

    if action == "reject":
        eligible = current_order_status in _REJECTABLE_ORDER_STATUSES
        vendor_status = _REJECT_VENDOR_STATUS
    else:
        source, vendor_status = _PROGRESS_ACTIONS[action]
        eligible = current_order_status == source

    if not eligible:
        raise _fail(
            409,
            "REQUEST_STATUS_CONFLICT",
            f"訂單目前是「{ORDER_STATUS_LABEL.get(current_order_status, current_order_status)}」，無法{_ACTION_LABELS[action]}。",
            _detail_payload(order),
        )

    updated = delivery.apply_vendor_status(order, vendor_status)
    if updated is None:
        raise _fail(400, "INVALID_ACTION", "不支援的動作。")

    if not STORE.save_request_if_version(owner_id, updated, body.version):
        _, current = _load_order_or_404(vendor.vendor_id, request_id)
        raise _fail(
            409,
            "REQUEST_VERSION_CONFLICT",
            "訂單已被更新，請重新整理後再操作。",
            _detail_payload(current),
        )
    return {"success": True, **_detail_payload(updated)}
```

在 `backend/app/main.py` 把第 6 行：
```python
from .api import auth, chat, delivery, health, onboarding, requests, reservations, services, sessions, shop, vendor
```
改成：
```python
from .api import (
    auth,
    chat,
    delivery,
    health,
    onboarding,
    requests,
    reservations,
    services,
    sessions,
    shop,
    vendor,
    vendor_delivery,
)
```
並在第 31 行 `app.include_router(vendor.router)` 後面加一行：
```python
app.include_router(vendor_delivery.router)
```

- [ ] **Step 4: 跑測試確認通過**

Run: `cd backend && python -m pytest tests/test_vendor_delivery_orders.py tests/test_delivery_api.py tests/test_vendor_portal.py -v`
Expected: 全部通過

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/vendor_delivery.py backend/app/api/delivery.py backend/app/main.py backend/app/services/store.py backend/tests/test_vendor_delivery_orders.py backend/tests/test_delivery_api.py
git commit -m "feat: add vendor-authenticated delivery order lifecycle endpoints"
```

---

## Task 7：前端外送廠商 API 與拿掉使用者端模擬按鈕

**Files:**
- Create: `frontend/src/api/vendorDelivery.ts`
- Modify: `frontend/src/api/delivery.ts`
- Modify: `frontend/src/pages/DeliveryFlowPage.tsx`
- Modify: `frontend/src/pages/DeliveryFlowPage.test.tsx`

**Interfaces:**
- Produces: `listVendorDeliveryOrders`／`getVendorDeliveryOrder`／`actOnVendorDeliveryOrder`，函式簽章跟 `frontend/src/api/vendor.ts` 的 `listVendorRequests`／`getVendorRequest`／`actOnVendorRequest` 對齊（供 Task 11 用同一個介面切換）

- [ ] **Step 1: 新增廠商 API 模組**

新增 `frontend/src/api/vendorDelivery.ts`：

```typescript
import type {
  VendorAction,
  VendorActionResult,
  VendorRequestDetail,
  VendorRequestList,
  VendorScope,
} from "../types/vendor";
import { vendorApi } from "./client";

export function listVendorDeliveryOrders(scope: VendorScope) {
  return vendorApi<VendorRequestList>(`/api/vendor/delivery-orders?scope=${scope}`);
}

export function getVendorDeliveryOrder(requestId: string) {
  return vendorApi<VendorRequestDetail>(`/api/vendor/delivery-orders/${requestId}`);
}

export function actOnVendorDeliveryOrder(requestId: string, action: VendorAction, version: number) {
  return vendorApi<VendorActionResult>(`/api/vendor/delivery-orders/${requestId}/${action}`, {
    method: "POST",
    body: JSON.stringify({ version }),
  });
}
```

- [ ] **Step 2: 移除使用者端模擬 API 與按鈕**

在 `frontend/src/api/delivery.ts` 刪掉 `simulateDeliveryStatus`（第 37-49 行）。

在 `frontend/src/pages/DeliveryFlowPage.tsx`：把 import 那行拿掉 `simulateDeliveryStatus`：
```typescript
import {
  getDeliveryOrder,
  getDeliveryStore,
  listDeliveryStores,
  submitDeliveryOrder,
} from "../api/delivery";
```

刪掉渲染模擬按鈕的 IIFE 區塊（第 548-575 行，從 `{(() => {` 到對應的 `})()}`）。

在 `frontend/src/pages/DeliveryFlowPage.test.tsx` 的 `beforeEach` 裡刪掉這一段（第 78-82 行）：
```typescript
  vi.mocked(deliveryApi.simulateDeliveryStatus).mockResolvedValue({
    success: true,
    order_status: "02",
    order_status_label: "已接單",
  });
```

- [ ] **Step 3: 跑測試與建置**

Run: `cd frontend && npx vitest run src/pages/DeliveryFlowPage.test.tsx && npm run build`
Expected: 測試通過；建置成功，沒有未定義的 `simulateDeliveryStatus` 參照

- [ ] **Step 4: Commit**

```bash
git add frontend/src/api/vendorDelivery.ts frontend/src/api/delivery.ts frontend/src/pages/DeliveryFlowPage.tsx frontend/src/pages/DeliveryFlowPage.test.tsx
git commit -m "feat: add vendor delivery API client, remove customer-facing demo button"
```

---

## Task 8：商城廠商帳號與出貨狀態機

**Files:**
- Modify: `backend/app/config.py`
- Modify: `backend/app/services/catalog.py`
- Modify: `backend/app/services/shop.py`
- Test: `backend/tests/test_shop_service.py`

**Interfaces:**
- Produces: `shop.STATUS_LABELS: dict[str, str]`、`shop.SHOP_VENDOR_TRANSITIONS: dict[str, tuple[str, str]]`（action → (source, target)）、`shop.advance_shop_order_for_vendor(actor_id, request_id, action, expected_version) -> dict`、`shop.cancel_shop_order(actor_id, request_id, reason="USER_CANCEL", expected_version=None) -> dict`（新增可選的 `expected_version` 參數，向後相容既有呼叫端）

- [ ] **Step 1: 寫失敗測試**

在 `backend/tests/test_shop_service.py` 把 `test_advance_shop_order_status_progresses_through_fixed_sequence`（第 191-202 行）整段換成：

```python
def test_advance_shop_order_for_vendor_progresses_through_named_actions():
    created = shop.create_shop_order("user-a", physical_cart_payload())
    assert created["status"] == "SUBMITTED"
    version = 1  # create_shop_order 之後的第一版

    r1 = shop.advance_shop_order_for_vendor("user-a", created["request_id"], "confirm", version)
    assert r1 == {"success": True, "status": "CONFIRMED"}

    order = shop.get_shop_order("user-a", created["request_id"])
    r2 = shop.advance_shop_order_for_vendor("user-a", created["request_id"], "ship", order["version"])
    assert r2["status"] == "IN_PROGRESS"

    order = shop.get_shop_order("user-a", created["request_id"])
    r3 = shop.advance_shop_order_for_vendor("user-a", created["request_id"], "deliver", order["version"])
    assert r3["status"] == "COMPLETED"


def test_advance_shop_order_for_vendor_rejects_wrong_source_status():
    created = shop.create_shop_order("user-a", physical_cart_payload())
    result = shop.advance_shop_order_for_vendor("user-a", created["request_id"], "ship", 1)
    assert result["success"] is False
    assert result["error"]["code"] == "STATUS_ADVANCE_NOT_ALLOWED"


def test_advance_shop_order_for_vendor_rejects_stale_version():
    created = shop.create_shop_order("user-a", physical_cart_payload())
    result = shop.advance_shop_order_for_vendor("user-a", created["request_id"], "confirm", 999)
    assert result["success"] is False
    assert result["error"]["code"] == "VERSION_CONFLICT"


def test_cancel_shop_order_with_version_conflict_does_not_restock(isolated_store):
    created = shop.create_shop_order("user-a", physical_cart_payload())
    result = shop.cancel_shop_order("user-a", created["request_id"], expected_version=999)
    assert result["success"] is False
    assert result["error"]["code"] == "VERSION_CONFLICT"
    # 版本衝突時不能已經退了庫存卻沒有真的取消。isolated_store fixture 給
    # sku_tshirt_white_s 起始庫存 5，physical_cart_payload() 預設買 2 件，
    # 建單後庫存應為 3，取消失敗不該讓它變回去。
    assert isolated_store.get_sku_stock("sku_tshirt_white_s") == 3
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `cd backend && python -m pytest tests/test_shop_service.py -v`
Expected: `AttributeError: module 'shop' has no attribute 'advance_shop_order_for_vendor'`；`cancel_shop_order() got an unexpected keyword argument 'expected_version'`

- [ ] **Step 3: 實作**

在 `backend/app/config.py` 的 `_BUILTIN_VENDOR_ACCOUNTS` 新增（緊接在 Task 5 加的 `vendor30@demo.local` 後面）：

```python
    "vendor40@demo.local": {
        "vendor_id": 40,
        "name": "商城出貨中心",
        "password": "vendor1234",
    },
```

在 `backend/app/services/catalog.py` 把 `shop_purchase` 服務定義（第 340-358 行）裡的：
```python
        "service_vendor_id": None,
```
改成：
```python
        "service_vendor_id": 40,
```

在 `backend/app/services/shop.py`：

把 `STATUS_PROGRESSION`（第 17 行）換成：
```python
STATUS_LABELS = {
    "SUBMITTED": "待確認",
    "CONFIRMED": "備貨中",
    "IN_PROGRESS": "已出貨",
    "COMPLETED": "已送達",
    "CANCELLED": "已取消",
}

# 廠商後台的動作 → (要求的來源狀態, 目標狀態)。
SHOP_VENDOR_TRANSITIONS: dict[str, tuple[str, str]] = {
    "confirm": ("SUBMITTED", "CONFIRMED"),
    "ship": ("CONFIRMED", "IN_PROGRESS"),
    "deliver": ("IN_PROGRESS", "COMPLETED"),
}
```

把 `cancel_shop_order`（第 180-198 行）整個換成：

```python
def cancel_shop_order(
    actor_id: str, request_id: str, reason: str = "USER_CANCEL", expected_version: int | None = None
) -> dict:
    order = STORE.get_request(actor_id, request_id)
    if not order:
        return _error("REQUEST_NOT_FOUND", "找不到這筆訂單")
    if order.get("status") not in CANCELLABLE_STATUSES:
        return _error("CANCEL_NOT_ALLOWED", "目前狀態無法取消訂單")

    updated = dict(order)
    updated["status"] = "CANCELLED"
    updated["cancel_reason"] = reason
    updated["status_history"] = list(order.get("status_history") or [])
    updated["status_history"].append({"status": "CANCELLED", "at": now_iso()})

    # 樂觀鎖先過，才做退點數／補庫存——避免版本衝突時已經退了，但案件其實沒取消成功。
    if expected_version is not None:
        if not STORE.save_request_if_version(actor_id, updated, expected_version):
            return _error("VERSION_CONFLICT", "訂單已被更新，請重新整理後再操作。")
    else:
        STORE.save_request(actor_id, updated)

    for line in order["form_data"]["cart"]:
        STORE.restock_sku(line["sku_id"], line["quantity"])

    points_discount = order.get("points_discount", 0)
    if points_discount:
        STORE.refund_user_points(actor_id, points_discount // POINTS_TO_NT_RATE)

    return {"success": True, "status": "CANCELLED"}
```

把 `advance_shop_order_status`（第 201-213 行）整個換成：

```python
def advance_shop_order_for_vendor(actor_id: str, request_id: str, action: str, expected_version: int) -> dict:
    order = STORE.get_request(actor_id, request_id)
    if not order:
        return _error("REQUEST_NOT_FOUND", "找不到這筆訂單")

    source, target = SHOP_VENDOR_TRANSITIONS[action]
    if order.get("status") != source:
        return _error(
            "STATUS_ADVANCE_NOT_ALLOWED", f"訂單目前是「{STATUS_LABELS.get(order.get('status'), order.get('status'))}」，無法{action}"
        )

    updated = dict(order)
    updated["status"] = target
    updated["status_history"] = list(order.get("status_history") or [])
    updated["status_history"].append({"status": target, "at": now_iso()})

    if not STORE.save_request_if_version(actor_id, updated, expected_version):
        return _error("VERSION_CONFLICT", "訂單已被更新，請重新整理後再操作。")

    return {"success": True, "status": target}
```

- [ ] **Step 4: 跑測試確認通過**

Run: `cd backend && python -m pytest tests/test_shop_service.py tests/test_shop_api.py -v`
Expected: 全部通過

- [ ] **Step 5: Commit**

```bash
git add backend/app/config.py backend/app/services/catalog.py backend/app/services/shop.py backend/tests/test_shop_service.py
git commit -m "feat: add versioned shop order vendor transitions and vendor40 account"
```

---

## Task 9：商城廠商後台端點

**Files:**
- Create: `backend/app/api/vendor_shop.py`
- Modify: `backend/app/api/shop.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_vendor_shop_orders.py`

**Interfaces:**
- Consumes: `shop.SHOP_VENDOR_TRANSITIONS`／`shop.advance_shop_order_for_vendor`／`shop.cancel_shop_order`／`shop.STATUS_LABELS`（Task 8）
- Produces: `GET /api/vendor/shop-orders`、`GET /api/vendor/shop-orders/{id}`、`POST /api/vendor/shop-orders/{id}/{action}`（`action` ∈ confirm／ship／deliver／reject）

- [ ] **Step 1: 寫失敗測試**

新增 `backend/tests/test_vendor_shop_orders.py`：

```python
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.api import vendor_shop
from backend.app.services import shop, store as store_module


@pytest.fixture(autouse=True)
def isolated_store(monkeypatch):
    test_store = store_module.MemoryStore()
    monkeypatch.setattr(store_module, "STORE", test_store)
    monkeypatch.setattr(shop, "STORE", test_store)
    # vendor_shop.py 直接引用 STORE 查索引與寫樂觀鎖，這個名字也要單獨換掉。
    monkeypatch.setattr(vendor_shop, "STORE", test_store)
    test_store.put_item(
        {
            "PK": "SHOP_SKU#sku_tshirt_white_s", "SK": "STOCK",
            "entity_type": "SHOP_SKU_STOCK", "quantity": 5, "updated_at": "",
        }
    )
    yield test_store


def _resident_headers(client: TestClient) -> dict:
    accounts = client.get("/api/auth/demo-accounts").json()["accounts"]
    return {"Authorization": f"Bearer {accounts[0]['token']}"}


def _vendor_headers(client: TestClient) -> dict:
    login = client.post(
        "/api/vendor/login", json={"email": "vendor40@demo.local", "password": "vendor1234"}
    ).json()
    return {"Authorization": f"Bearer {login['token']}"}


def _create_physical_order(client: TestClient, headers: dict) -> dict:
    return client.post(
        "/api/shop/submit",
        json={
            "cart": [{"sku_id": "sku_tshirt_white_s", "quantity": 1}],
            "contact_name": "王小明",
            "phone": "0912345678",
            "address": {"city": "台北市", "street": "忠孝東路四段100號", "contact_name": "王小明"},
            "used_points": 0,
        },
        headers=headers,
    ).json()


def test_new_physical_order_is_visible_to_shop_vendor():
    client = TestClient(app)
    headers = _resident_headers(client)
    created = _create_physical_order(client, headers)

    res = client.get("/api/vendor/shop-orders?scope=pending", headers=_vendor_headers(client))
    assert res.status_code == 200
    assert created["request_id"] in [i["request_id"] for i in res.json()["items"]]


def test_vendor_advances_shop_order_through_full_lifecycle():
    client = TestClient(app)
    headers = _resident_headers(client)
    created = _create_physical_order(client, headers)
    vendor_headers = _vendor_headers(client)

    detail = client.get(
        f"/api/vendor/shop-orders/{created['request_id']}", headers=vendor_headers
    ).json()
    assert detail["available_actions"] == ["confirm", "reject"]
    version = detail["version"]

    for action in ("confirm", "ship", "deliver"):
        res = client.post(
            f"/api/vendor/shop-orders/{created['request_id']}/{action}",
            json={"version": version},
            headers=vendor_headers,
        )
        assert res.status_code == 200, res.text
        version = res.json()["version"]

    final = client.get(f"/api/shop/orders/{created['request_id']}", headers=headers).json()
    assert final["status"] == "COMPLETED"


def test_vendor_reject_restocks_and_refunds():
    client = TestClient(app)
    headers = _resident_headers(client)
    created = _create_physical_order(client, headers)
    vendor_headers = _vendor_headers(client)
    version = client.get(
        f"/api/vendor/shop-orders/{created['request_id']}", headers=vendor_headers
    ).json()["version"]

    reject = client.post(
        f"/api/vendor/shop-orders/{created['request_id']}/reject",
        json={"version": version},
        headers=vendor_headers,
    )
    assert reject.status_code == 200, reject.text
    assert reject.json()["status"] == "CANCELLED"

    order = client.get(f"/api/shop/orders/{created['request_id']}", headers=headers).json()
    assert order["status"] == "CANCELLED"


def test_shop_vendor_cannot_ship_before_confirm():
    client = TestClient(app)
    headers = _resident_headers(client)
    created = _create_physical_order(client, headers)
    vendor_headers = _vendor_headers(client)
    version = client.get(
        f"/api/vendor/shop-orders/{created['request_id']}", headers=vendor_headers
    ).json()["version"]

    res = client.post(
        f"/api/vendor/shop-orders/{created['request_id']}/ship",
        json={"version": version},
        headers=vendor_headers,
    )
    assert res.status_code == 409
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `cd backend && python -m pytest tests/test_vendor_shop_orders.py -v`
Expected: 全部 404（路由不存在）

- [ ] **Step 3: 實作**

在 `backend/app/api/shop.py` 刪掉 `simulate_shop_order_progress` 端點（第 71-78 行）。

新增 `backend/app/api/vendor_shop.py`：

```python
"""廠商後台：商城實體商品訂單清單與出貨推進（vendor_id 40，商城出貨中心）。

商城橫跨多間合作店家，但沿用既有「一個服務線一個廠商帳號」的慣例（跟餐廳訂位、
美食外送一樣），由單一出貨中心帳號集中處理所有實體商品訂單的出貨，不依店家拆單。
"""
from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import BaseModel, Field

from ..auth.cognito import CurrentUser, get_current_vendor
from ..services import shop
from ..services.store import STORE, version_of

router = APIRouter(prefix="/api/vendor/shop-orders")

_PENDING_STATUSES = ("SUBMITTED",)
_ORDER_STATUSES = ("CONFIRMED", "IN_PROGRESS", "COMPLETED")
_CLOSED_STATUSES = ("CANCELLED",)
_VISIBLE_STATUSES = frozenset(_PENDING_STATUSES + _ORDER_STATUSES + _CLOSED_STATUSES)

_SCOPES = {
    "pending": frozenset(_PENDING_STATUSES),
    "orders": frozenset(_ORDER_STATUSES),
    "all": _VISIBLE_STATUSES,
}

_ACTION_LABELS = {"confirm": "確認訂單", "ship": "出貨", "deliver": "送達", "reject": "無法出貨"}


def _fail(status: int, code: str, message: str, extra: dict | None = None) -> HTTPException:
    return HTTPException(
        status_code=status,
        detail={"success": False, "error": {"code": code, "message": message} | (extra or {})},
    )


def _available_actions(status: str) -> list[str]:
    actions = [name for name, (source, _) in shop.SHOP_VENDOR_TRANSITIONS.items() if source == status]
    if status == "SUBMITTED":
        actions.append("reject")
    return actions


def _goods_summary(cart: list) -> str:
    return "、".join(f"{line['sku_id']} x{line['quantity']}" for line in cart)


def _to_list_item(item: dict) -> dict:
    form_data = item.get("form_data") or {}
    status = item.get("status", "")
    return {
        "request_id": item["request_id"],
        "service_id": "shop_purchase",
        "service_name": item.get("service_name", "商城購物"),
        "status": status,
        "status_label": shop.STATUS_LABELS.get(status, status),
        "customer_name": form_data.get("contact_name", ""),
        "summary": _goods_summary(form_data.get("cart") or []),
        "version": version_of(item),
        "available_actions": _available_actions(status),
        "created_at": item.get("created_at", ""),
        "updated_at": item.get("updated_at", ""),
    }


def _load_order_or_404(vendor_id: int, request_id: str) -> tuple[str, dict]:
    index = STORE.get_vendor_request(vendor_id, request_id)
    owner_id = str((index or {}).get("owner_id") or "")
    order = STORE.get_request(owner_id, request_id) if owner_id else None
    if not order or order.get("service_id") != "shop_purchase" or order.get("status") not in _VISIBLE_STATUSES:
        raise _fail(404, "REQUEST_NOT_FOUND", "找不到對應的訂單。")
    return owner_id, order


def _to_fields(order: dict) -> list[dict]:
    form_data = order.get("form_data") or {}
    address = form_data.get("address") or {}
    rows = [
        {"id": "cart", "label": "商品", "value": _goods_summary(form_data.get("cart") or [])},
        {"id": "contact_name", "label": "聯絡人", "value": form_data.get("contact_name", "")},
        {"id": "phone", "label": "聯絡電話", "value": form_data.get("phone", "")},
    ]
    if address:
        rows.append(
            {"id": "address", "label": "收件地址", "value": f"{address.get('city', '')}{address.get('street', '')}"}
        )
    return [row for row in rows if row["value"]]


def _detail_payload(order: dict) -> dict:
    status = order.get("status", "")
    return {
        "request_id": order["request_id"],
        "service_id": "shop_purchase",
        "service_name": order.get("service_name", "商城購物"),
        "status": status,
        "status_label": shop.STATUS_LABELS.get(status, status),
        "customer_name": (order.get("form_data") or {}).get("contact_name", ""),
        "version": version_of(order),
        "available_actions": _available_actions(status),
        "fields": _to_fields(order),
        "created_at": order.get("created_at", ""),
        "updated_at": order.get("updated_at", ""),
    }


class VendorShopActionIn(BaseModel):
    version: int = Field(..., ge=0)


@router.get("")
def list_vendor_shop_orders(scope: str = "all", vendor: CurrentUser = Depends(get_current_vendor)):
    if scope not in _SCOPES:
        raise _fail(422, "INVALID_SCOPE", "scope 參數不合法。")
    stored = STORE.list_vendor_requests(vendor.vendor_id)
    items = [_to_list_item(i) for i in stored if i.get("status") in _SCOPES[scope]]
    counts = {name: sum(1 for i in stored if i.get("status") in statuses) for name, statuses in _SCOPES.items()}
    return {"items": items, "counts": counts}


@router.get("/{request_id}")
def get_vendor_shop_order(request_id: str, vendor: CurrentUser = Depends(get_current_vendor)):
    _, order = _load_order_or_404(vendor.vendor_id, request_id)
    return _detail_payload(order)


@router.post("/{request_id}/{action}")
def act_on_vendor_shop_order(
    body: VendorShopActionIn,
    request_id: str,
    action: str = Path(pattern="^(confirm|ship|deliver|reject)$"),
    vendor: CurrentUser = Depends(get_current_vendor),
):
    owner_id, order = _load_order_or_404(vendor.vendor_id, request_id)
    status = order.get("status", "")

    if action == "reject":
        if status != "SUBMITTED":
            raise _fail(
                409,
                "REQUEST_STATUS_CONFLICT",
                f"訂單目前是「{shop.STATUS_LABELS.get(status, status)}」，無法{_ACTION_LABELS[action]}。",
                _detail_payload(order),
            )
        result = shop.cancel_shop_order(owner_id, request_id, reason="VENDOR_CANCEL", expected_version=body.version)
    else:
        source, _target = shop.SHOP_VENDOR_TRANSITIONS[action]
        if status != source:
            raise _fail(
                409,
                "REQUEST_STATUS_CONFLICT",
                f"訂單目前是「{shop.STATUS_LABELS.get(status, status)}」，無法{_ACTION_LABELS[action]}。",
                _detail_payload(order),
            )
        result = shop.advance_shop_order_for_vendor(owner_id, request_id, action, body.version)

    if not result.get("success"):
        code = result["error"]["code"]
        _, current = _load_order_or_404(vendor.vendor_id, request_id)
        raise _fail(409, code, result["error"]["message"], _detail_payload(current))

    _, updated = _load_order_or_404(vendor.vendor_id, request_id)
    return {"success": True, **_detail_payload(updated)}
```

在 `backend/app/main.py` 把 Task 6 剛改成的 import 區塊：
```python
from .api import (
    auth,
    chat,
    delivery,
    health,
    onboarding,
    requests,
    reservations,
    services,
    sessions,
    shop,
    vendor,
    vendor_delivery,
)
```
加上 `vendor_shop`（依字母序插入 `vendor_delivery` 後面）：
```python
from .api import (
    auth,
    chat,
    delivery,
    health,
    onboarding,
    requests,
    reservations,
    services,
    sessions,
    shop,
    vendor,
    vendor_delivery,
    vendor_shop,
)
```
並在 `app.include_router(vendor_delivery.router)` 後面加一行：
```python
app.include_router(vendor_shop.router)
```

- [ ] **Step 4: 跑測試確認通過**

Run: `cd backend && python -m pytest tests/test_vendor_shop_orders.py tests/test_shop_api.py tests/test_shop_service.py -v`
Expected: 全部通過

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/vendor_shop.py backend/app/api/shop.py backend/app/main.py backend/tests/test_vendor_shop_orders.py
git commit -m "feat: add vendor-authenticated shop order fulfillment endpoints"
```

---

## Task 10：前端商城廠商 API 與拿掉使用者端模擬按鈕

**Files:**
- Create: `frontend/src/api/vendorShop.ts`
- Modify: `frontend/src/api/shop.ts`
- Modify: `frontend/src/pages/ShopFlowPage.tsx`

**Interfaces:**
- Produces: `listVendorShopOrders`／`getVendorShopOrder`／`actOnVendorShopOrder`，簽章對齊 `frontend/src/api/vendor.ts`

- [ ] **Step 1: 新增廠商 API 模組**

新增 `frontend/src/api/vendorShop.ts`：

```typescript
import type {
  VendorAction,
  VendorActionResult,
  VendorRequestDetail,
  VendorRequestList,
  VendorScope,
} from "../types/vendor";
import { vendorApi } from "./client";

export function listVendorShopOrders(scope: VendorScope) {
  return vendorApi<VendorRequestList>(`/api/vendor/shop-orders?scope=${scope}`);
}

export function getVendorShopOrder(requestId: string) {
  return vendorApi<VendorRequestDetail>(`/api/vendor/shop-orders/${requestId}`);
}

export function actOnVendorShopOrder(requestId: string, action: VendorAction, version: number) {
  return vendorApi<VendorActionResult>(`/api/vendor/shop-orders/${requestId}/${action}`, {
    method: "POST",
    body: JSON.stringify({ version }),
  });
}
```

- [ ] **Step 2: 移除使用者端模擬 API 與按鈕**

在 `frontend/src/api/shop.ts` 刪掉 `simulateShopOrderProgress`（第 48-50 行）。

在 `frontend/src/pages/ShopFlowPage.tsx`：把 import 那行拿掉 `simulateShopOrderProgress`：
```typescript
import {
  cancelShopOrder,
  getShopOrder,
  getShopPoints,
  listShopCategories,
  listShopProducts,
  submitShopOrder,
} from "../api/shop";
```

刪掉 `handleSimulateAdvance` 函式（第 188-197 行）。

把渲染按鈕的區塊（第 557-574 行）從兩顆按鈕改成只剩「取消訂單」一顆：
```tsx
                {order.status !== "COMPLETED" && order.status !== "CANCELLED" && (
                  <div className="flex gap-3">
                    <button
                      type="button"
                      onClick={handleCancel}
                      className="min-h-[44px] flex-1 rounded-2xl border-2 border-brand px-6 py-4 text-base font-bold text-brand"
                    >
                      取消訂單
                    </button>
                  </div>
                )}
```

- [ ] **Step 3: 跑測試與建置**

Run: `cd frontend && npx vitest run src/pages/ShopFlowPage.test.tsx && npm run build`
Expected: 測試通過；建置成功

- [ ] **Step 4: Commit**

```bash
git add frontend/src/api/vendorShop.ts frontend/src/api/shop.ts frontend/src/pages/ShopFlowPage.tsx
git commit -m "feat: add vendor shop API client, remove customer-facing demo button"
```

---

## Task 11：廠商後台頁面依登入帳號切換三種案件來源

**Files:**
- Create: `frontend/src/api/vendorRouting.ts`
- Modify: `frontend/src/types/vendor.ts`
- Modify: `frontend/src/pages/VendorRequestsPage.tsx`
- Modify: `frontend/src/pages/VendorRequestDetailPage.tsx`

**Interfaces:**
- Consumes: `useVendorAuth().vendorId`、Task 4 的通用 API（`frontend/src/api/vendor.ts`）、Task 7 的外送 API、Task 10 的商城 API
- Produces: `vendorKindOf(vendorId: number | null): VendorKind`、`getVendorApiForKind(kind: VendorKind)`

- [ ] **Step 1: 新增 kind 判斷與路由表**

在 `frontend/src/types/vendor.ts` 檔案最後追加：

```typescript
export type VendorKind = "generic" | "delivery" | "shop";

const DELIVERY_VENDOR_ID = 30;
const SHOP_VENDOR_ID = 40;

/** 依登入的 vendor_id 判斷這個帳號屬於哪種案件——沿用 catalog.py 裡「一個服務線一個廠商帳號」的慣例。 */
export function vendorKindOf(vendorId: number | null): VendorKind {
  if (vendorId === DELIVERY_VENDOR_ID) return "delivery";
  if (vendorId === SHOP_VENDOR_ID) return "shop";
  return "generic";
}
```

新增 `frontend/src/api/vendorRouting.ts`：

```typescript
import { actOnVendorRequest, getVendorRequest, listVendorRequests } from "./vendor";
import { actOnVendorDeliveryOrder, getVendorDeliveryOrder, listVendorDeliveryOrders } from "./vendorDelivery";
import { actOnVendorShopOrder, getVendorShopOrder, listVendorShopOrders } from "./vendorShop";
import type { VendorKind } from "../types/vendor";

const API_BY_KIND = {
  generic: { list: listVendorRequests, get: getVendorRequest, act: actOnVendorRequest },
  delivery: { list: listVendorDeliveryOrders, get: getVendorDeliveryOrder, act: actOnVendorDeliveryOrder },
  shop: { list: listVendorShopOrders, get: getVendorShopOrder, act: actOnVendorShopOrder },
} as const;

export function getVendorApiForKind(kind: VendorKind) {
  return API_BY_KIND[kind];
}
```

- [ ] **Step 2: 接上兩個頁面**

在 `frontend/src/pages/VendorRequestsPage.tsx`：把：
```typescript
import { listVendorRequests } from "../api/vendor";
```
改成：
```typescript
import { getVendorApiForKind } from "../api/vendorRouting";
import { vendorKindOf } from "../types/vendor";
```

把 `const { name, logout } = useVendorAuth();` 改成：
```typescript
  const { name, vendorId, logout } = useVendorAuth();
  const vendorApiSet = getVendorApiForKind(vendorKindOf(vendorId));
```

把 `load` 函式裡的 `listVendorRequests(next)` 改成 `vendorApiSet.list(next)`，並在 `useCallback` 的依賴陣列加上 `vendorApiSet`：
```typescript
  const load = useCallback(
    (next: VendorScope) => {
      setLoading(true);
      setError("");
      vendorApiSet
        .list(next)
        .then((r) => {
          setItems(r.items);
          setCounts(r.counts);
        })
        .catch((e) => {
          if (e instanceof ApiError && e.code === "UNAUTHORIZED") {
            navigate("/vendor/login");
            return;
          }
          setError(e instanceof ApiError ? e.message : "載入失敗，請稍後再試");
        })
        .finally(() => setLoading(false));
    },
    [navigate, vendorApiSet],
  );
```

在 `frontend/src/pages/VendorRequestDetailPage.tsx`：把：
```typescript
import { actOnVendorRequest, getVendorRequest } from "../api/vendor";
```
改成：
```typescript
import { getVendorApiForKind } from "../api/vendorRouting";
import { vendorKindOf } from "../types/vendor";
import { useVendorAuth } from "../hooks/useVendorAuth";
```

在 component 內加：
```typescript
  const { vendorId } = useVendorAuth();
  const vendorApiSet = getVendorApiForKind(vendorKindOf(vendorId));
```

把 `getVendorRequest(requestId)` 改成 `vendorApiSet.get(requestId)`（在 `useEffect` 依賴陣列加上 `vendorApiSet`），把 `actOnVendorRequest(requestId, action, detail.version)` 改成 `vendorApiSet.act(requestId, action, detail.version)`。

- [ ] **Step 3: 跑既有視覺回歸測試與建置**

Run: `cd frontend && npx vitest run src/pages/VendorPages.visual.test.tsx && npm run build`
Expected: 全部通過。`VendorPages.visual.test.tsx` mock 的是 `../api/vendor` 模組本身，`vendorId` 沒設定時 `useVendorAuth().vendorId` 會是 `null`，`vendorKindOf(null)` 回傳 `"generic"`，路由到的仍是被 mock 的 `../api/vendor`，行為不變

- [ ] **Step 4: Commit**

```bash
git add frontend/src/api/vendorRouting.ts frontend/src/types/vendor.ts frontend/src/pages/VendorRequestsPage.tsx frontend/src/pages/VendorRequestDetailPage.tsx
git commit -m "feat: route vendor portal pages to the right order API by vendor kind"
```

---

## Task 12：回填腳本支援本地 MemoryStore

**Files:**
- Modify: `backend/scripts/backfill_vendor_index.py`

**Interfaces:**
- Consumes: `app.services.store.build_store()`、`BaseStore.scan_by_entity_type`／`put_item`（兩種後端都已實作）

- [ ] **Step 1: 手動驗證目前的缺口**

Run（在 `backend/` 目錄下，確認本地 `.local-store.json` 存在且 `USE_MOCK` 是預設值 true）：
```bash
cd backend && python scripts/backfill_vendor_index.py --dry-run
```
Expected: 印出「USE_MOCK=true：本地記憶體儲存不需要回填。」——這正是要修掉的缺口，本地商城舊訂單不會被回填

- [ ] **Step 2: 重寫腳本**

把整份 `backend/scripts/backfill_vendor_index.py` 換成：

```python
"""把既有案件回填成廠商後台的 VENDOR# 索引項目。

廠商清單靠 save_request 時鏡射的 VENDOR#{id} 項目查詢（見 services/store.py），
但這份索引是 Milestone 3 才加的，之前建立的案件不會有——除非它們剛好又被改過
狀態。廠商後台上線後、或 catalog.py 的 service_vendor_id 對應改變後，跑一次
這支腳本即可補齊。DynamoDB 與本地 MemoryStore（USE_MOCK=true）都支援。

可重複執行：每次都以案件本體覆寫索引，不會產生重複項目。

    python backend/scripts/backfill_vendor_index.py --dry-run
    python backend/scripts/backfill_vendor_index.py
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services import catalog, store as store_module


def vendor_id_of(request: dict) -> int | None:
    vendor_id = request.get("service_vendor_id")
    if vendor_id is not None:
        return int(vendor_id)
    return catalog.vendor_id_for_service(str(request.get("service_id", "")))


def index_item(request: dict, vendor_id: int) -> dict:
    # PK 是 USER#{actor_id}，索引要記回案件屬於哪位住戶。
    owner_id = str(request["PK"]).removeprefix("USER#")
    return {
        "PK": f"VENDOR#{vendor_id}",
        "SK": f"REQUEST#{request['request_id']}",
        "entity_type": "VENDOR_REQUEST_INDEX",
        "vendor_id": vendor_id,
        "owner_id": owner_id,
        "request_id": request["request_id"],
        "service_id": request.get("service_id", ""),
        "service_name": request.get("service_name", ""),
        "status": request.get("status", ""),
        "order_status": request.get("order_status"),
        # 廠商後台接單／拒單要帶回版本比對，索引跟著鏡射（舊案件沒有就是 0）。
        "version": int(request.get("version") or 0),
        "form_data": request.get("form_data", {}),
        "created_at": request.get("created_at", ""),
        "updated_at": request.get("updated_at", request.get("created_at", "")),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="只列出要寫入的項目")
    args = parser.parse_args()

    backend = store_module.build_store()
    requests = backend.scan_by_entity_type("SERVICE_REQUEST")
    existing = {
        (str(i.get("PK")), str(i.get("SK")))
        for i in backend.scan_by_entity_type("VENDOR_REQUEST_INDEX")
    }

    to_write, skipped = [], []
    for request in requests:
        vendor_id = vendor_id_of(request)
        if vendor_id is None:
            # 服務目錄查不到廠商（例如只存在於 MCP Gateway 的服務），沒有東西可歸屬。
            skipped.append(request)
            continue
        to_write.append(index_item(request, vendor_id))

    fresh = [i for i in to_write if (i["PK"], i["SK"]) not in existing]
    print(f"（backend={backend.backend_name}）案件 {len(requests)} 筆　可歸屬 {len(to_write)} 筆（其中新建 {len(fresh)} 筆）")
    if skipped:
        print(f"略過 {len(skipped)} 筆：服務目錄查不到 service_vendor_id")
        for request in skipped:
            print(f"  - {request.get('request_id')} {request.get('service_name')}")

    if args.dry_run:
        for item in fresh:
            print(f"  + {item['PK']} {item['SK']} {item['service_name']} {item['status']}")
        return 0

    for item in to_write:
        backend.put_item(item)
    print(f"已寫入 {len(to_write)} 筆索引項目。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 3: 驗證兩種後端都能跑**

Run: `cd backend && python scripts/backfill_vendor_index.py --dry-run`
Expected: 印出 `（backend=memory+file）案件 N 筆　可歸屬 M 筆`，不再印出「不需要回填」；若本地 `.local-store.json` 有 `shop_purchase` 的舊訂單，這次應該會被列進「可歸屬」（因為 Task 8 已經把 `shop_purchase` 的 `service_vendor_id` 設成 40）

Run: `cd backend && python -m pytest tests/ -k backfill -v` （若這支腳本原本沒有對應測試檔，這行預期沒有測試被收集，屬正常，純粹用上面 Step 3 的手動 dry-run 驗證即可）

- [ ] **Step 4: Commit**

```bash
git add backend/scripts/backfill_vendor_index.py
git commit -m "fix: support MemoryStore backend in vendor index backfill script"
```

---

## Task 13：更新 Demo 劇本

**Files:**
- Modify: `docs/demo-script.md`

**Interfaces:**
- 無（純文件修正）

- [ ] **Step 1: 移除已失效的步驟**

把 `docs/demo-script.md` 的「Demo 2：案件追蹤」（第 14-17 行）：
```markdown
## Demo 2：案件追蹤
1. 點擊剛建立的案件卡片
2. 展示：狀態徽章、表單資料、完整對話紀錄
3. 點「（Demo）模擬廠商確認」→ 狀態即時更新為「已確認」
```
改成：
```markdown
## Demo 2：案件追蹤
1. 點擊剛建立的案件卡片
2. 展示：狀態徽章、表單資料、完整對話紀錄
```

（不用動 Demo 5，Demo 5 第 3 步預期案件還在「待確認諮詢單」分頁，拿掉 Demo 2 的模擬步驟後這個預期本來就會成立，兩者現在前後一致）

- [ ] **Step 2: 確認沒有其他地方引用同一顆按鈕**

Run: `cd "$(git rev-parse --show-toplevel)" && grep -rn "模擬廠商確認" docs/ 2>/dev/null; echo done`
Expected: 只有剛剛修掉的那一處（若指令找不到 `grep` 就手動打開 `docs/demo-script.md` 確認全文搜尋不到「模擬廠商確認」）

- [ ] **Step 3: Commit**

```bash
git add docs/demo-script.md
git commit -m "docs: update demo script for vendor-driven confirmation flow"
```
