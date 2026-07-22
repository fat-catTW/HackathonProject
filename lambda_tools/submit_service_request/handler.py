"""Gateway tool handler for submitting service requests."""
from __future__ import annotations

from datetime import date

from shared_lambda.catalog import (
    dynamodb_table,
    load_service,
    next_request_id,
    now_iso,
    validate_required_fields,
)


def _context_value(context, key: str) -> str | None:
    client_context = getattr(context, "client_context", None)
    custom = getattr(client_context, "custom", None)
    if isinstance(custom, dict):
        value = custom.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _verified_actor_id(event: dict, context) -> str | None:
    request_context = event.get("requestContext") or {}
    identity = request_context.get("identity") or {}
    for value in (
        identity.get("actorId"),
        event.get("actor_id"),
        _context_value(context, "actorId"),
        _context_value(context, "principalId"),
    ):
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _is_future_or_today(raw_date: str) -> bool:
    try:
        return date.fromisoformat(raw_date) >= date.today()
    except ValueError:
        return False


def _validate_payload_shape(payload: dict) -> str | None:
    if not isinstance(payload, dict):
        return "payload must be an object."
    preferred_date = payload.get("preferred_date")
    if isinstance(preferred_date, str) and preferred_date and not _is_future_or_today(preferred_date):
        return "preferred_date must be today or a future date."
    return None


def lambda_handler(event, context):
    event = event or {}
    service_id = event.get("service_id")
    session_id = event.get("session_id")
    payload = event.get("payload") or {}
    actor_id = _verified_actor_id(event, context)

    if not service_id:
        return {
            "success": False,
            "error": {
                "code": "INVALID_FORM_DATA",
                "message": "service_id is required.",
            },
        }
    if not session_id:
        return {
            "success": False,
            "error": {
                "code": "INVALID_FORM_DATA",
                "message": "session_id is required.",
            },
        }
    if not actor_id:
        return {
            "success": False,
            "error": {
                "code": "UNAUTHORIZED",
                "message": "Unable to determine actor identity.",
            },
        }

    payload_error = _validate_payload_shape(payload)
    if payload_error:
        return {
            "success": False,
            "error": {
                "code": "INVALID_FORM_DATA",
                "message": payload_error,
            },
        }

    try:
        service = load_service(service_id)
        if not service:
            return {
                "success": False,
                "error": {
                    "code": "SERVICE_NOT_FOUND",
                    "message": f"Unknown service_id: {service_id}.",
                },
            }

        missing_fields = validate_required_fields(service["schema"]["fields"], payload)
        if missing_fields:
            return {
                "success": False,
                "error": {
                    "code": "INVALID_FORM_DATA",
                    "message": "Missing required fields.",
                    "missing_fields": missing_fields,
                },
            }

        request_id = next_request_id()
        timestamp = now_iso()
        dynamodb_table().put_item(
            Item={
                "PK": f"USER#{actor_id}",
                "SK": f"REQUEST#{request_id}",
                "entity_type": "SERVICE_REQUEST",
                "request_id": request_id,
                "session_id": session_id,
                "service_id": service["id"],
                "service_name": service["name"],
                "status": "SUBMITTED",
                "form_data": payload,
                "created_at": timestamp,
                "updated_at": timestamp,
            }
        )
        return {
            "success": True,
            "request_id": request_id,
            "status": "SUBMITTED",
            "message": "Service request submitted.",
        }
    except Exception as exc:
        return {
            "success": False,
            "error": {
                "code": "TOOL_INVOCATION_FAILED",
                "message": str(exc) or "Failed to submit service request.",
            },
        }
