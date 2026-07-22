"""Tool execution for mock, embedded AWS, DynamoDB, and Lambda modes."""
from __future__ import annotations

import json
import uuid

import httpx

from ..config import get_settings
from ..services import catalog
from ..services.aws import get_aws_client, get_aws_resource
from ..services.store import STORE, now_iso


def _validate_payload(fields: list[dict], payload: dict) -> list[str]:
    required = [field["id"] for field in fields if field.get("required")]
    return [field_id for field_id in required if payload.get(field_id) in (None, "")]


def _save_request(actor_id: str, session_id: str | None, service: dict, payload: dict) -> dict:
    request_id = STORE.next_request_id()
    try:
        STORE.save_request(
            actor_id,
            {
                "request_id": request_id,
                "session_id": session_id,
                "service_id": service["id"],
                "service_name": service["name"],
                "status": "SUBMITTED",
                "form_data": payload,
                "created_at": now_iso(),
            },
        )
    except Exception as exc:
        return {
            "success": False,
            "error": {"code": "REQUEST_SAVE_FAILED", "message": str(exc)},
        }
    return {
        "success": True,
        "request_id": request_id,
        "status": "SUBMITTED",
        "message": "Service request submitted.",
    }


def _embedded_list_services(_: dict) -> dict:
    return {"success": True, "services": catalog.list_services()}


def _embedded_get_service_schema(params: dict) -> dict:
    schema = catalog.get_service_schema(params.get("service_id", ""))
    if not schema:
        return {
            "success": False,
            "error": {"code": "SERVICE_NOT_FOUND", "message": "Service was not found."},
        }
    return {"success": True, **schema}


def _embedded_submit_service_request(params: dict) -> dict:
    service = catalog.get_service(params.get("service_id", ""))
    if not service:
        return {
            "success": False,
            "error": {"code": "SERVICE_NOT_FOUND", "message": "Service was not found."},
        }
    payload = params.get("payload") or {}
    missing = _validate_payload(service["schema"]["fields"], payload)
    if missing:
        return {
            "success": False,
            "error": {
                "code": "INVALID_FORM_DATA",
                "message": "Missing required fields.",
                "missing_fields": missing,
            },
        }
    return _save_request(params["actor_id"], params.get("session_id"), service, payload)


def _load_catalog_from_dynamodb() -> list[dict]:
    from boto3.dynamodb.conditions import Attr

    table = get_aws_resource("dynamodb").Table(get_settings().dynamodb_table_name)
    items: list[dict] = []
    start_key = None
    while True:
        kwargs = {
            "FilterExpression": Attr("entity_type").eq("SERVICE") & Attr("enabled").eq(True),
        }
        if start_key:
            kwargs["ExclusiveStartKey"] = start_key
        response = table.scan(**kwargs)
        items.extend(response.get("Items", []))
        start_key = response.get("LastEvaluatedKey")
        if not start_key:
            return items


def _dynamodb_list_services(_: dict) -> dict:
    try:
        items = _load_catalog_from_dynamodb()
        if not items:
            return _embedded_list_services({})
        services = [
            {
                "id": item["PK"].split("#", 1)[1],
                "name": item["name"],
                "description": item.get("description", ""),
            }
            for item in items
        ]
        return {"success": True, "services": services}
    except Exception as exc:
        return {
            "success": False,
            "error": {"code": "SERVICE_CATALOG_UNAVAILABLE", "message": str(exc)},
        }


def _load_service_from_dynamodb(service_id: str) -> dict | None:
    table = get_aws_resource("dynamodb").Table(get_settings().dynamodb_table_name)
    item = table.get_item(Key={"PK": f"SERVICE#{service_id}", "SK": "METADATA"}).get("Item")
    if not item or not item.get("enabled"):
        return None
    return {
        "id": service_id,
        "name": item["name"],
        "description": item.get("description", ""),
        "schema": item["schema"],
    }


