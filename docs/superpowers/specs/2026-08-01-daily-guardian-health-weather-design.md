# 設計文件：日常的守護（天氣卡片 + 健康諮詢掛號情境）

日期：2026-08-01
動機：「台中添財阿伯」情境二——平日獨居長輩的一天。早上看天氣、下午覺得不舒服時，用語音描述症狀就能找到附近診所、掛號、順便加購對症商品，並自動產生一則可分享給子女的通知文字。防詐相關內容與「一鍵產生早安圖」不在本次範圍。

## 範圍與優先順序

1. **症狀諮詢 → 找診所 → 掛號 → 商品加購 → 通知家人**（核心，情境二下午段落的主體）
2. **首頁天氣卡片 + 語音朗讀**（情境二上午段落，範圍縮小為卡片本身，不含早安圖產生器）

不在本次範圍：防詐相關文案／頁面（沿用既有 `/scam-check`，不重複建設）、「早安圖」圖片產生與分享、家人聯絡人資料模型、任何真的對外發送機制（LINE/簡訊 API）。

---

## 功能一：症狀諮詢 → 找診所 → 掛號 → 加購 → 通知家人

### 現況與落差
- 現有「健康商品推薦」（`health_recommendation.py` + `HealthRecommendationPage`）只做飲食/營養商品推薦，商品清單（`health_catalog.py`）裡沒有感冒/喉嚨不適相關品項，也完全沒有「診所」「掛號」的概念。
- 「餐廳訂位」（`restaurant_catalog.py` + `reservation.py` + `ReservationFlowPage`）是最接近的既有模式：靜態場所清單 + 日期時段 + 聯絡資訊 + 送出即建立案件，本次直接沿用這個形狀，不重造。
- 家人分享機制（`ShareWithFamilyButton.tsx`，見情境一設計文件）已經存在且完全符合「同步通知子女」的需求——不需要新增家人聯絡人資料表或任何真的發送機制，本次只需要生成正確的分享文字並在掛號/加購完成畫面掛上這顆既有按鈕。

### 設計

**1. 診所真實資料來源：衛福部健保署「健保特約醫事機構－診所」開放資料**

已實測確認為可用、免金鑰、每日更新的公開 API：
```
GET https://info.nhi.gov.tw/api/iode0010/v1/rest/datastore/A21030000I-D21004-009?limit=1000&offset=0
```
回傳欄位（實測得到的真實 schema）：`HOSP_ID`、`HOSP_NAME`、`HOSP_CODE_CNAME`（機構種類）、`TEL`、`ADDRESS`、`FUNCTYPE_CNAME`（診療科別，逗號分隔字串，例如「內科,眼科,復健科」）、`HOLIDAYDUTY_CNAME`（21 段式看診時段字串：星期×上午/下午/晚上×看診/休診）、`CONT_S_DATE`、`CLOSESHOP` 等。

新增 `backend/app/services/clinic_catalog.py`：
- `fetch_clinics()`：呼叫上述 API，分頁抓取（每頁 1000 筆，設 5 頁上限 = 5000 筆，10 秒逾時），失敗或逾時直接回退到本模組內建的靜態清單（3–5 筆真實診所資料，含情境腳本裡的「王耳鼻喉科」），與專案既有 fallback 慣例一致（比照 `health_recommendation.py`／`booking_adapter`）。
- 記憶體快取抓回的資料 24 小時（比照資料集「每日更新」的頻率，避免每次請求都重打政府 API）。
- `list_clinics(city: str, district: str, specialty: str | None) -> list[dict]`：在快取資料中以 `ADDRESS` 是否包含 `f"{city}{district}"` 做地區篩選（不使用 `GOVAREANO` 欄位——其編碼規則與本專案 `tw_regions.json` 的行政區代碼不保證一致，用地址文字比對更可靠也更好除錯），再以 `specialty in FUNCTYPE_CNAME` 篩選科別；回傳時附加 `is_open_now`（依 `HOLIDAYDUTY_CNAME` 解析今天星期＋現在時段是否為「看診」）。
- 這一層只負責「查詢＋整理原始資料」，不做推薦判斷。

**2. 症狀 → 科別 → 推薦文字：新增 Bedrock 判斷函式**

