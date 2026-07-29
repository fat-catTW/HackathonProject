# 美食外送 × 語音/聊天機器人整合 Design

## 背景

「美食外送」（`food_delivery`）服務目前已經有完整的手動精靈頁（`DeliveryFlowPage.tsx`，5 步驟：地址→選店家→選餐點→確認→追蹤）與後端訂單邏輯（`backend/app/services/delivery.py`：`order_type=06`、外送範圍判斷、`vendor_data.delivery`、狀態碼對照表、取消規則），這條路線已可直接用、已掛上 `/services/food_delivery` 路由與首頁服務卡片。

`backend/app/services/catalog.py` 裡也已經預先放了 `food_delivery` 的 schema（`address`／`store_id`／`goods`／`contact_name`），但這只是半成品：`backend/app/agent/agent.py`（聊天機器人的核心狀態機）完全沒有處理這幾個特殊欄位型別的邏輯——`store_id` 沒有動態選項來源、`goods`（購物車）型別目前會被當一般文字囫圇吞棗地收下、送出時也沒有走 `delivery.create_delivery_order()`，會存成一筆格式不符、無法在追蹤頁顯示的一般案件。

對照組是「餐廳訂位」（`restaurant_reservation`）：它除了有自己的精靈頁（`ReservationFlowPage.tsx`，直接呼叫 `/api/reservations/*` REST API），**同時也在 `agent.py` 裡做了完整的聊天整合**（`_submit_reservation` 等），使用者可以純用文字/語音對話完成訂位。本次目標是讓「美食外送」比照辦理，補齊聊天機器人這條路徑。

## 目標

使用者可以在 ButlerPanel（聊天/語音介面）用一次一問的對話完成外送下單，訂單建立後與精靈頁下的單完全同構——存在同一個 `STORE`，可在「我的服務」的外送追蹤頁看到，資料結構完全相容 `DeliveryFlowPage` 既有的 tracking UI。

不追求功能對等於精靈頁的完整購物體驗（無加購選項結構化選擇、無地圖選點），目標是「展示这條路徑真的能跑通」，細節可之後再補。

## 非目標（本次不做）

- 加購選項（甜度/冰量/加蛋等 `modifier_group`）在聊天中的結構化選擇——聊天只收一段自由文字備註（`note`），不影響金額計算，也不寫入 `modifier_group`。
- 真實地理編碼／地圖選點——聊天下單一律使用示範中心點座標（`lat 25.033 / lng 121.565`，與 `DeliveryFlowPage` 現有預設值相同）。
- `lambda_tools/shared_lambda/catalog.py`（AWS Lambda 工具版本的服務目錄）同步——`restaurant_reservation` 本身也未同步進去，維持與現有模式一致，本次先以預設的 `embedded`/mock 模式（`USE_MOCK=true`）為準。
- 品項「已下架」重新檢核——店家/菜單資料目前是寫死的靜態清單，沒有上下架機制，不新增。
- 聊天中查詢外送進度（「我的外送到哪了」）——外送進度只透過精靈頁的追蹤畫面查看，聊天機器人不回答這類問題，維持跟其他服務（水電/清潔等也都沒有聊天查進度功能）一致的範圍。

## 架構

### 1. 店家目錄拆成共用模組

新增 `backend/app/services/delivery_catalog.py`，把目前寫死在 `backend/app/api/delivery.py` 裡的 `DELIVERY_STORES` 清單搬過去，仿照既有 `restaurant_catalog.py` 的形式（`list_stores()` / `get_store(store_id)` 等函式）。

- `backend/app/api/delivery.py` 改成從 `delivery_catalog` import 店家資料，行為不變。
- `backend/app/agent/nlu.py` 與 `backend/app/services/catalog.py` 都能安全 import 這個新模組（無循環引用問題，因為它跟 `restaurant_catalog.py` 一樣是純資料模組，被大家依賴而不依賴別人）。

### 2. Schema 補一個欄位

`catalog.py` 的 `food_delivery` schema 新增一個 `note`（自由文字，非必填）欄位，對應「有沒有別的需求，如全糖去冰」。`store_id` 的 `question` 動態列出 `delivery_catalog` 目前的店家名稱（比照 `restaurant_id` 欄位列餐廳名稱的寫法）。

### 3. NLU 新增兩個解析函式（`backend/app/agent/nlu.py`）

- `parse_delivery_store(text: str) -> str | None`：比對店家全名/簡稱，回傳 `store_id`。做法比照既有 `parse_restaurant()`。
- `parse_menu_item(text: str, store_id: str) -> dict | None`：在指定店家的菜單裡找出文字中提到的品項名稱，並用既有 `parse_quantity()` 邏輯抓數量（找不到數量預設 1 份）。回傳 `{"id", "title", "price", "quantity"}` 或 `None`（representing 沒配對到任何已知品項）。

### 4. Agent 狀態機新增「購物車收集」子流程（`backend/app/agent/agent.py`）

`goods` 是會累積的清單，沒辦法套用現有「一個 `field_id` 對一個值」的固定收集引擎，因此在 `state` 裡新增兩個暫存旗標（比照現有 `pending_pref_field` 的模式）：

- `pending_delivery_item`：目前正在等使用者說出下一個品項。
- `collected_fields["goods"]`：list，逐項 append。

流程：