def _dynamodb_get_service_schema(params: dict) -> dict:
    service_id = params.get("service_id", "")
    try:
        service = _load_service_from_dynamodb(service_id)
        if not service:
            return _embedded_get_service_schema(params)
        return {
            "success": True,
            "service_id": service["id"],
            "title": service["name"],
            "fields": service["schema"]["fields"],
        }
    except Exception as exc:
        return {
            "success": False,
            "error": {"code": "SERVICE_CATALOG_UNAVAILABLE", "message": str(exc)},
        }


def _dynamodb_submit_service_request(params: dict) -> dict:
    service_id = params.get("service_id", "")
    payload = params.get("payload") or {}
    try:
        service = _load_service_from_dynamodb(service_id) or catalog.get_service(service_id)
        if not service:
            return {
                "success": False,
                "error": {"code": "SERVICE_NOT_FOUND", "message": "Service was not found."},
            }
        missing = _validate_payload(service["schema"]["fields"], payload)
        if missing:
            return {
                "success": False,
                "error": {
                    "code": "INVALID_FORM_DATA",
                    "message": "Missing required fields.",
                    "missing_fields": missing,
                },
            }
        return _save_request(params["actor_id"], params.get("session_id"), service, payload)
    except Exception as exc:
        return {
            "success": False,
            "error": {"code": "TOOL_INVOCATION_FAILED", "message": str(exc)},
        }


def _invoke_lambda(tool_name: str, params: dict) -> dict:
    settings = get_settings()
    function_names = {
        "list_services": settings.list_services_lambda_name,
        "get_service_schema": settings.get_service_schema_lambda_name,
        "submit_service_request": settings.submit_service_request_lambda_name,
    }
    function_name = function_names.get(tool_name)
    if not function_name:
        return {
            "success": False,
            "error": {
                "code": "TOOL_INVOCATION_FAILED",
                "message": f"Lambda not configured for {tool_name}.",
            },
        }

    event = dict(params)
    actor_id = event.pop("actor_id", None)
    if actor_id:
        event["requestContext"] = {"identity": {"actorId": actor_id}}

    try:
        response = get_aws_client("lambda").invoke(
            FunctionName=function_name,
            InvocationType="RequestResponse",
            Payload=json.dumps(event).encode("utf-8"),
        )
        payload = response["Payload"].read().decode("utf-8")
        result = json.loads(payload) if payload else {}
        if isinstance(result, dict) and "body" in result and isinstance(result["body"], str):
            try:
                result = json.loads(result["body"])
            except json.JSONDecodeError:
                pass
        if response.get("FunctionError"):
            return {
                "success": False,
                "error": {
                    "code": "TOOL_INVOCATION_FAILED",
                    "message": payload or "Lambda invocation failed.",
                },
            }
        return result
    except Exception as exc:
        return {
            "success": False,
            "error": {"code": "TOOL_INVOCATION_FAILED", "message": str(exc)},
        }


def _gateway_tool_name(tool_name: str) -> str:
    settings = get_settings()
    names = {
        "list_services": settings.mcp_list_services_tool_name,
        "get_service_schema": settings.mcp_get_service_schema_tool_name,
        "submit_service_request": settings.mcp_submit_service_request_tool_name,
    }
    return names.get(tool_name, tool_name)


def _gateway_endpoint() -> str | None:
    settings = get_settings()
    base = settings.agentcore_gateway_url.strip()
    if not base:
        return None
    if base.endswith("/mcp"):
        return base
    return f"{base.rstrip('/')}{settings.agentcore_gateway_mcp_path}"


def _gateway_headers(auth_token: str | None) -> dict:
    settings = get_settings()
    token = auth_token
    if token in settings.demo_users:
        token = settings.agentcore_gateway_auth_token or ""
    elif not token:
        token = settings.agentcore_gateway_auth_token
    headers = {"Content-Type": "application/json"}
    if token:
        scheme = settings.agentcore_gateway_auth_scheme.strip() or "Bearer"
        headers["Authorization"] = f"{scheme} {token}"
    return headers


