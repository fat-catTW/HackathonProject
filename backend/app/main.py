"""FastAPI application entrypoint."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .agent import llm
from .api import (
    auth,
    chat,
    delivery,
    health,
    onboarding,
    requests,
    reservations,
    services,
    sessions,
    shop,
    vendor,
    vendor_delivery,
    vendor_shop,
)
from .config import get_settings
from .services.aws import has_aws_credentials
from .services.conversation_memory import MEMORY
from .services.store import STORE

app = FastAPI(title=get_settings().app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(sessions.router)
app.include_router(chat.router)
app.include_router(services.router)
app.include_router(requests.router)
app.include_router(reservations.router)
app.include_router(delivery.router)
app.include_router(shop.router)
app.include_router(health.router)
app.include_router(vendor.router)
app.include_router(vendor_delivery.router)
app.include_router(vendor_shop.router)
app.include_router(onboarding.router)


@app.get("/health")
def health():
    settings = get_settings()
    return {
        "status": "ok",
        "mock": settings.use_mock,
        "allow_demo_auth": settings.allow_demo_auth,
        "conversation_memory_backend": MEMORY.backend_name,
        "agentcore_memory_id": settings.agentcore_memory_id,
        "store_backend": STORE.backend_name,
        "tool_mode": settings.agent_tool_mode,
        "aws_credentials_detected": has_aws_credentials(),
        "bedrock_ready": llm.is_available(),
        "bedrock_model_id": settings.bedrock_model_id,
        "dynamodb_table_name": settings.dynamodb_table_name,
        "agentcore_gateway_url": settings.agentcore_gateway_url,
        "mcp_tooling_enabled": settings.mcp_tooling_enabled,
    }
