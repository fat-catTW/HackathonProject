# 包裹寄送留資表單 Design

## 背景

命題方（統一資訊）的原始題目要求「住」／延伸生活場景下有一個包裹寄送留資表單：使用者填寫寄／收件地址與包裹資訊、選擇取件時段，送出後轉交服務廠商（`service_vendor_id=2`）報價或排定收件。命題方也提供了一份「諮詢單 → 訂單」轉單邏輯（M2）作為資料模型參考（`pms_form_feedback` → `mms_order_record`，`order_type`/`order_status` 數字碼、訂金/報價欄位等）。

為了讓提案更貼近「統一資訊」的真實資產，本次調研確認：**黑貓宅急便的經營主體「統一速達」本身就是統一超商轉投資成立的子公司**，7-ELEVEN 交貨便（店到店）也是統一速達收送件的其中一個通路，不是另一家公司。因此本功能用同一個廠商（`service_vendor_id=2`，命名「統一速達（黑貓宅急便）」）代表這個服務商，「到府收件」與「7-11 店到店」是這個廠商底下的兩種取件方式，各自套用對應通路的真實資費結構：

- **到府收件（黑貓宅急便宅配，三邊合計計費）**：≤60cm 約 NT$110、61–90cm 約 NT$150、91–120cm 約 NT$190；超過 120cm 或 20kg 需改走其他貨運，本功能不受理。
- **7-11 店到店（交貨便）**：本島常溫 NT$60（限重 ≤5kg、三邊合計 ≤105cm）；106–120cm 大包裹 NT$125–135（同樣限重 ≤5kg）；超過三邊合計 120cm、重量 5kg，或申報價值超過 NT$5,000，需改走到府收件。（官方最長邊 ≤45cm 的細則只查到適用於常溫基本方案，「大包裹」方案是否放寬單邊限制沒有查到明確資料，為避免規則互相矛盾，本功能的分級與擋下判斷一律只用「三邊合計＋重量」，不額外檢查單邊長度。）

現有專案的服務目錄（`backend/app/services/catalog.py`）已經有兩種實作模式：水電/清潔/冷氣/洗衣機是純 schema 驅動、完全靠 AI 管家一次一問對話收集（`backend/app/agent/agent.py` 的通用收集引擎 + `backend/app/agent/tools.py` 的 `submit_service_request`）；餐廳訂位/美食外送則各自有專屬服務模組（`reservation.py`/`delivery.py`）與 `_submit_reservation`/`_submit_delivery` 專用提交函式，因為需要額外的驗證、費用、狀態碼邏輯。本功能因為有取件方式分岔、運費試算、違禁品確認等自訂邏輯，比照後者的模式。

## 目標

使用者可以在 AI 管家（聊天/語音介面）用一次一問的對話完成包裹寄送留資表單：選取件方式 → 依方式分岔問寄件/收件地址或門市 → 包裹重量與材積 → 內容物概述（含違禁品關鍵字攔截）→ 申報價值 → 取件時段 → 聯絡資料 → 摘要確認 → 送出。送出後依重量/材積試算「預估運費區間」文字回覆，並建立一筆狀態為「待廠商報價」的案件，流程與其餘服務一致地出現在「我的服務」與廠商後台。

## 非目標（本次不做）

- 不接真實 7-11 門市查詢/選店 API——寄件人/收件人的取件門市用自由文字輸入，不做地圖選點或門市代碼驗證。
- 不做即時秤重/材積機器驗證——重量與尺寸完全依使用者自述輸入，試算出的運費是「預估區間」，不是保證價，最終仍需人工報價（沿用原題目「客服將於 30 分鐘內回覆報價」的精神，只是把區間先顯示出來）。
- 不引入命題方 M2 提到的 `mms_order_record` 正式資料表結構或 `pms_form_feedback` 來源欄位——沿用現有專案已經在用的內部 `order_type`/`order_status` 數字碼慣例（`reservation.py`/`delivery.py` 已有前例），只新增一個目前沒用過的代碼，不建立平行的資料模型。
- 不做防重複送單的資料層去重（`feedback_no` 唯一索引）——沿用全站既有「送出前必經確認摘要」的 UX 原則，不額外加後端層級的重複偵測。
- 不做「廠商停用/超區域」的人工工單通知機制——服務啟用與否沿用 `catalog.py` 既有的 `enabled` 開關；超區域（本次 demo 用外島縣市清單）直接在送出前擋下並提示，不寫入待人工複核的案件。
- 不新增獨立的多步驟精靈頁（比照 `DeliveryFlowPage.tsx`）——沿用通用表單引擎，manual 表單渲染（`FieldPanel`）與對話走同一份 schema。

