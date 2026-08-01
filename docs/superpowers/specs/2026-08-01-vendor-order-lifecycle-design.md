# 廠商後台完整案件生命週期設計

**日期**：2026-08-01
**狀態**：待審核

## 背景與問題

目前系統裡有三組案件會經過「送出 → 廠商確認 → 履約 → 完成」的生命週期：通用服務案件（清潔／水電／包裹寄送／餐廳訂位）、美食外送、商城實體商品訂單。三組都各自留了一個「使用者自己按按鈕模擬廠商動作」的 Demo 端點：

- `/api/requests/{id}/simulate/{status}`（[requests.py:107](../../../backend/app/api/requests.py#L107)），前端按鈕明講「Demo：模擬廠商已確認」（[RequestDetailPage.tsx:82-92](../../../frontend/src/pages/RequestDetailPage.tsx#L82-L92)）
- `/api/delivery/orders/{id}/simulate`（[delivery.py:71](../../../backend/app/api/delivery.py#L71)）
- `/api/shop/orders/{id}/simulate`（[shop.py:71](../../../backend/app/api/shop.py#L71)）

這三個端點都是用**使用者自己的 token**（`get_current_user`）呼叫，代表使用者可以繞過廠商同意，自己把案件狀態改成「已確認」「已完成」等。其中通用服務案件更嚴重：廠商後台（[vendor.py](../../../backend/app/api/vendor.py)）本來就有正規的「接單」流程（狀態機＋樂觀鎖），使用者端的模擬按鈕等於是一條繞過它的平行捷徑。

同時，通用服務案件的廠商狀態機（[statuses.py](../../../backend/app/services/statuses.py)）只定義到「接單／拒單」，CONFIRMED 之後的 IN_PROGRESS／COMPLETED／VERIFIED 完全沒有廠商端 API 可以推進——所以才會冒出使用者端的模擬按鈕當替代品。

## 目標

把這三組案件的「狀態推進」動作，從使用者端移到對應的廠商後台，由廠商登入後、經狀態機檢查與樂觀鎖，才能推進。移除的使用者端 Demo 端點與按鈕全部刪除，不保留。

## 非目標（本次不做）

- `/api/webhooks/delivery-callback` 沒有簽章／密鑰驗證的問題——維持現狀，另案處理
- 把「外送員（騎手）」從「店家」拆成獨立身分——本次仍是店家帳號一路推進到「已送達」
- 商城訂單依店家拆單各自出貨——本次仍是單一「商城出貨中心」帳號集中處理所有實體商品訂單

## 架構總覽

三種案件共用同一套底層機制，這套機制已經存在、不需要新建：

- 廠商身分驗證：`get_current_vendor`（[cognito.py:42](../../../backend/app/auth/cognito.py#L42)）
- 廠商可見清單：`STORE.list_vendor_requests(vendor_id)` 查 `VENDOR#{id}` 鏡射索引（[store.py:160](../../../backend/app/services/store.py#L160)）
- 樂觀鎖：`STORE.save_request_if_version`（[store.py:111](../../../backend/app/services/store.py#L111)），案件版本號在寫入時自動遞增

三種案件的「狀態欄位形狀」本來就不一樣（通用案件是單一 `status` 列舉；外送是 `status` 粗粒度 + `order_status` 兩位數代碼；商城是單一 `status` 但有點數／庫存的補償邏輯），所以**不做成單一的多型分派層**，而是各自維護一份小而專一的轉換規則，共用底下的驗證與儲存機制。

## 各服務改動細節

### 1. 通用服務案件（清潔／水電／包裹寄送／餐廳訂位）

在既有 `VENDOR_TRANSITIONS`（[statuses.py:37](../../../backend/app/services/statuses.py#L37)）新增：

| 動作 | 來源狀態 | 目標狀態 | 標籤 | 適用服務 |
|---|---|---|---|---|
| `start` | CONFIRMED | IN_PROGRESS | 開始服務 | 全部 |
| `complete` | IN_PROGRESS | COMPLETED | 完成服務 | 全部 |
| `verify` | COMPLETED | VERIFIED | 核銷 | 僅 `restaurant_reservation` |

`verify` 是唯一限定服務類型的轉換，因為只有餐廳訂位有「核銷」概念（其餘服務完工即結案，不會再變成 VERIFIED）。`VendorTransition` 需要新增一個可選欄位（例如 `applicable_services: frozenset[str] | None`，`None` 代表不限），`vendor.py` 的 `_available_actions` 要多帶入 `service_id` 才能判斷 `verify` 是否該出現。

移除：
- `backend/app/api/requests.py` 的 `simulate_status` 端點與路由
- `frontend/src/api/requests.ts` 的 `simulateStatus`
- `frontend/src/pages/RequestDetailPage.tsx` 裡 `nextDemo` / `demo` 那段模擬按鈕邏輯

### 2. 美食外送（`food_delivery`）

catalog 裡本來就有 `service_vendor_id: 30`（[catalog.py:430](../../../backend/app/services/catalog.py#L430)），只是沒有對應的登入帳號。新增內建示範帳號 `vendor30@demo.local`／「美食外送物流中心」（沿用 [config.py:29-45](../../../backend/app/config.py#L29-L45) 的 `_BUILTIN_VENDOR_ACCOUNTS` 格式，密碼比照現有帳號用 `vendor1234`）。

新增廠商動作，重用既有 `VENDOR_STATUS_MAP`（[delivery.py:9-17](../../../backend/app/services/delivery.py#L9-L17)）代碼：

| 動作 | 來源 order_status | 目標 order_status | 標籤 |
|---|---|---|---|
| `accept` | 01 | 02 | 商家已接單 |
| `prepare` | 02 | 03 | 開始備餐 |
| `pickup` | 03 | 04 | 外送員已取餐 |
| `dispatch` | 04 | 05 | 開始配送 |
| `deliver` | 05 | 70 | 已送達 |
| `reject` | 01／02／03 | 90 | 無法接單／取消 |

底層邏輯重用 `update_delivery_status_from_vendor`（[delivery.py:221](../../../backend/app/services/delivery.py#L221)）的狀態映射與 `status_history` 累加，但改造成不在函式內直接呼叫 `STORE.save_request`，而是回傳更新後的 dict，讓呼叫端（新的廠商端點）用 `save_request_if_version` 帶著樂觀鎖版本號寫入。`pickup`／`dispatch`／`deliver` 之後（04／05／70）不可再 `reject`，比照現有使用者端的取消限制（[delivery.py:210-211](../../../backend/app/api/delivery.py#L210-L211) 邏輯挪過來）。

新增端點（掛在 `/api/vendor/` 底下，例如 `/api/vendor/delivery-orders`、`/api/vendor/delivery-orders/{id}`、`/api/vendor/delivery-orders/{id}/{action}`），沿用 `get_current_vendor` 驗證身分後直接用 `vendor.vendor_id` 查 `VENDOR#{id}` 索引——跟現有 `vendor.py` 一樣不必特別檢查是不是 30，任何廠商帳號來查都只會看到自己名下的案件，歸屬完全由索引本身保證，這是既有機制既有的安全特性。

移除：
- `backend/app/api/delivery.py` 的 `simulate_delivery_status` 端點
- `frontend/src/api/delivery.ts` 的 `simulateDeliveryStatus`
- `frontend/src/pages/DeliveryFlowPage.tsx` 裡呼叫它的模擬按鈕區塊（約 [DeliveryFlowPage.tsx:560-570](../../../frontend/src/pages/DeliveryFlowPage.tsx#L560-L570)）

保留不動：`/api/webhooks/delivery-callback`（給真正第三方系統回呼用，屬於另一個行為者，不在本次「使用者 vs 廠商」的問題範圍內）。

### 3. 商城實體商品（`shop_purchase`）

`catalog.py` 的 `shop_purchase` 服務目前 `service_vendor_id: None`（[catalog.py:343](../../../backend/app/services/catalog.py#L343)），改成 `40`。新增內建示範帳號 `vendor40@demo.local`／「商城出貨中心」。

新增廠商動作，重用既有 `STATUS_PROGRESSION`（[shop.py:17](../../../backend/app/services/shop.py#L17)）：

| 動作 | 來源狀態 | 目標狀態 | 標籤 |
|---|---|---|---|
| `confirm` | SUBMITTED | CONFIRMED | 確認訂單／備貨 |
| `ship` | CONFIRMED | IN_PROGRESS | 出貨 |
| `deliver` | IN_PROGRESS | COMPLETED | 送達／完成 |
| `reject` | SUBMITTED | CANCELLED | 無法出貨 |

`reject` 不能只是把 `status` 改成 `CANCELLED`——商城訂單取消牽涉退點數與補庫存，必須走既有 `cancel_shop_order`（[shop.py:180](../../../backend/app/services/shop.py#L180)）的補償邏輯。這支函式目前沒有樂觀鎖版本檢查（使用者端本來就沒有這個問題，因為只有本人能取消自己的訂單），改成廠商也能呼叫後，要加上 `expected_version` 參數，內部用 `save_request_if_version` 取代目前無條件的 `save_request`，避免廠商看到的畫面跟案件當下版本不一致時誤觸。

`confirm`／`ship`／`deliver` 三個純狀態推進沿用既有 `STATUS_PROGRESSION` 線性表即可，不需要額外補償邏輯。

新增端點（`/api/vendor/shop-orders`、`/api/vendor/shop-orders/{id}`、`/api/vendor/shop-orders/{id}/{action}`），身分驗證後同樣直接用 `vendor.vendor_id` 查索引，不特別檢查是不是 40。

移除：
- `backend/app/api/shop.py` 的 `simulate_shop_order_progress` 端點與 `services/shop.py` 的 `advance_shop_order_status`
- `frontend/src/api/shop.ts` 的 `simulateShopOrderProgress`
- `frontend/src/pages/ShopFlowPage.tsx` 的 `handleSimulateAdvance` 與對應按鈕

## 前端廠商後台

[VendorRequestDetailPage.tsx](../../../frontend/src/pages/VendorRequestDetailPage.tsx) 目前寫死「接單」「婉拒」兩顆按鈕（[VendorRequestDetailPage.tsx:175-197](../../../frontend/src/pages/VendorRequestDetailPage.tsx#L175-L197)）。改成依 `detail.available_actions` 陣列動態渲染任意數量的動作按鈕，搭配一份 `ACTION_LABELS` / `DONE_MESSAGES` 對照表（涵蓋 `start`／`complete`／`verify`／`accept`／`prepare`／`pickup`／`dispatch`／`deliver`／`confirm`／`ship`／`reject`）。這樣三種案件可以共用同一套廠商後台頁面與列表頁（[VendorRequestsPage.tsx](../../../frontend/src/pages/VendorRequestsPage.tsx)），不需要為外送、商城另外做兩套 UI。

前端型別（[types/vendor.ts](../../../frontend/src/types/vendor.ts)）的 `VendorAction` 要從 `"accept" | "reject"` 擴充成涵蓋全部新動作的聯集型別。

外送／商城的案件詳情欄位渲染：沿用既有 `VendorRequestDetail.fields`（label/value 陣列）的形狀，後端把外送的地址／餐點清單、商城的購物車／收件資訊攤平成 field 列表回傳，前端不需要為這兩種案件另外寫欄位渲染邏輯。

## 資料回填

`shop_purchase` 舊訂單建立當時 `service_vendor_id` 還是 `None`，`_save_vendor_index`（[store.py:127-158](../../../backend/app/services/store.py#L127-L158)）在寫入當下算出 `vendor_id is None` 就直接跳過鏡射，所以舊訂單不會出現在 `VENDOR#40` 索引裡，即使之後 catalog 改了也不會回溯生效。

改完 catalog 後要跑 [backfill_vendor_index.py](../../../backend/scripts/backfill_vendor_index.py) 補齊索引。這支腳本目前遇到 `USE_MOCK=true`（本地開發預設值）會直接印訊息跳過（[backfill_vendor_index.py:71-73](../../../backend/scripts/backfill_vendor_index.py#L71-L73)），但本地的 `.local-store.json`（`MemoryStore`）其實有一模一樣的缺口——舊的 shop_purchase 測試資料一樣不會被鏡射。這支腳本要一併改成透過 `store.build_store()` 取得當前後端（不管是 DynamoDB 還是 MemoryStore）並支援兩者的回填。

## 測試計畫

- `backend/tests/test_vendor_portal.py`：擴充涵蓋新的 `start`／`complete`／`verify` 轉換與狀態機／樂觀鎖的邊界情況（例如案件不在允許來源狀態時回 409）
- `backend/tests/test_requests_simulate_reservation.py`：現有測試打的是即將刪除的端點，改寫成驗證新端點已移除（呼叫回 404）+ 新增一份走廠商端點推進 PENDING_PROVIDER → CONFIRMED → IN_PROGRESS → COMPLETED → VERIFIED 全流程的測試
- 新增 `backend/tests/test_vendor_delivery_orders.py`：涵蓋 accept/prepare/pickup/dispatch/deliver/reject 的狀態機、樂觀鎖、pickup 之後不可 reject 的邊界
- 新增 `backend/tests/test_vendor_shop_orders.py`：涵蓋 confirm/ship/deliver、reject 時退點數與補庫存是否正確、樂觀鎖版本衝突
- 前端：`VendorRequestDetailPage.test.tsx`、`VendorPages.visual.test.tsx`、`DeliveryFlowPage.test.tsx`、`ReservationFlowPage.test.tsx` 需要更新掉對舊模擬按鈕的斷言；新增廠商後台對外送／商城案件的渲染測試

## 風險與注意事項

- 三個端點群組（通用／外送／商城）都要記得在案件不屬於當下登入廠商（案件不在 `VENDOR#{vendor.vendor_id}` 索引裡）時回 404，不能洩漏其他廠商的案件是否存在——沿用 [vendor.py:168-184](../../../backend/app/api/vendor.py#L168-L184) `_load_case_or_404` 的既有防護邏輯，外送／商城端點直接照抄同一個寫法即可
- `reject` 動作在外送／商城都有「過了某個階段就不能拒」的限制，兩邊各自實作，不要漏掉
- [docs/demo-script.md](../../demo-script.md) 的 Demo 2 第 3 步「點（Demo）模擬廠商確認」會因為端點被刪除而失效，需要拿掉這一步。這其實順便修掉一個既有的邏輯矛盾：Demo 2 用模擬按鈕把案件變成 CONFIRMED，但 Demo 5 第 3 步又預期同一張案件在「待確認諮詢單」分頁——照原劇本順序執行到 Demo 5 時案件其實已經被 Demo 2 confirm 過了。拿掉 Demo 2 的模擬步驟後，「案件從送出到確認」只在 Demo 5（登入廠商後台按「接下這張單」）發生一次，前後一致。
