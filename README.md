# AI 智慧生活服務管家（Hackathon MVP）

> 2026 雲湧智生黑客松（統一資訊命題：AI 生活管家）
> 使用者只需說出需求，AI 即協助判斷服務、補齊表單並建立服務案件。

目前為 **Milestone 1：本地 Mock 流程** — 不需任何 AWS 資源即可完整跑 Demo。
Agent 決策流程、Tool 介面（list_services / get_service_schema / submit_service_request）、
DynamoDB 單表 Key 設計皆與系統設計書一致，之後逐里程碑替換為
Bedrock、AgentCore Memory/Gateway、Lambda、DynamoDB、Cognito。

## 快速開始

### 後端（Python 3.12）
```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload        # http://localhost:8000（/docs 有 Swagger）
```

### 前端（Node 18+）
```bash
cd frontend
npm install
npm run dev                          # http://localhost:5173
```

登入頁提供兩個示範帳號（Vincent／美惠），用於展示多使用者資料隔離。
語音輸入使用 Web Speech API（Chrome/Edge 支援最佳），不支援時自動退回文字輸入。

## 目前完成（Milestone 1）
- 規則式中文 NLU：服務判斷、數量（含中文數字）、相對日期（明天／下週三／8月1日）、
  時段、電話、地址（使用命題「縣市區域檔」22 縣市＋200 行政區資料驗證）
- Agent 狀態機（設計書 §14）：一次一問、不重複詢問、送出前必經確認摘要、
  Tool 失敗不偽造案件編號
- 長期記憶偏好：沿用上次地址／電話／偏好時段（需使用者同意才套用）
- 案件 CRUD、狀態流轉（含 Demo 模擬廠商確認／完工）
- 多使用者資料隔離（PK=USER#actorId）

## 廠商後台（Milestone 3／4／15）
`/vendor/login` 登入後於 `/vendor/requests` 查看自家 `service_vendor_id` 的諮詢單與訂單
（待確認／已接訂單／全部三個分頁），開啟案件明細可看表單內容與聯絡資訊，並直接接單或婉拒。

- **接單／拒單**：`POST /api/vendor/requests/{id}/accept|reject`，body 帶 `version`。
  - 狀態機定義在 `app/services/statuses.py` 的 `VENDOR_TRANSITIONS`：只有待處理中的
    案件（`VENDOR_PENDING_STATUSES`，即 `SUBMITTED`／`PENDING_PROVIDER`／
    `AWAITING_QUOTE`）能接單（→ `CONFIRMED`）或婉拒（→ `REJECTED`），住戶已取消或
    同事先接走的單會被擋下並回 409 `REQUEST_STATUS_CONFLICT`。
  - 樂觀鎖：案件帶 `version`，每次寫入加一；寫入時以 DynamoDB
    `ConditionExpression` 比對版本，對不上回 409 `REQUEST_VERSION_CONFLICT`，
    連點兩下或兩個分頁同時操作只會有一次生效。兩種 409 都會把案件現況一併回傳，
    前端直接更新畫面不必重新整理。
- 案件在 `save_request` 時同步鏡射一份 `PK=VENDOR#{id}` 的索引項目，單表不必加 GSI；
  索引是盡力而為的鏡射，狀態與版本一律以 `PK=USER#{actor}` 的案件本體為準。
- 廠商帳號由部署端佈建（`VENDOR_ACCOUNTS`），**不開放自助註冊**：vendor_id 決定
  看得到哪些案件，若讓使用者自行宣告等同能讀取任一廠商的訂單。
- 內建示範帳號：`vendor1@demo.local`（潔家家事服務，vendor 1）、
  `vendor11@demo.local`（安心水電工程行，vendor 11），密碼皆為 `vendor1234`。
- 住戶 token 打廠商 API 回 403，廠商 token 打住戶 API 也回 403，兩邊登入狀態分開存放。

### 聯絡資訊：加密保存、解密留痕（Milestone 15）
住戶填的姓名／電話／地址（`app/services/contact_privacy.py` 的 `CONTACT_FIELDS`）
在儲存層就是密文，廠商後台平常只看得到遮罩值，要看完整內容得另外解鎖，而且每次
解鎖都會留紀錄。

- **寫入即加密**：`save_request` 是所有案件寫入的唯一出口，聯絡欄位在這裡換成
  `enc:` 開頭的密文，同時算好遮罩值存進 `form_data_masked`；`VENDOR#` 索引鏡射的
  也是密文。金鑰預設由 `CONTACT_ENCRYPTION_KEY` 導出（本地 AES-GCM），設定
  `CONTACT_KMS_KEY_ID` 則改用 KMS；兩種密文前綴不同，換金鑰來源不會讓舊資料變亂碼。
  兩者都沒設時退回內建開發金鑰，僅供本機 Demo。
- **平常只給遮罩**：清單摘要與明細一律走 `form_data_masked`，例如
  `0912***678`、`台北市信義區…`、`王○明`。遮罩夠廠商判斷服務範圍與辨識客戶，
  但撥不出電話、找不到門牌。這條路徑不解密，因此不會產生存取紀錄。
- **解密要留痕**：`POST /api/vendor/requests/{id}/contact` 才回傳完整內容，並在
  `PK=REQUEST#{id}, SK=ACCESS#{時間}` 寫一筆 `CONTACT_ACCESS_LOG`（誰、什麼時候、
  看了哪些欄位）。紀錄寫不進去就不解密，回 503 `CONTACT_LOG_UNAVAILABLE`——先吐出
  電話再記錄，記錄失敗時就成了一次查不到的存取。案件明細會把該廠商自己的存取紀錄
  一併帶回；別家廠商的紀錄不外流。