`backend/app/agent/llm.py` 新增（比照既有 `check_scam_message`／`choose_service` 的 `_converse_json` 呼叫模式，不新建另一套呼叫機制）：
```python
def triage_symptom(symptom_text: str) -> dict | None:
    # 回傳 {"specialty": "耳鼻喉科", "advisory": "聽起來像是感冒了，要多喝溫水喔！"}
```
搭配新的 `_SYMPTOM_TRIAGE_SYSTEM` 提示詞，限制 `specialty` 只能是既有科別清單中的一個值（避免模型自創清單中不存在的科別，導致後續 `list_clinics` 篩不到任何診所）。`llm.is_available()` 回傳 false（沒有 AWS 憑證）時，退回一份小型規則式關鍵字對照表（咳嗽/喉嚨/鼻塞→耳鼻喉科、頭痛/發燒→家醫科、肚子痛→腸胃科…），與 `is_available()` 為 false 時其餘既有 Bedrock 呼叫的退回方式一致。

```python
def recommend_clinic(symptom_text: str, candidates: list[dict]) -> dict | None:
    # 輸入：症狀描述 + list_clinics() 查到的真實候選清單
    # 輸出：{"clinic_id": "...", "reason": "步行只要 5 分鐘，現在有看診"}
```
把 `list_clinics()` 查到的真實候選（含地址、電話、`is_open_now`、科別）整理成文字餵給 Bedrock，讓模型從真實資料中選一間並給理由，而不是規則式排序（例如優先挑最近的）——這正是這次要接外部 API 的目的：讓模型基於**真實資料**做判斷，而非寫死的邏輯。候選清單為空、或 Bedrock 不可用時，回傳候選清單中 `is_open_now=True` 的第一筆並附上制式理由，維持功能不中斷。

**3. 加購推薦：新增 Bedrock 判斷函式（僅限本次新流程使用）**

```python
def recommend_health_products_for_symptom(symptom_text: str, products: list[dict]) -> dict | None:
```
延用 `health_catalog.py` 的商品清單（本次新增 3–4 筆感冒/喉嚨相關品項，如「無糖喉糖」「川貝枇杷膏」，並在 `health_recommendation.py` 既有的 `HEALTH_KEYWORDS` 補上「感冒」「喉嚨」「咳嗽」關鍵字，讓規則式 fallback 也查得到這幾樣新商品），但推薦引擎改叫上面這個新的 Bedrock 函式，而不是既有的 `health_recommendation.recommend()`（那個函式明確標註是刻意保留給「健康商品推薦」頁使用 Gemini 的既有決策，本次不動它，避免影響既有功能的既定行為）。Bedrock 不可用時退回 `health_recommendation.fallback_recommend()` 的關鍵字比對邏輯（重用既有函式，不重寫一份）。

**4. 掛號本身：新的獨立服務，不進對話狀態機**

新增 `backend/app/services/clinic_appointment.py`（比照 `reservation.py` 的形狀）：
- `create_appointment(actor_id, payload)`：驗證 `clinic_id`／`date`／`time`／`contact_name`／`phone`／`symptom_note`，一律直接視為掛號成功（demo 用途，不像餐廳訂位需要串接第三方訂位系統的成功/失敗判斷），透過 `STORE.save_request` 寫入，`service_id="clinic_appointment"`。`form_data` 沿用 `contact_name`／`phone` 欄位名稱，因此自動套用既有的聯絡資訊加密與遮罩（`contact_privacy.py` 的 `CONTACT_FIELDS` 是依欄位名稱比對，不分服務種類）。
- 新增 API（`backend/app/api/clinics.py`，比照 `reservations.py`）：
  - `GET /api/clinics?city=&district=&specialty=`
  - `POST /api/symptom-triage` body `{symptom_text}` → `{specialty, advisory, clinics: [...], recommended_clinic_id, recommend_reason}`（內部依序呼叫 `triage_symptom` → `list_clinics` → `recommend_clinic`，一次回傳給前端，減少來回）
  - `POST /api/clinic-appointments` → `create_appointment`
  - `GET /api/clinic-appointments/{request_id}`
  - `POST /api/clinic-appointments/{request_id}/cross-sell` body `{}` → 內部用該筆掛號存的 `symptom_note` 呼叫 `recommend_health_products_for_symptom`，回傳推薦商品
- 註冊進 `catalog.py`（`clinic_appointment` 服務，id/name/vendor 皆無需廠商）、`frontend/src/data/services.ts`（新增一筆 `fields: []` 的服務定義，比照 `restaurant_reservation`）、`page_catalog.py` 的 `SERVICE_FORM_ALIASES`（讓「掛號」「看醫生」「診所」等語音關鍵字能被頁面問答與 `agent.py` 的一行導頁特例正確辨識）。
- `agent.py` 只新增與 `shop_purchase` 完全同構的一行特例（`_handle_one_shot_service` 內）：偵測到 `clinic_appointment` 時直接導頁到 `/services/clinic_appointment`，不進入通用表單欄位收集流程。**不改動、不擴充既有 2000 多行的狀態機邏輯本身。**

