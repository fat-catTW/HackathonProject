"""應用程式設定。

Milestone 1 預設 USE_MOCK=true：不需任何 AWS 資源即可完整 Demo。
之後切到 Bedrock / AgentCore 時，把 .env 的 USE_MOCK 設成 false 並填入 ARN。
"""
import os
from functools import lru_cache

from dataclasses import dataclass, field


@dataclass
class Settings:
    app_name: str = "AI 智慧生活服務管家"
    use_mock: bool = os.getenv("USE_MOCK", "true").lower() == "true"

    aws_region: str = os.getenv("AWS_REGION", "ap-northeast-1")
    cognito_user_pool_id: str = os.getenv("COGNITO_USER_POOL_ID", "")
    cognito_client_id: str = os.getenv("COGNITO_CLIENT_ID", "")
    agentcore_runtime_arn: str = os.getenv("AGENTCORE_RUNTIME_ARN", "")
    agentcore_memory_id: str = os.getenv("AGENTCORE_MEMORY_ID", "")
    agentcore_gateway_url: str = os.getenv("AGENTCORE_GATEWAY_URL", "")
    bedrock_model_id: str = os.getenv(
        "BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0"
    )
    dynamodb_table_name: str = os.getenv("DYNAMODB_TABLE_NAME", "ServiceAssistant")

    # Mock 模式下的示範帳號（正式環境改用 Cognito JWT）
    demo_users: dict = field(default_factory=lambda: {
        "demo-token-vincent": {"sub": "user-vincent", "name": "Vincent"},
        "demo-token-mei": {"sub": "user-mei", "name": "美惠"},
    })


@lru_cache
def get_settings() -> Settings:
    return Settings()