## 架構

### 1. 服務目錄新增 `package_shipping`（`backend/app/services/catalog.py`）

新增一筆 `SERVICES` entry，`id="package_shipping"`，`service_vendor_id=2`，`cms_type` 暫用內部保留碼 `"20"`（本次未取得官方資料集的正式代碼表，比照現有 `delivery.py` 的 `order_type="06"`、`reservation.py` 的 `"02"` 這種各服務自訂數字碼的既有慣例，之後若拿到官方代碼可再對應調整）。`keywords` 包含「包裹」「寄件」「寄送」「宅配」「黑貓」「交貨便」「寄快遞」等。

Schema 欄位（依對話順序）：

| field_id | type | required | 備註 |
|---|---|---|---|
| `pickup_method` | select | 必填 | `HOME_PICKUP`（到府收件）/ `STORE_TO_STORE`（7-11 店到店） |
| `sender_address` | address | 必填，`visibleWhen pickup_method=HOME_PICKUP` | 沿用既有 `address` 型別（`nlu.parse_address`，含 22 縣市＋約 200 行政區驗證），不新增欄位型別 |
| `receiver_address` | address | 必填，`visibleWhen pickup_method=HOME_PICKUP` | 同上 |
| `sender_store` | text | 必填，`visibleWhen pickup_method=STORE_TO_STORE` | 7-11 門市名稱，純文字，不做門市代碼驗證 |
| `receiver_store` | text | 必填，`visibleWhen pickup_method=STORE_TO_STORE` | 同上 |
| `weight_kg` | number | 必填 | |
| `length_cm` / `width_cm` / `height_cm` | number | 必填 | 三邊合計用來試算運費與檢查上限 |
| `item_description` | textarea | 必填 | 內容物概述，同時作為違禁品關鍵字比對來源 |
| `declared_value` | number | 必填 | 申報價值（僅店到店會檢查 ≤5,000 上限） |
| `pickup_time_slot` | time | 必填 | 沿用其他服務的 `minValue`/`maxValue`/`step` 慣例 |
| `contact_name` / `phone` | text | 必填 | |

> 「型別5（縣市/行政區選單）」的落地方式：不新增獨立的 cascading select 型別元件，改成沿用專案裡已經在跑的 `address` 型別（`food_delivery` 的 `address` 欄位就是這樣做，靠 `nlu.parse_address` 解析＋驗證縣市/行政區），一次多一個地址欄位即可達到同樣的驗證效果，不需要新的前後端元件。

### 2. 修正通用收集引擎的兩個既有缺口（`backend/app/agent/agent.py`）

這兩點是分岔表單能「一次一問」運作的前提，屬於既有邏輯的缺陷修正，不是本功能專屬的特例邏輯：

- **`_recompute_missing()`（第 243–249 行）目前不檢查 `visibleWhen`**，只檢查 `required`。改成比照 `tools.py` 的 `_field_is_visible()` 邏輯，跳過目前不可見的欄位，否則到府/店到店兩組欄位會被同時追問。
- **`_normalize_field_value()` 的地址分支目前用 `field_id == "address"` 硬編碼判斷**（第 552–553 行），只支援單一地址欄位。改成判斷 `field["type"] == "address"`，讓 `sender_address`/`receiver_address` 都能走同一套 `nlu.parse_address` 正規化。

同時需要新增：

