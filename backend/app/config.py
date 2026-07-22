"""Application settings."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache

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

    bedrock_model_id: str = os.getenv(
        "BEDROCK_MODEL_ID",
        "apac.amazon.nova-pro-v1:0",
    )
    dynamodb_table_name: str = os.getenv("DYNAMODB_TABLE_NAME", "ServiceAssistant")
    allow_demo_auth: bool = _env_flag("ALLOW_DEMO_AUTH", True)
    agent_tool_mode: str = os.getenv("AGENT_TOOL_MODE", "embedded").strip().lower()
    list_services_lambda_name: str = os.getenv("LIST_SERVICES_LAMBDA_NAME", "")
    get_service_schema_lambda_name: str = os.getenv("GET_SERVICE_SCHEMA_LAMBDA_NAME", "")
    submit_service_request_lambda_name: str = os.getenv("SUBMIT_SERVICE_REQUEST_LAMBDA_NAME", "")

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

    demo_users: dict = field(
        default_factory=lambda: {
            "demo-token-vincent": {"sub": "user-vincent", "name": "Vincent"},
            "demo-token-mei": {"sub": "user-mei", "name": "Mei"},
        }
    )

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
