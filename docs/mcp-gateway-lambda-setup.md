# MCP Gateway Lambda Setup

This project currently exposes 10 MCP tool handlers through AWS Lambda:

- `list_services`
- `get_service_schema`
- `submit_service_request`
- `get_page_context`
- `search_pages`
- `recommend_products_by_health_need`
- `get_product_nutrition`
- `list_shop_stores`
- `get_shop_products`
- `get_user_points`

## 1. Build Lambda zip files

From the project root:

```powershell
backend\.venv\Scripts\python.exe lambda_tools\package_lambda_tools.py
```

This creates:

- `lambda_tools/dist/list_services.zip`
- `lambda_tools/dist/get_service_schema.zip`
- `lambda_tools/dist/submit_service_request.zip`
- `lambda_tools/dist/get_page_context.zip`
- `lambda_tools/dist/search_pages.zip`
- `lambda_tools/dist/recommend_products_by_health_need.zip`
- `lambda_tools/dist/get_product_nutrition.zip`
- `lambda_tools/dist/list_shop_stores.zip`
- `lambda_tools/dist/get_shop_products.zip`
- `lambda_tools/dist/get_user_points.zip`

## 2. Create the Lambda functions

In AWS Lambda Console, create 10 Python 3.12 functions in `ap-northeast-1` with the same names as the tools above, then upload the matching zip file to each function.

Recommended environment variables for each Lambda:

- `DYNAMODB_TABLE_NAME=ServiceAssistant`
- `SERVICE_CATALOG_FALLBACK=true`

`SERVICE_CATALOG_FALLBACK=true` keeps the service-catalog tools working even when DynamoDB does not yet contain the `SERVICE#...` catalog items.

`recommend_products_by_health_need` always uses rule-based keyword matching in this Lambda deployment mode (unlike the embedded/backend mode, which additionally searches Google via Bedrock — see `backend/app/services/health_recommendation.py`).

## 3. Create the AgentCore Gateway

Create a Gateway with:

- Protocol: `MCP`
- Authorizer: `NONE` for the fastest first end-to-end test

Then add one Lambda target per tool. Example target names are shown below; you can rename them, but the exposed tool name will become `${target_name}___${tool_name}`.

1. Target name: `svc-list`
   Lambda: `list_services`
   Tool schema: `lambda_tools/tool_schemas/list_services.json`
2. Target name: `svc-schema`
   Lambda: `get_service_schema`
   Tool schema: `lambda_tools/tool_schemas/get_service_schema.json`
3. Target name: `svc-submit`
   Lambda: `submit_service_request`
   Tool schema: `lambda_tools/tool_schemas/submit_service_request.json`
4. Target name: `page-ctx`
   Lambda: `get_page_context`
   Tool schema: `lambda_tools/tool_schemas/get_page_context.json`
5. Target name: `page-search`
   Lambda: `search_pages`
   Tool schema: `lambda_tools/tool_schemas/search_pages.json`
6. Target name: `health-recommend`
   Lambda: `recommend_products_by_health_need`
   Tool schema: `lambda_tools/tool_schemas/recommend_products_by_health_need.json`
7. Target name: `health-nutrition`
   Lambda: `get_product_nutrition`
   Tool schema: `lambda_tools/tool_schemas/get_product_nutrition.json`
8. Target name: `shop-stores`
   Lambda: `list_shop_stores`
   Tool schema: `lambda_tools/tool_schemas/list_shop_stores.json`
9. Target name: `shop-products`
   Lambda: `get_shop_products`
   Tool schema: `lambda_tools/tool_schemas/get_shop_products.json`
10. Target name: `user-points`
    Lambda: `get_user_points`
    Tool schema: `lambda_tools/tool_schemas/get_user_points.json`

Use outbound auth:

- `GATEWAY_IAM_ROLE`

## 4. Copy the Gateway URL into `.env`

Example:

```env
AGENT_TOOL_MODE=mcp
AGENTCORE_GATEWAY_URL=https://<gateway-id>.gateway.bedrock-agentcore.ap-northeast-1.amazonaws.com
MCP_LIST_SERVICES_TOOL_NAME=svc-list___list_services
MCP_GET_SERVICE_SCHEMA_TOOL_NAME=svc-schema___get_service_schema
MCP_SUBMIT_SERVICE_REQUEST_TOOL_NAME=svc-submit___submit_service_request
MCP_GET_PAGE_CONTEXT_TOOL_NAME=page-ctx___get_page_context
MCP_SEARCH_PAGES_TOOL_NAME=page-search___search_pages
MCP_RECOMMEND_PRODUCTS_BY_HEALTH_NEED_TOOL_NAME=health-recommend___recommend_products_by_health_need
MCP_GET_PRODUCT_NUTRITION_TOOL_NAME=health-nutrition___get_product_nutrition
MCP_LIST_SHOP_STORES_TOOL_NAME=shop-stores___list_shop_stores
MCP_GET_SHOP_PRODUCTS_TOOL_NAME=shop-products___get_shop_products
MCP_GET_USER_POINTS_TOOL_NAME=user-points___get_user_points
```

If your Gateway uses different target names, update the `.env` values to the exact exposed names from AgentCore Gateway.

Reference:

- https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-tool-naming.html