- `FIELD_DISPLAY_NAMES` / `_display_field_label` 的 fallback 補上新欄位中文標籤。
- `_build_field_question()` 補上新欄位的口語化提問句（例如 `pickup_method` 問「請問希望到府收件，還是要用 7-11 店到店寄件呢？」）。
- `SERVICE_DISPLAY_NAMES` / `_display_service_name` 補上 `package_shipping: 包裹寄送`。
- `SELECT_ALIASES` / `SELECT_DISPLAY_NAMES` 補上 `HOME_PICKUP`/`STORE_TO_STORE` 的口語別名（「到府」「到府收件」「店到店」「超商」「7-11」等）與顯示名稱。

### 3. 違禁品確認子流程（`backend/app/agent/agent.py`）

比照現有 `pending_delivery_field`（外送購物車收集）的模式，新增一個中斷旗標 `pending_prohibited_confirm`：

1. `item_description` 收集到值後，呼叫 `shipping.contains_prohibited_keywords(text)`（見下方第 4 節），比對黑貓/7-11 官方違禁品分類的關鍵字（電池、易燃、易碎、玻璃、生鮮、冷藏、精密儀器、3C、家電、有價證券、票券等）。
2. 命中時不直接把 `item_description` 寫進 `collected_fields`，而是設定 `state["pending_prohibited_confirm"] = {"matched": [...], "raw_text": text}`，回覆列出命中的違禁分類並要求使用者確認「已詳讀寄送規範，確認可以寄送」。
3. 使用者確認（`_judge_reply` 判斷 yes）→ 把 `item_description` 寫入 `collected_fields`，清除旗標，繼續收集；使用者否認/不確定 → 提示「請重新描述包裹內容物」，清除旗標但不寫入欄位，讓下一輪重新收集 `item_description`。
4. 未命中關鍵字則跟現有欄位一樣直接寫入，不中斷流程。

### 4. 新增服務模組 `backend/app/services/shipping.py`

比照 `reservation.py` 的結構（`_error()`、`_validate_payload()`、`create_shipping_order()`）：

- **`_validate_payload(payload)`**：檢查必填欄位；依 `pickup_method` 檢查對應的重量/材積上限（到府收件三邊合計 >120cm 或重量 >20kg 擋下；店到店三邊合計 >120cm、重量 >5kg，或 `declared_value` >5000 擋下，訊息建議改用另一種取件方式或聯繫客服；只用三邊合計＋重量判斷，不檢查單邊長度，理由見上方背景說明）；檢查寄件地址是否在 demo 用的服務限制清單（`EXCLUDED_COUNTIES = {"金門縣", "連江縣", "澎湖縣"}`，僅在 `pickup_method=HOME_PICKUP` 時檢查 `sender_address` 解析出的縣市）。
- **`estimate_shipping_fee(pickup_method, weight_kg, length_cm, width_cm, height_cm) -> tuple[int, int]`**：依前述兩組真實資費分級規則回傳 `(fee_min, fee_max)`。到府收件三個級距回傳單一值（`fee_min == fee_max`）；店到店常溫回傳 `(60, 60)`，大包裹級距回傳 `(125, 135)`。
- **`contains_prohibited_keywords(text) -> list[str]`**：關鍵字表比對，回傳命中的分類名稱清單（可能為空）。
- **`create_shipping_order(actor_id, payload) -> dict`**：驗證 → 試算運費 → 組 `order_items`/`form_data` → `order_type="20"`（同上，內部保留碼）、初始 `order_status="01"`、`status="AWAITING_QUOTE"` → `STORE.save_request()` → 回傳 `{success, request_id, status, order_status, estimated_fee_min, estimated_fee_max}`。

### 5. Agent 提交函式 `_submit_package_shipping`（`backend/app/agent/agent.py`）

比照 `_submit_reservation`/`_submit_delivery`：從 `state["collected_fields"]` 組 payload 呼叫 `shipping.create_shipping_order()`；失敗走既有 `submit_error` 回覆樣板；成功則在 `submit_success` 回覆裡多帶一段運費區間文字（複用 `_fallback_reply`/`llm.compose_reply` 既有的 `submit_success` phase，新增 `estimated_fee_min`/`estimated_fee_max` kwargs，文案：「已幫你建立案件 {request_id}，依重量與材積試算，預估運費約 NT${min}–{max}，正式報價將由客服於 30 分鐘內回覆確認。」）。`_submit()`（第 1055 行附近）新增 `state["service_id"] == "package_shipping"` 的分支導向這支函式，比照現有 `restaurant_reservation`/`food_delivery` 的寫法。

