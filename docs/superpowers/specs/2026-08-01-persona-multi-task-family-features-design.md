# 設計文件：多任務統籌與家人協作功能

日期：2026-08-01
動機：以「台中添財阿伯」高齡使用者情境（掃墓週末一次委託三件事：買供品、訂餐廳、約居家清潔）為驅動，替現有 AI 生活服務管家新增「一句話辦多件事」與「完成後可以一鍵分享給家人」的能力，並補上詐騙訊息辨識、台語腔國語理解等呼應該情境痛點的小功能。

## 範圍與優先順序

因時間有限（今天內要完成），依 demo 效益與風險排序，由上而下實作：

1. **多任務統籌**（核心，情境一的主體）
2. **家人分享（Web Share API）** + **行事曆彙總**
3. **詐騙訊息辨識**
4. **台語腔國語提示詞強化**（純提示詞調整）

不在今天範圍內、僅記錄為未來里程碑：**Nova Sonic 台語語音辨識**（即時雙向語音串流，整合風險與工作量都遠高於今天可用時間）。

---

## 功能一：多任務統籌

### 現況與落差
`backend/app/agent/agent.py` 的狀態機一次只能處理一個 `service_id`；`state["service_id"]` 是單一值，`handle_message` 沒有「多個服務排隊」的概念。使用者一句話裡講了三件事時，目前只會抓到其中一個服務意圖。

### 設計

**1. 新的 Bedrock 判斷模式**
在 `backend/app/agent/llm.py` 的 `_TURN_SYSTEM` 提示詞中，於現有 `chat/service_request/page_help/memory_query/unknown` 之外新增 `multi_task` 模式。新增函式 `plan_multi_task(message, services, ...)`，回傳：
```json
{"tasks": [{"service_id": "quick_purchase", "hint_fields": {"query": "拜拜用的三牲跟水果"}},
           {"service_id": "restaurant_reservation", "hint_fields": {"reserved_date": "2026-08-02"}},
           {"service_id": "home_cleaning", "hint_fields": {}}]}
```
判斷依據：訊息中出現兩個以上可對應到不同 `service_id` 的獨立需求時觸發，單一需求仍走原本的 `service_request` 模式，不影響既有單一服務流程的行為。

**2. 新的狀態結構**
`agent.py` 新增 `MultiTaskState`（不取代 `new_state()`，而是包一層）：
```python
{
    "is_multi_task": True,
    "pending_tasks": [...],      # 尚未選擇/尚未開始的任務卡
    "active_task_state": {...},  # 進行中任務，形狀等同 new_state()
    "completed_tasks": [...],    # 已完成任務的摘要，供最終彙總與分享文字使用
}
```
`handle_message` 入口處：當 `turn_plan["mode"] == "multi_task"` 時建立此狀態並回傳任務卡，不進入欄位收集。

**3. 任務卡確認與篩選**
`ChatResponse`（`backend/app/models/chat.py`）新增欄位 `task_cards: list[dict] | None`，前端收到後渲染成多張卡片（沿用 DESIGN.md 既有卡片樣式：`rounded-2xl`、白底、`shadow-sm`）。使用者回覆「先做前兩個」時，用既有的 `_judge_reply`-style 判斷（比對任務清單 + 一次 Bedrock 分類呼叫）決定要保留/排序哪些任務。

**4. 逐一執行**
`pending_tasks` 佇列的第一項變成 `active_task_state`，直接重用現有的 `_continue_collection` / `_submit` 等函式（沒有 diff——這些函式操作的是 `state["service_id"]`／`state["collected_fields"]`，只要把 `active_task_state` 傳進去即可）。一個任務 `_submit` 成功後：
- 該任務摘要進 `completed_tasks`
- 取下一個 `pending_tasks` 項目成為新的 `active_task_state`
- 回覆前綴一句銜接語（沿用既有 `_prepend_reply` 機制）
- 若 `pending_tasks` 空了，整個 `MultiTaskState` 結束，回傳所有 `completed_tasks` 的彙總文字（給功能二使用）

**5. 新的「隨手買」一次性下單模式**
新增 `quick_purchase` service_id 與 `backend/app/services/quick_purchase_catalog.py`：一份精選組合清單（例如「清明祭祖水果盆」599 元、「三牲祭祀組合」等），比照 `health_product_recommendation` 的問答式（非表單）處理——Bedrock 依關鍵字挑一個組合，直接呼叫 `shop.create_shop_order` 送出單品項購物車，不經過商城瀏覽/購物車 UI。

