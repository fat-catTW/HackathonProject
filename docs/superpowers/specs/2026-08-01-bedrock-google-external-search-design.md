# Bedrock + Google 外部搜尋推薦（設計書）

## 目標

三個現有的「關鍵字/Gemini 比對內部清單」推薦點，改成「Bedrock 判斷查詢 + Google API 搜尋外部結果 + Bedrock 排序推薦」，內部清單保留為候選池之一，不整個丟掉。外部結果一律標明來源，且不能直接享有內部清單品項的交易保證（庫存/點數/第三方訂位 API）。

涉及：
1. 健康商品推薦（`health_recommendation.py`）
2. 供品／水果快速購買（`quick_purchase_catalog.py` / `quick_purchase.py`）
3. 餐廳訂位依地址搜尋（`restaurant_catalog.py` / `reservation.py` / `booking_adapter.py`）

附帶修復：`shop_price_compare` 既有 bug（`agent.py` 呼叫的 `_answer_price_compare` 未定義，`test_shop_price_compare.py` 現有 3 個測試 FAILED）。比價機制本身（內部點數比價）不套用 Google 搜尋，維持現狀。

## 共用架構

### 新模組：`app/services/external_search.py`
- `google_text_search(query: str) -> list[dict] | None`：呼叫 Google Custom Search JSON API，回傳 `[{title, snippet, link}]`；未設定金鑰或呼叫失敗回傳 `None`。
- `google_places_search(query: str, *, location: str | None) -> list[dict] | None`：呼叫 Google Places API Text Search，回傳 `[{place_id, name, address, rating, ...}]`；同上失敗回傳 `None`。
- 新增設定（`app/config.py` + `.env.example`）：`GOOGLE_SEARCH_API_KEY`、`GOOGLE_SEARCH_ENGINE_ID`、`GOOGLE_MAPS_API_KEY`。

### Bedrock 兩段式（沿用 `llm.py` 既有 `_converse_json` 風格，新增對應 system prompt 常數）
1. `plan_external_query(user_text, context) -> str`：把使用者需求轉成搜尋字串。
2. 後端執行對應的 Google API 呼叫。
3. `rank_external_results(query, candidates: list[dict]) -> list[dict]`：Bedrock 從**候選池**（內部清單 + Google 結果）挑最多 N 筆並附推薦理由，只能回傳候選池裡真實存在的 id（沿用 `health_recommendation.py` 現有的防幻覺寫法）。

### 三層 fallback
Google 金鑰未設定 → Bedrock 不可用（`llm.is_available()` 為 False）→ Google API 呼叫例外/逾時，任一層失敗都整段退回現有的內部關鍵字比對邏輯（不拋錯、不中斷對話），沿用現有 `fallback_used` 欄位慣例。

### 來源標記
每筆推薦結果帶 `source: "internal" | "google_search" | "google_places"`。對話回覆文字需區分「這是內部特約商品/店家」vs「這是我在網路上額外找到的」。

### Server 端結果暫存與核對（信任邊界）
外部搜尋結果先寫入呼叫者的短期暫存（比照 `state["health_last_recommendations"]` 現有模式；餐廳訂位走 REST API、非對話流程，改用 `STORE` 依 `actor_id` 存最近一次搜尋結果，TTL 30 分鐘）。使用者要對外部結果「下單/訂位」時，後端用結果 id 回頭核對暫存資料，不接受前端直接夾帶店名/地址/商品資訊建立案件；找不到對應暫存（過期或從未搜尋）就回錯誤，請使用者重新搜尋。

## 各功能點

### 1. 健康商品推薦
移除 `_analyze_with_gemini`（含 `GEMINI_API_KEY` 相關程式碼，這是目前唯一用到 Gemini 的地方），改用共用的 Bedrock 兩段式，候選池 = `health_catalog.py` 內部商品 + Google 搜尋結果。`fallback_recommend`（關鍵字比對）保留作為最終 fallback。

### 2. 供品／水果快速購買
`quick_purchase_catalog.QUICK_PURCHASE_BUNDLES` 保留作為候選池一部分，`match_bundle` 保留作為 fallback。新增 Google 搜尋分支：Bedrock 選中外部結果時，不再呼叫 `shop.create_shop_order`（會因 `sku_id` 不在 `shop_catalog` 而失敗），改為直接建立一筆案件，狀態 `PENDING_PROVIDER`，不做庫存/點數異動，`form_data` 存搜尋結果的原始資訊（名稱/連結/描述）。

### 3. 餐廳訂位依地址搜尋
新增依地址搜尋端點/流程：Bedrock 把地址＋偏好轉成 Google Places 查詢，取前 **5 家**排序＋理由，跟內部 `RESTAURANTS` 清單合併呈現、標示來源。

`reservation.create_reservation_order` 修改：
- 內部特約店家（`supports_booking_api=True`）：流程不變，走 `MockEZTableAdapter`。
- Google 搜尋來源的店家：一律不呼叫訂位 adapter，直接建立 `PENDING_PROVIDER` 狀態的訂位案件（比照現有「`supports_booking_api=False` 的內部店家」既有路徑，不另開新分支）。`restaurant_id` 改接受 Google `place_id`，店家資訊從「Server 端結果暫存」核對取得，不信任前端傳入的店名/地址欄位。

## 附帶修復：`shop_price_compare`
補上 `agent.py` 缺失的 `_answer_price_compare(text, auth_token) -> (reply, redirect_path)`，呼叫既有的 `compare_product_prices` embedded tool（`shop_catalog.find_compare_group_id_by_query` + `list_compare_offers`），依 `test_shop_price_compare.py` 既有測試預期組回覆文字與 `redirect_path`。純粹修 bug，不套用 Google 搜尋。

## 測試方向
每個新分支（Bedrock 可用/不可用、Google 金鑰有無、Google 呼叫失敗、候選池挑選、pending 案件建立、server 端核對失敗）各補 1-2 個單元測試，比照現有 `test_shop_price_compare.py` / `test_restaurant_catalog.py` 的寫法即可，不需要額外設計新的測試框架。

## Out of scope
- 比價推薦（`shop_price_compare`）語意本身（維持內部點數比價，不接 Google）。
- 前端 UI 改版（本次先讓後端 API/agent 回覆支援外部來源標記與 pending 案件；前端顯示樣式後續再視情況調整）。
- 真的申請/設定 Google API 金鑰（本次只加程式碼與設定欄位，未設定金鑰時走 fallback，不影響現有 Demo）。
