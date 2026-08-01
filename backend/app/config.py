"""Application settings."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parent.parent

try:
    from dotenv import find_dotenv, load_dotenv
except ImportError:  # pragma: no cover - optional during bootstrap
    find_dotenv = load_dotenv = None

if find_dotenv and load_dotenv:
    load_dotenv(find_dotenv(filename=".env", usecwd=True), override=False)


def _env_flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


# 內建的示範廠商帳號，對應 services/catalog.py 的 service_vendor_id。
_BUILTIN_VENDOR_ACCOUNTS: dict = {
    "vendor1@demo.local": {
        "vendor_id": 1,
        "name": "潔家家事服務",
        "password": "vendor1234",
    },
    "vendor11@demo.local": {
        "vendor_id": 11,
        "name": "安心水電工程行",
        "password": "vendor1234",
    },
    "vendor2@demo.local": {
        "vendor_id": 2,
        "name": "統一速達（黑貓宅急便）",
        "password": "vendor1234",
    },
    "vendor22@demo.local": {
        "vendor_id": 22,
        "name": "22世紀風味館",
        "password": "vendor1234",
    },
    "vendor30@demo.local": {
        "vendor_id": 30,
        "name": "美食外送物流中心",
        "password": "vendor1234",
    },
    "vendor40@demo.local": {
        "vendor_id": 40,
        "name": "商城出貨中心",
        "password": "vendor1234",
    },
}


def _load_vendor_accounts() -> dict:
    """廠商帳號一律由部署端佈建，不開放自助註冊。

    vendor_id 決定看得到哪些案件，若讓使用者註冊時自行宣告，等同任意讀取其他
    廠商的訂單。設定 VENDOR_ACCOUNTS（JSON: {email: {vendor_id, name, password}}）
    即覆蓋內建示範帳號；正式版改由 Cognito 群組 vendor:{id} 帶出。
    """
    raw = os.getenv("VENDOR_ACCOUNTS", "").strip()
    if not raw:
        return {
            email: {**account, "builtin_demo": True}
            for email, account in _BUILTIN_VENDOR_ACCOUNTS.items()
        }
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    accounts: dict = {}
    for email, account in (parsed or {}).items():
        if not isinstance(account, dict) or account.get("vendor_id") is None:
            continue
        accounts[email.strip().lower()] = {
            "vendor_id": int(account["vendor_id"]),
            "name": account.get("name") or email,
            "password": account.get("password", ""),
            "builtin_demo": False,
        }
    return accounts


@dataclass
class Settings:
    app_name: str = "AI Smart Life Service Assistant"
    use_mock: bool = _env_flag("USE_MOCK", True)

    aws_region: str = os.getenv("AWS_REGION", "ap-northeast-1")
    aws_access_key_id: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    aws_secret_access_key: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    aws_session_token: str = os.getenv("AWS_SESSION_TOKEN", "")
    aws_profile: str = os.getenv("AWS_PROFILE", "")

    cognito_user_pool_id: str = os.getenv("COGNITO_USER_POOL_ID", "")
    cognito_client_id: str = os.getenv("COGNITO_CLIENT_ID", "")

    # 聯絡資訊欄位級加密（Milestone 15）。兩者皆未設定時退回內建開發金鑰，
    # 詳見 services/contact_privacy.py。
    contact_encryption_key: str = os.getenv("CONTACT_ENCRYPTION_KEY", "")
    contact_kms_key_id: str = os.getenv("CONTACT_KMS_KEY_ID", "")

    bedrock_model_id: str = os.getenv(
        "BEDROCK_MODEL_ID",
        "apac.amazon.nova-pro-v1:0",
    )
    dynamodb_table_name: str = os.getenv("DYNAMODB_TABLE_NAME", "ServiceAssistant")
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    mock_store_path: Path = _BACKEND_ROOT / os.getenv("MOCK_STORE_PATH", ".local-store.json")
    user_store_path: Path = _BACKEND_ROOT / os.getenv("USER_STORE_PATH", ".local-users.json")
    allow_demo_auth: bool = _env_flag("ALLOW_DEMO_AUTH", True)
    agent_tool_mode: str = os.getenv("AGENT_TOOL_MODE", "embedded").strip().lower()
    list_services_lambda_name: str = os.getenv("LIST_SERVICES_LAMBDA_NAME", "")
    get_service_schema_lambda_name: str = os.getenv("GET_SERVICE_SCHEMA_LAMBDA_NAME", "")
    submit_service_request_lambda_name: str = os.getenv("SUBMIT_SERVICE_REQUEST_LAMBDA_NAME", "")
    get_page_context_lambda_name: str = os.getenv("GET_PAGE_CONTEXT_LAMBDA_NAME", "")
    search_pages_lambda_name: str = os.getenv("SEARCH_PAGES_LAMBDA_NAME", "")
    recommend_products_by_health_need_lambda_name: str = os.getenv(
        "RECOMMEND_PRODUCTS_BY_HEALTH_NEED_LAMBDA_NAME", ""
    )
    get_product_nutrition_lambda_name: str = os.getenv("GET_PRODUCT_NUTRITION_LAMBDA_NAME", "")
    list_shop_stores_lambda_name: str = os.getenv("LIST_SHOP_STORES_LAMBDA_NAME", "")
    get_shop_products_lambda_name: str = os.getenv("GET_SHOP_PRODUCTS_LAMBDA_NAME", "")
    get_user_points_lambda_name: str = os.getenv("GET_USER_POINTS_LAMBDA_NAME", "")

    # AgentCore integration.
    agentcore_runtime_arn: str = os.getenv("AGENTCORE_RUNTIME_ARN", "")
    agentcore_memory_id: str = os.getenv("AGENTCORE_MEMORY_ID", "")
    agentcore_gateway_url: str = os.getenv("AGENTCORE_GATEWAY_URL", "")
    agentcore_gateway_mcp_path: str = os.getenv("AGENTCORE_GATEWAY_MCP_PATH", "/mcp")
    agentcore_gateway_auth_scheme: str = os.getenv("AGENTCORE_GATEWAY_AUTH_SCHEME", "Bearer")
    agentcore_gateway_auth_token: str = os.getenv("AGENTCORE_GATEWAY_AUTH_TOKEN", "")
    mcp_list_services_tool_name: str = os.getenv("MCP_LIST_SERVICES_TOOL_NAME", "list_services")
    mcp_get_service_schema_tool_name: str = os.getenv("MCP_GET_SERVICE_SCHEMA_TOOL_NAME", "get_service_schema")
    mcp_submit_service_request_tool_name: str = os.getenv("MCP_SUBMIT_SERVICE_REQUEST_TOOL_NAME", "submit_service_request")
    mcp_get_page_context_tool_name: str = os.getenv("MCP_GET_PAGE_CONTEXT_TOOL_NAME", "get_page_context")
    mcp_search_pages_tool_name: str = os.getenv("MCP_SEARCH_PAGES_TOOL_NAME", "search_pages")
    mcp_recommend_products_by_health_need_tool_name: str = os.getenv(
        "MCP_RECOMMEND_PRODUCTS_BY_HEALTH_NEED_TOOL_NAME", "recommend_products_by_health_need"
    )
    mcp_get_product_nutrition_tool_name: str = os.getenv(
        "MCP_GET_PRODUCT_NUTRITION_TOOL_NAME", "get_product_nutrition"
    )
    mcp_list_shop_stores_tool_name: str = os.getenv("MCP_LIST_SHOP_STORES_TOOL_NAME", "list_shop_stores")
    mcp_get_shop_products_tool_name: str = os.getenv("MCP_GET_SHOP_PRODUCTS_TOOL_NAME", "get_shop_products")
    mcp_get_user_points_tool_name: str = os.getenv("MCP_GET_USER_POINTS_TOOL_NAME", "get_user_points")

    demo_users: dict = field(
        default_factory=lambda: {
            "demo-token-vincent": {"sub": "user-vincent", "name": "Vincent"},
            "demo-token-mei": {"sub": "user-mei", "name": "Mei"},
        }
    )

    # 廠商後台帳號（Milestone 3），email → {vendor_id, name, password, builtin_demo}
    vendor_accounts: dict = field(default_factory=_load_vendor_accounts)

    @property
    def has_explicit_aws_credentials(self) -> bool:
        return bool(self.aws_access_key_id and self.aws_secret_access_key)

    @property
    def lambda_tooling_enabled(self) -> bool:
        return all(
            (
                self.list_services_lambda_name,
                self.get_service_schema_lambda_name,
                self.submit_service_request_lambda_name,
            )
        )

    @property
    def use_agentcore_memory(self) -> bool:
        return bool(not self.use_mock and self.agentcore_memory_id)

    @property
    def mcp_tooling_enabled(self) -> bool:
        return bool(self.agentcore_gateway_url)


@lru_cache
def get_settings() -> Settings:
    return Settings()