def _parse_mcp_result(payload: dict) -> dict:
    if not isinstance(payload, dict):
        return {
            "success": False,
            "error": {"code": "TOOL_INVOCATION_FAILED", "message": "Invalid MCP response payload."},
        }

    if isinstance(payload.get("error"), dict):
        error = payload["error"]
        return {
            "success": False,
            "error": {
                "code": error.get("code", "TOOL_INVOCATION_FAILED"),
                "message": error.get("message", "MCP tool call failed."),
            },
        }

    result = payload.get("result")
    if not isinstance(result, dict):
        return {
            "success": False,
            "error": {"code": "TOOL_INVOCATION_FAILED", "message": "Missing MCP result payload."},
        }

    if isinstance(result.get("structuredContent"), dict):
        structured = result["structuredContent"]
        if "success" not in structured:
            structured["success"] = not bool(result.get("isError"))
        return structured

    content = result.get("content")
    if isinstance(content, list):
        for item in content:
            if not isinstance(item, dict):
                continue
            if isinstance(item.get("json"), dict):
                body = item["json"]
                if "success" not in body:
                    body["success"] = not bool(result.get("isError"))
                return body
            text = item.get("text")
            if isinstance(text, str) and text.strip():
                try:
                    body = json.loads(text)
                except json.JSONDecodeError:
                    continue
                if isinstance(body, dict):
                    if "success" not in body:
                        body["success"] = not bool(result.get("isError"))
                    return body

    return {
        "success": not bool(result.get("isError")),
        "mcp_result": result,
    }


def _invoke_mcp_gateway(tool_name: str, params: dict, auth_token: str | None) -> dict:
    endpoint = _gateway_endpoint()
    if not endpoint:
        return {
            "success": False,
            "error": {
                "code": "TOOL_INVOCATION_FAILED",
                "message": "AGENTCORE_GATEWAY_URL is not configured.",
            },
        }

    payload = {
        "jsonrpc": "2.0",
        "id": f"tool-{uuid.uuid4().hex[:12]}",
        "method": "tools/call",
        "params": {
            "name": _gateway_tool_name(tool_name),
            "arguments": params,
        },
    }

    try:
        with httpx.Client(timeout=20.0) as client:
            response = client.post(
                endpoint,
                headers=_gateway_headers(auth_token),
                json=payload,
            )
        response.raise_for_status()
        return _parse_mcp_result(response.json())
    except httpx.HTTPStatusError as exc:
        body = exc.response.text.strip()
        return {
            "success": False,
            "error": {
                "code": "TOOL_INVOCATION_FAILED",
                "message": body or f"MCP gateway returned HTTP {exc.response.status_code}.",
            },
        }
    except Exception as exc:
        return {
            "success": False,
            "error": {"code": "TOOL_INVOCATION_FAILED", "message": str(exc)},
        }


_EMBEDDED_TOOLS = {
    "list_services": _embedded_list_services,
    "get_service_schema": _embedded_get_service_schema,
    "submit_service_request": _embedded_submit_service_request,
}

_DYNAMODB_TOOLS = {
    "list_services": _dynamodb_list_services,
    "get_service_schema": _dynamodb_get_service_schema,
    "submit_service_request": _dynamodb_submit_service_request,
}


def call(tool_name: str, params: dict, auth_token: str | None = None) -> dict:
    settings = get_settings()

    if settings.use_mock:
        fn = _EMBEDDED_TOOLS.get(tool_name)
        if not fn:
            return {
                "success": False,
                "error": {"code": "TOOL_INVOCATION_FAILED", "message": f"Unknown tool: {tool_name}"},
            }
        return fn(params)

    if settings.agent_tool_mode in {"mcp", "gateway"}:
        return _invoke_mcp_gateway(tool_name, params, auth_token)

    if settings.agent_tool_mode == "lambda" or settings.lambda_tooling_enabled:
        return _invoke_lambda(tool_name, params)

    if settings.agent_tool_mode == "dynamodb":
        fn = _DYNAMODB_TOOLS.get(tool_name)
    else:
        fn = _EMBEDDED_TOOLS.get(tool_name)

    if not fn:
        return {
            "success": False,
            "error": {"code": "TOOL_INVOCATION_FAILED", "message": f"Unknown tool: {tool_name}"},
        }
    return fn(params)