### 邊界與不做的事
- 任務之間沒有「互相依賴」邏輯（例如不會因為餐廳訂位失敗就連動取消打掃）——各任務獨立送出、獨立成功/失敗，失敗的任務會在彙總裡標示待重試，不阻塞其他任務。
- 不支援同時並行問多個任務的欄位；嚴格維持一次一問。

---

## 功能二：家人分享（取代原本設想的 LINE Messaging API 主動推播）

### 為何不用 LINE Messaging API 主動推播
真正的伺服器端主動推播需要：申請 LINE 官方帳號（免費但要設定）＋ 一個對外可連線的 webhook 端點來取得對方 `userId`＋ 家人必須先加官方帳號好友並主動傳一次訊息。這一整套流程在今天的時間內完成並確保能穩定 demo，風險過高，故不採用。LINE Notify 服務也已於 2025 年 3 月被官方關閉，並非可用選項。

### 設計：Web Share API + 剪貼簿備援
純前端功能，不需要任何第三方 API 金鑰、不需要後端新服務：

- 多任務彙總完成（或單一服務送出成功）畫面上新增「分享給家人」按鈕
- 點擊時：若瀏覽器支援 `navigator.share`，呼叫 `navigator.share({ title, text })`，喚出裝置原生分享選單（使用者可直接選 LINE、簡訊或任何已安裝的 App）
- 若不支援（少數桌面瀏覽器），退回 `navigator.clipboard.writeText(text)` 並顯示提示 Toast「已複製訊息，請貼到 LINE 傳給家人」（沿用既有 `Toast.tsx` 元件）
- 分享文字內容＝功能一產生的彙總摘要（或單一服務的完成摘要）

前端新增元件 `ShareWithFamilyButton.tsx`，放在多任務完成畫面與（可選）單一服務 `submit_success` 之後的畫面。不需要資料庫新增家人帳號資料表——這個設計不需要事先登記家人的聯絡方式，分享對象由使用者當下在系統分享選單中自行決定，更符合「不想造成子女負擔、想要自己搞定」的產品調性，也是最快能在今天做完的版本。

---

## 功能三：行事曆彙總

純讀取端功能：
- 新增 `GET /api/calendar`，重用 `STORE.list_requests(actor_id)`（`backend/app/services/store.py` 已有），依各案件的日期欄位（`preferred_date` / `reserved_date` 等，依 `service_id` 對應不同欄位名）分組
- 前端新增一個依日期分組的清單頁面，沿用既有 `RequestCard` 系列樣式
- 不新增寫入邏輯、不改資料庫結構

---

## 功能四：詐騙訊息辨識

完全獨立、零風險加分項：
- `llm.py` 新增 `_SCAM_CHECK_SYSTEM` 提示詞與 `check_scam_message(text)` 函式，回傳分類（`投資詐騙` / `假冒親友` / `釣魚連結` / `正常訊息`）與白話風險說明
- `agent.py` 的 `_TURN_SYSTEM` 新增對應的觸發判斷（使用者貼上/描述可疑訊息並詢問是否為詐騙時觸發），或另開一個獨立端點 `POST /api/scam-check`（今天優先做獨立端點，风险更低、不影響既有對話流程）
- 不需要資料庫變更

---

## 功能五：台語腔國語提示詞強化

純提示詞調整，不改架構：
- `llm.py` 的 `_FIELD_SYSTEM`、`_SERVICE_SYSTEM`、`_TURN_SYSTEM` 加入台語腔國語常見講法的 few-shot 範例（如「三牲」「透天厝」「逗陣」「愛」（要）等詞彙與語序），讓既有的 Web Speech API 語音轉文字結果即使帶有台語腔國語特徵，也能被正確判斷意圖與欄位
- 不涉及真正的台語 ASR（聽懂純台語語音），該項列入下方未來規劃

---

## 未來規劃（今天不做）

**Nova Sonic 台語語音辨識**：以 Amazon Bedrock 的 Nova Sonic 語音理解模型取代前端 Web Speech API，直接處理雙向音訊串流以支援純台語語音輸入。需要：前端音訊擷取與串流上傳改造、後端串流轉發至 Bedrock、逐字稿即時回饋 UI。工作量與整合風險遠高於今天可用時間，留待下一個里程碑（可對應 README 既有的「M2 Bedrock」之後的延伸里程碑）。

---

## 資料模型變更彙總

| 項目 | 變更 |
|---|---|
| DynamoDB | 無新表、無新 PK/SK 型態（功能二改為純前端方案後不再需要 `FAMILY_MEMBER#` 項目） |
| `ChatResponse` | 新增 `task_cards: list[dict] \| None` |
| 新 API | `GET /api/calendar`、`POST /api/scam-check` |
