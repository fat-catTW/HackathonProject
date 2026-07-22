# AWS Agent Setup

## Recommended path

Start with:

- `USE_MOCK=false`
- `AGENT_TOOL_MODE=embedded`
- `ALLOW_DEMO_AUTH=true`

This lets the backend use AWS for persistence while still accepting the existing demo bearer tokens, so you do not need Cognito on day one.

## Quick start

1. Copy `.env.example` to `.env`.
2. Fill in:
   - `USE_MOCK=false`
   - `AWS_REGION`
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`
   - `AWS_SESSION_TOKEN` if you use temporary credentials
   - `BEDROCK_MODEL_ID`
   - `DYNAMODB_TABLE_NAME`
   - `ALLOW_DEMO_AUTH=true`
- `AGENT_TOOL_MODE=embedded`
3. Install backend dependencies:

```bash
cd backend
pip install -r requirements.txt
```

4. Bootstrap the minimum AWS resources:

```bash
python scripts/bootstrap_aws.py
```

5. Start the API:

```bash
uvicorn app.main:app --reload
```

6. Check health:

```bash
curl http://localhost:8000/health
```

Expected fields:

- `store_backend`: `dynamodb` when `USE_MOCK=false`
- `tool_mode`: your selected tool mode
- `aws_credentials_detected`: `true` when credentials are visible to boto3
- `bedrock_ready`: `true` when the Bedrock client can be created

## DynamoDB table shape

For `embedded` mode, the table only needs a composite key:

- Partition key: `PK` (String)
- Sort key: `SK` (String)

Stored items use these patterns:

- `USER#<actor_id>` / `SESSION#<session_id>`
- `USER#<actor_id>` / `REQUEST#<request_id>`
- `USER#<actor_id>` / `PREFERENCES`

If you use `AGENT_TOOL_MODE=dynamodb`, also seed service catalog items like:

- `SERVICE#air_conditioner_cleaning` / `METADATA`

## Lambda mode

If you already deploy the functions under `lambda_tools/`, set:

- `AGENT_TOOL_MODE=lambda`
- `LIST_SERVICES_LAMBDA_NAME`
- `GET_SERVICE_SCHEMA_LAMBDA_NAME`
- `SUBMIT_SERVICE_REQUEST_LAMBDA_NAME`

The backend will invoke Lambda directly with boto3.

## MCP / AgentCore Gateway mode

If you want the agent to call tools through AgentCore Gateway using MCP, set:

- `AGENT_TOOL_MODE=mcp`
- `AGENTCORE_GATEWAY_URL=https://<your-gateway-id>.gateway.bedrock-agentcore.<region>.amazonaws.com`

Optional settings:

- `AGENTCORE_GATEWAY_AUTH_SCHEME=Bearer`
- `AGENTCORE_GATEWAY_AUTH_TOKEN=<token>` if you want the backend to use a fixed token
- `MCP_LIST_SERVICES_TOOL_NAME`
- `MCP_GET_SERVICE_SCHEMA_TOOL_NAME`
- `MCP_SUBMIT_SERVICE_REQUEST_TOOL_NAME`

Notes:

- The backend posts JSON-RPC `tools/call` requests to `${AGENTCORE_GATEWAY_URL}/mcp`.
- If the incoming user already has a bearer token, the backend forwards that token to the gateway first.
- If no incoming token is available for the gateway, the backend falls back to `AGENTCORE_GATEWAY_AUTH_TOKEN`.
- If your gateway exposes tool names with target prefixes, set the three `MCP_*_TOOL_NAME` values to the exact exposed names.
