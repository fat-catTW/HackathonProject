# MCP Gateway Lambda Setup

This project exposes five MCP tool handlers through AWS Lambda:

- `list_services`
- `get_service_schema`
- `submit_service_request`
- `get_page_context`
- `search_pages`

## 1. Build Lambda zip files

From the project root:

```powershell
cd E:\黑客松\production\HackathonProject
backend\.venv\Scripts\python.exe lambda_tools\package_lambda_tools.py
```

This creates:

- `lambda_tools/dist/list_services.zip`
- `lambda_tools/dist/get_service_schema.zip`
- `lambda_tools/dist/submit_service_request.zip`
- `lambda_tools/dist/get_page_context.zip`
- `lambda_tools/dist/search_pages.zip`

## 2. Create the Lambda functions

In AWS Lambda Console, create five Python 3.12 functions in `ap-northeast-1`:

- `list_services`
- `get_service_schema`
- `submit_service_request`
- `get_page_context`
- `search_pages`

Upload the matching zip file to each function.

Recommended environment variables for each Lambda:

- `DYNAMODB_TABLE_NAME=ServiceAssistant`
- `SERVICE_CATALOG_FALLBACK=true`

`SERVICE_CATALOG_FALLBACK=true` means the tool still works even when DynamoDB does not yet contain the `SERVICE#...` catalog items.

## 3. Create the AgentCore Gateway

Create a Gateway with:

- Protocol: `MCP`
- Authorizer: `NONE` for the fastest first end-to-end test

After the Gateway is created, add three Lambda targets:

1. Target name: `svc_list`
   Lambda: `list_services`
   Tool schema: `lambda_tools/tool_schemas/list_services.json`

2. Target name: `svc_schema`
   Lambda: `get_service_schema`
   Tool schema: `lambda_tools/tool_schemas/get_service_schema.json`

3. Target name: `svc_submit`
   Lambda: `submit_service_request`
   Tool schema: `lambda_tools/tool_schemas/submit_service_request.json`

4. Target name: `page_ctx`
   Lambda: `get_page_context`
   Tool schema: `lambda_tools/tool_schemas/get_page_context.json`

5. Target name: `page_search`
   Lambda: `search_pages`
   Tool schema: `lambda_tools/tool_schemas/search_pages.json`

Use outbound auth:

- `GATEWAY_IAM_ROLE`

## 4. Copy the Gateway URL into `.env`

Example:

```env
AGENT_TOOL_MODE=mcp
AGENTCORE_GATEWAY_URL=https://<gateway-id>.gateway.bedrock-agentcore.ap-northeast-1.amazonaws.com
MCP_LIST_SERVICES_TOOL_NAME=svc_list___list_services
MCP_GET_SERVICE_SCHEMA_TOOL_NAME=svc_schema___get_service_schema
MCP_SUBMIT_SERVICE_REQUEST_TOOL_NAME=svc_submit___submit_service_request
MCP_GET_PAGE_CONTEXT_TOOL_NAME=page_ctx___get_page_context
MCP_SEARCH_PAGES_TOOL_NAME=page_search___search_pages
```

Tool names are prefixed by the target name in AgentCore Gateway:

- `${target_name}___${tool_name}`

Reference:

- https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-tool-naming.html
