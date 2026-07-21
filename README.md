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
- 單元測試 11 項（backend/tests，`pytest backend/tests`）

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
| M6 Cognito | `.env` 設 `USE_MOCK=false`，`app/auth/cognito.py` 自動啟用 JWT 驗證 |
