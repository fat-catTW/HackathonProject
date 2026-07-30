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

## 廠商後台（Milestone 3／4）
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
