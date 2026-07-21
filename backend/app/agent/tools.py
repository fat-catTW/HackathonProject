"""MCP Tool 呼叫層。

Mock 模式：直接 import lambda_tools 的 handler 邏輯在本地執行，
輸入輸出格式與設計書 §12 Tool Spec 完全一致。
Milestone 4 之後改走 AgentCore Gateway（MCP），此模組介面不變。
"""
from __future__ import annotations

from ..config import get_settings
from ..services import catalog
from ..services.store import STORE, now_iso


def _list_services(_: dict) -> dict:
    return {"success": True, "services": catalog.list_services()}


def _get_service_schema(params: dict) -> dict:
    schema = catalog.get_service_schema(params.get("service_id", ""))
    if not schema:
        return {"success": False,
                "error": {"code": "SERVICE_NOT_FOUND", "message": "找不到指定服務"}}
    return {"success": True, **schema}


def _submit_service_request(params: dict) -> dict:
    service = catalog.get_service(params.get("service_id", ""))
    if not service:
        return {"success": False,
                "error": {"code": "SERVICE_NOT_FOUND", "message": "找不到指定服務"}}
    payload = params.get("payload") or {}
    required = [f["id"] for f in service["schema"]["fields"] if f.get("required")]
    missing = [fid for fid in required if payload.get(fid) in (None, "")]
    if missing:
        return {"success": False,
                "error": {"code": "INVALID_FORM_DATA", "message": "表單資料不完整",
                          "missing_fields": missing}}

    actor_id = params["actor_id"]  # 由已驗證身分注入，不接受前端指定
    request_id = STORE.next_request_id()
    STORE.save_request(actor_id, {
        "request_id": request_id,
        "session_id": params.get("session_id"),
        "service_id": service["id"],
        "service_name": service["name"],
        "status": "SUBMITTED",
        "form_data": payload,
        "created_at": now_iso(),
    })
    return {"success": True, "request_id": request_id, "status": "SUBMITTED",
            "message": "服務申請已成功建立"}


_LOCAL_TOOLS = {
    "list_services": _list_services,
    "get_service_schema": _get_service_schema,
    "submit_service_request": _submit_service_request,
}


def call(tool_name: str, params: dict) -> dict:
    settings = get_settings()
    if settings.use_mock:
        fn = _LOCAL_TOOLS.get(tool_name)
        if not fn:
            return {"success": False,
                    "error": {"code": "TOOL_INVOCATION_FAILED",
                              "message": f"未知 Tool: {tool_name}"}}
        try:
            return fn(params)
        except Exception as exc:  # noqa: BLE001
            return {"success": False,
                    "error": {"code": "TOOL_INVOCATION_FAILED", "message": str(exc)}}
    # 非 mock：透過 AgentCore Gateway 呼叫 MCP Tool（Milestone 4）
    raise NotImplementedError("AgentCore Gateway 尚未接入，請設定 USE_MOCK=true")