1. 使用者說出想要的外送需求 → `_detect_service` 偵測到 `food_delivery`（沿用 `catalog.py` 裡已有的 `keywords: ["外送","美食","外帶","便當","飲料","點餐","delivery"]`，不需要额外改 `RULE_SERVICE_KEYWORDS`，因為 `restaurant_reservation` 也是靠 `nlu.detect_service` 這層 fallback 生效，不在那個清單裡）。
2. 問「請問想點哪一間店家？目前提供：好味道便當、鮮茶道、義式小館。」→ `parse_delivery_store` 解析成 `store_id`。
3. 進入加點迴圈：問「想點餐點裡的哪一項？可以先說一項，要加點我再問。」→ `parse_menu_item(text, store_id)`：
   - 配對成功 → 加進 `collected_fields["goods"]`，問「還要加點別的嗎？」（沿用既有 `_judge_reply` 是非判斷）。回答「要」→ 回到「想點哪一項」；回答「不要」→ 結束迴圈，繼續下一步。
   - 配對不到已知品項 → 用現有錯誤重問的口吻回覆「這個品項目前菜單上沒有找到，要不要換一個？」（不會把無效品項塞進購物車，也不會卡死，使用者可以重講）。
4. 走原本一次一問引擎收剩下欄位：地址（沿用既有 `parse_address` / `address` field_id 通用處理）→ 收件人姓名（`contact_name`）→「有沒有別的需求，如全糖去冰？」（`note`，非必填，允許直接跳過）。
5. 全部欄位到齊 → 沿用 `_build_summary_text` 產生摘要覆誦（購物車品項列出「品名 x 數量」），使用者確認後呼叫新增的 `_submit_delivery(actor_id, state, latest_user_message)`。

### 5. `_submit_delivery`（`backend/app/agent/agent.py`）

比照現有 `_submit_reservation` 的寫法：從 `state["collected_fields"]` 組出跟 `DeliveryFlowPage.handleSubmit()` 送出的 payload 同構的資料：

```python
{
    "address": {
        "lat": 25.033, "lng": 121.565,  # 示範中心點，固定值
        "city": "台北市", "area": "", "street": <parsed address text>,
        "remark": "", "contact_name": <contact_name>,
    },
    "goods": <collected cart list>,
    "store_id": <store_id>,
    "store_name": <store name looked up from delivery_catalog>,
    "store_address": <store address looked up from delivery_catalog>,
    "note": <note or "">,
    "shipping_fee": 60,  # 與精靈頁常數一致
}
```

呼叫 `delivery.create_delivery_order(actor_id, payload)`，成功則沿用既有 `submit_success` 回覆樣板回報 `request_id`；失敗（例如 `EMPTY_CART`）則沿用既有 `submit_error` 樣板。

### 6. 外送進度 Demo 模擬按鈕（`frontend/src/pages/DeliveryFlowPage.tsx`）

在 tracking 步驟加一顆「Demo：模擬下一個狀態」按鈕，比照 `RequestDetailPage.tsx` 現有的模擬按鈕邏輯，依序推進 `vendor_status`（0→1→2→3→4→5，對應平台 `order_status` 01→02→03→04→05→70），並帶入一組假外送員資訊（姓名、電話、預估到達分鐘數）讓畫面能展示 `vendor_data.delivery` 有值可顯示。這顆按鈕只存在於精靈頁的追蹤畫面，聊天機器人不會用到它（聊天機器人本身不查詢/操作進度）。

規劃階段發現既有的 `POST /api/webhooks/delivery-callback` 是給第三方系統用的無登入 webhook，需要呼叫端自帶 `actor_id`——前端目前只有 demo token，並不知道對應的 `actor_id`（`sub`），直接從瀏覽器帶明碼 `actor_id` 呼叫也不是好做法。因此改成新增一支**走既有登入驗證**的 Demo 專用端點 `POST /api/delivery/orders/{request_id}/simulate`（body: `{"vendor_status": int, "delivery": {...} | None}`），內部直接呼叫既有的 `delivery.update_delivery_status_from_vendor()`——跟 webhook 走的是同一段更新邏輯，只是換一個有登入驗證的入口，行為完全等價。

需要在 `frontend/src/api/delivery.ts` 新增對應的 fetch 函式呼叫這支新端點。

## 資料流一致性

不論訂單是從精靈頁還是聊天機器人建立，最終都會呼叫同一個 `delivery.create_delivery_order()`，寫入同一個 `STORE`，`order_type=06` / `vendor_data.delivery` / `order_status` 對照表等既有邏輯完全不變，追蹤頁與「我的服務」清單能正確顯示兩種來源的訂單。

## 測試範圍

不採用「餐廳訂位」那種完整 TDD 多任務、hypothesis property test 的規模，改用一般 pytest 補基本案例：

- `parse_delivery_store`：正確店名、簡稱、找不到店家。
- `parse_menu_item`：正確品項＋數量、只講品項無數量（預設 1）、講不存在的品項。
- `_submit_delivery`：成功建立訂單、購物車為空、店家不存在。

前端不特別加測試（現況 `DeliveryFlowPage` 本身也沒有測試檔），改動完成後會實際啟動前後端手動跑一次完整對話下單流程與 Demo 模擬按鈕。

## 已知限制（留給之後調整）

- 聊天下單一律用示範座標，無法像精靈頁一樣展示「超出外送範圍」錯誤（因為聊天沒有地圖，永遠落在範圍中心點）。
- 加購選項只能靠自由文字備註表達，不會反映在金額或 `modifier_group` 結構裡。
- AWS Lambda 版本的服務目錄（`lambda_tools/shared_lambda/catalog.py`）尚未同步 `food_delivery`／`restaurant_reservation`，兩者都仍停留在 embedded/mock 模式；正式部署到 AWS 前需要另外處理這塊同步（不在本次範圍）。