### 6. 案件狀態（`backend/app/services/statuses.py`）

新增 `AWAITING_QUOTE: "待廠商報價"`，並加進 `VENDOR_PENDING_STATUSES`（廠商後台「待處理諮詢單」分頁要看得到）。後續狀態轉移（廠商回覆正式報價後 → `CONFIRMED` → `IN_PROGRESS` → `COMPLETED`）沿用既有狀態機與廠商後台既有的（目前唯讀）案件明細顯示，不需要新的 UI。

### 7. 廠商帳號（`backend/app/config.py`）

`_BUILTIN_VENDOR_ACCOUNTS` 新增 `vendor2@demo.local`：`{"vendor_id": 2, "name": "統一速達（黑貓宅急便）", "password": "vendor1234"}`，密碼比照現有兩組示範帳號慣例。

## 資料流一致性

不論之後是否有其他入口，目前唯一的建立路徑是 `_submit_package_shipping()` → `shipping.create_shipping_order()`，寫入同一個 `STORE`，`service_id="package_shipping"`／`service_vendor_id=2`／`order_type="20"` 等欄位固定不變。廠商後台既有的「依 `service_vendor_id` 篩案件」與「案件明細顯示 `form_data`」機制不需修改即可支援這個新服務，因為它們是通用邏輯，不是寫死特定服務的欄位。

## 測試範圍

比照 `food_delivery`/`restaurant_reservation` 現有測試的規模與檔名慣例，一般 pytest（不採 hypothesis property test）：

- `backend/tests/test_catalog_shipping.py`：`package_shipping` schema 欄位完整性、`visibleWhen` 設定正確。
- `backend/tests/test_shipping_service.py`：`estimate_shipping_fee` 各級距（到府三段、店到店常溫/大包裹）、`contains_prohibited_keywords` 命中與不命中案例、`_validate_payload` 重量/材積/申報價值超限、外島地址擋下、`create_shipping_order` 成功案例（含 `order_status`/`status` 正確寫入）。
- `backend/tests/test_agent_shipping_submit.py`：比照 `test_agent_delivery_submit.py`/`test_agent_reservation_submit.py`，涵蓋完整對話流程（到府收件與店到店各跑一次分岔）、違禁品關鍵字觸發確認子流程、`_recompute_missing` 在分岔情境下不會多問另一分支的欄位（這是回歸測試，順便驗證第 2 節的既有缺陷修正沒有破壞其他服務）。

前端不特別加測試（現況通用 `FieldPanel`／對話 UI 本身也沒有針對個別服務的測試檔），改動完成後會實際啟動前後端手動跑一次到府收件與店到店兩種完整對話下單流程。

## 已知限制（留給之後調整）

- 運費是依使用者自述重量/材積試算的「預估區間」，不是保證價，也沒有真實秤重覆核機制——如果 demo 現場被問「如果使用者亂填重量怎麼辦」，誠實說明是預估報價、實際以廠商到場/秤重後的正式報價為準（這也是原題目本來就允許的設計）。
- 7-11 門市（`sender_store`/`receiver_store`）是自由文字，沒有真實門市清單或地址查詢，示範時建議直接打門市全名。
- `cms_type`/`order_type` 用的 `"20"` 是專案內部沿用既有慣例的保留碼，不是命題方官方資料集裡的正式代碼（本次沒有取得該對照表）；如果之後拿到附件裡的正式欄位/代碼定義，需要回來對應修改。
- `lambda_tools/shared_lambda/catalog.py`（AWS Lambda 版本的服務目錄）與 `lambda_tools/tool_schemas/*.json` 尚未同步 `package_shipping`，跟 `food_delivery`/`restaurant_reservation` 現況一致，仍停留在 embedded/mock 模式；要走 Milestone 4 的 MCP Gateway 部署前需要另外同步（不在本次範圍）。
- demo 用的外島服務限制清單（金門/連江/澎湖）只是為了讓「超區域」edge case 在展示時可以被觸發，不代表黑貓/7-11 實際上完全不服務這些地區，正式上線前需要用真實服務範圍資料取代。
