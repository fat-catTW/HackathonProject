"""FastAPI application entrypoint."""
from fastapi import FastAPI
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from botocore.exceptions import ClientError

from .agent import llm
from .api import (
    auth,
    calendar,
    chat,
    clinics,
    delivery,
    health,
    onboarding,
    requests,
    reservations,
    services,
    sessions,
    shop,
    speech,
    vendor,
    vendor_delivery,
    vendor_shop,
    weather,
)
from .config import get_settings
from .services.aws import has_aws_credentials
from .services.conversation_memory import MEMORY
from .services.store import STORE

app = FastAPI(title=get_settings().app_name)


@app.exception_handler(ClientError)
async def aws_client_error_handler(_request: Request, exc: ClientError):
    error = exc.response.get("Error", {})
    if error.get("Code") == "ExpiredTokenException":
        return JSONResponse(
            status_code=503,
            content={
                "success": False,
                "error": {
                    "code": "AWS_TOKEN_EXPIRED",
                    "message": "AWS credentials have expired. Refresh AWS credentials or switch USE_MOCK=true.",
                },
            },
        )
    return JSONResponse(
        status_code=503,
        content={
            "success": False,
            "error": {
                "code": error.get("Code") or "AWS_CLIENT_ERROR",
                "message": error.get("Message") or str(exc),
            },
        },
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(calendar.router)
app.include_router(sessions.router)
app.include_router(chat.router)
app.include_router(services.router)
app.include_router(requests.router)
app.include_router(reservations.router)
app.include_router(clinics.router)
app.include_router(delivery.router)
app.include_router(shop.router)
app.include_router(speech.router)
app.include_router(health.router)
app.include_router(vendor.router)
app.include_router(vendor_delivery.router)
app.include_router(vendor_shop.router)
app.include_router(onboarding.router)
app.include_router(weather.router)


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