**5. 前端流程頁：`ClinicConsultFlowPage.tsx`（路徑 `/services/clinic_appointment`）**

比照 `ReservationFlowPage.tsx` 的 step-based wizard 寫法：

| step | 內容 | 重用元件 |
|---|---|---|
| symptom | 語音／文字描述症狀 | `VoiceButton` + `useSpeechRecognition`（同 `HealthRecommendationPage`） |
| clinic | 顯示 AI 建議科別＋建議語＋推薦診所（附理由），可切換縣市/鄉鎮區（用既有 `twRegions.ts`，預設「台中市」「西屯區」對應腳本情境）並重新查詢 | 新元件 `ClinicCardList`（比照 `RestaurantCardList`） |
| date/time | 選日期與時段 | `ReservationDatePicker` / `TimeSlotSelector` |
| contact | 聯絡人姓名/電話（比照訂位流程帶入上次用過的資料） | `ReservationContactForm` |
| summary | 確認掛號內容 → 送出 | 新元件 `ClinicSummaryCard`（比照 `ReservationSummaryCard`） |
| cross-sell | 掛號成功後顯示加購推薦商品，可選「加購一份」→ 呼叫 `quick_purchase.py` 既有的單品下單機制建立訂單 | 沿用 `quick_purchase` 既有下單邏輯，前端新排版 |
| family-share | 顯示自動組好的通知文字（「爸爸今天有點咳嗽，已預約下午3點去{診所}看診，請不用擔心」），掛上既有 `ShareWithFamilyButton` | **完全重用既有元件，不新增分享機制** |

### 邊界與不做的事
- 不做真的對外發送（LINE/簡訊）——分享對象與時機由使用者當下用原生分享選單決定，比照情境一「家人分享」功能的既有決策。
- 不新增家人聯絡人資料模型。
- 掛號一律視為「立即確認成功」，不模擬診所端婉拒/滿診（跟餐廳訂位的高風險/需人工確認分支不同，掛號情境本次不需要那層複雜度）。
- 診所地區篩選用地址文字比對，不逆向工程 NHI 資料集的 `GOVAREANO` 欄位編碼規則。

---

## 功能二：首頁天氣卡片 + 語音朗讀

### 設計
- 新增 `backend/app/services/weather.py`：呼叫 Open-Meteo（免金鑰）——先用 Geocoding API 查城市座標，再用 Forecast API 查目前氣溫＋今日高低溫＋天氣代碼，5 秒逾時。失敗時回退到模組內建的固定假資料（依城市名對照一份小表，查不到城市名就用通用預設值）。記憶體快取每個城市 10 分鐘。
- 新增 `GET /api/weather?city=` 端點。城市預設「台中市」（對應情境角色），卡片上有一個小的「點一下修改」文字輸入可改城市——不做定位權限、不做使用者地址資料模型。
- 前端新增 `WeatherGreetingCard`（放在 `HomePage`），顯示城市／氣溫／天氣狀況，附「🔊 播放語音」按鈕：新增 `useSpeechSynthesis` hook 包裝瀏覽器內建 `window.speechSynthesis`（中文語音），**按了才念、不是自動播放**——維持與現有語音輸入一致的「使用者主動觸發」習慣，避免自動播放的音訊嚇到使用者或違反瀏覽器 autoplay 限制。

### 邊界與不做的事
- 不含防詐警語（依你的指示，防詐相關內容沿用既有 `/scam-check` 頁面，不重複置入天氣卡片文案）。
- 不含「一鍵產生早安圖」的圖片產生與分享功能。

---

## 資料模型變更彙總

| 項目 | 變更 |
|---|---|
| DynamoDB | 無新表、無新 PK/SK 型態；`clinic_appointment` 案件沿用既有 `REQUEST#` 型態與 `contact_privacy.py` 既有加密/遮罩邏輯 |
| `health_catalog.py` | 新增 3–4 筆感冒/喉嚨相關商品 |
| `health_recommendation.py` | `HEALTH_KEYWORDS` 新增「感冒」「喉嚨」「咳嗽」關鍵字對照；`fallback_recommend()` 被新流程重用，不修改其邏輯 |
| 新 API | `GET /api/weather`、`GET /api/clinics`、`POST /api/symptom-triage`、`POST /api/clinic-appointments`、`GET /api/clinic-appointments/{id}`、`POST /api/clinic-appointments/{id}/cross-sell` |
| `catalog.py` / `services.ts` / `page_catalog.py` | 新增 `clinic_appointment` 服務登記（比照 `shop_purchase` 的一次性導頁特例） |
| `agent.py` | `_handle_one_shot_service` 新增一行與 `shop_purchase` 同構的特例；不改動狀態機其餘邏輯 |