- **住戶端不受影響**：`get_request`／`list_requests` 會自動解密，住戶看自己的案件
  還是明文。解不開的欄位保留密文而非換成錯誤字串，避免下次寫回時把原始資料蓋掉。
- Milestone 15 之前存的明文案件仍會被就地遮罩（顯示層安全），但資料庫裡還是明文；
  跑一次 `python backend/scripts/backfill_encrypt_contacts.py` 補加密（支援
  `--dry-run`，寫回時比對 `version`，期間被改過的案件會略過而不是覆蓋）。

## AI 代操表單（form autopilot）
在服務表單頁打開 AI 管家說「幫我填」，Agent 不只是告訴你欄位在哪，而是**直接把表單填起來**：
逐格捲到該欄位、高亮、寫入值，填過的欄位留下「AI 已填」標記，最後回到使用者確認送出。
不在表單頁時說「幫我填冷氣清洗」，Agent 會先回 `redirect_path` 帶你到那張表單再開始填。

- **後端**：`app/agent/form_autopilot.py` 判斷代填意圖與頁面 ↔ 服務對應；`app/agent/agent.py`
  的 `handle_message` 在對話流程外包一層，把「這一輪 `collected_fields` 的變動」轉成
  `form_actions`（`fill` / `clear`，含欄位標籤、要寫進輸入框的值、給人看的值與資料來源說明）。
  visibleWhen 隱藏中的欄位不會產生動作，畫面上沒有的東西就不會被寫。
- **表單狀態同步**：前端每則訊息都附上 `form_context`（目前畫面上每一格的值，空的送空字串），
  Agent 以畫面為準：使用者自己打的字不會被回填覆蓋、清掉的欄位 Agent 也會跟著忘記，
  不會出現「Agent 以為填完了、送出卻缺欄位」。照片（data URL）不送、過長的值截斷。
- **偏好自動帶入**：只有明講「幫我填」時才會直接沿用長期記憶裡的地址／電話／慣用時段，
  並在該欄位下標註「沿用你上次填的資料」；沒明講就維持原本一次問一格的流程。
- **填不進去就不會說有填**：下拉沒有的選項、`visibleWhen` 隱藏中的欄位、拆不出行政區的地址，
  前端一律拒填並回報，畫面不會標「AI 已填」，狀態列也會告訴使用者哪幾格要自己選。
- **前端**：`hooks/useFormAgent.tsx` 是動作佇列（掛在路由外層，撐得過導頁與面板關閉），
  `pages/ServiceFormPage.tsx` 把自己註冊給它；地址欄會用 `utils/twAddress.ts` 把一整串地址
  拆回「縣市／鄉鎮市區／詳細地址」三個控制項。下拉選單對不上選項時寧可不填，不會把表單
  寫成不合法的狀態。
- 代填期間 AI 管家面板會自動收起來（不然整張表單被蓋住），改用畫面上方的狀態列顯示進度，
  隨時可以按「停止」喊停；使用者若開啟系統的「減少動態效果」，逐格捲動會改成不帶動畫。
- **安全與邊界**：包裹寄送的違禁品確認一樣要先問過才會填（代填、畫面同步兩條路都擋）；
  離開表單頁後代操自動結束；改口說「我要預約居家清潔」會帶你到那張表單，而不是硬塞進眼前這張。
- **哪些服務可以代填**：水電修繕、洗衣機清洗、冷氣清洗、居家清潔、包裹寄送（走通用表單頁）。
  餐廳訂位、美食外送、商城購物、健康商品推薦在前端是專屬流程頁（挑店家、購物車…），
  沒有可以逐格代填的欄位，說「幫我填美食外送」時管家會把你帶到那一頁再用對話接手
  （見 `form_autopilot.DEDICATED_FLOW_SERVICES`）。
- **「幫我填」不會走進死路**：聽不出是哪一種服務就直接回問你要哪一種；用語音講完整句需求
  （「我用說的，幫我填兩台壁掛式冷氣…」）也會真的代填，只有「可以用語音幫我填嗎」這種
  詢問功能的問句才回頁面說明。
- **日期以使用者當下的日期換算**：每則訊息附上前端的本地日期，「這禮拜三」不會被伺服器時區
  或模型推算的星期幾帶偏（見 `services/clock.py`）。

## 專案結構
```
backend/         FastAPI + Agent 狀態機 + Mock 儲存層（DynamoDB 單表介面）
lambda_tools/    Milestone 4 可部署的 Lambda Tool（boto3 版）＋ MCP tool schema
frontend/        React + TS + Vite + Tailwind（高齡友善大字級 UI）
docs/            demo-script.md
infrastructure/  CDK（待 Milestone 4+）
```

## 切換至 AWS（後續里程碑）
| 里程碑 | 替換點 |
|---|---|
| M2 Bedrock | `app/agent/agent.py` 的 NLU 換成 Bedrock Converse＋`app/agent/prompt.py` |
| M3 Memory | `MemoryStore` 的 session events／preferences 改寫入 AgentCore Memory |
| M4 Gateway | `app/agent/tools.py` 的 `call()` 改走 AgentCore Gateway（MCP），部署 `lambda_tools/` |
| M5 DynamoDB | `MemoryStore` 換成 boto3 DynamoDB（Key 設計不變） |
| M6 Cognito | `.env` 設 `USE_MOCK=false`，`app/auth/cognito.py` 自動啟用 JWT 驗證；廠商身分改由 Cognito 群組 `vendor:{id}` 帶出，`app/auth/vendors.py` 即可移除 |
