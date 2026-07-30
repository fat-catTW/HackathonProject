"""Gateway tool handler for reading a user's shop points balance."""
from __future__ import annotations

from shared_lambda.catalog import dynamodb_table


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


def lambda_handler(event, context):
    event = event or {}
    actor_id = _verified_actor_id(event, context)
    if not actor_id:
        return {"success": False, "error": {"code": "UNAUTHORIZED", "message": "Unable to determine actor identity."}}
    try:
        item = dynamodb_table().get_item(Key={"PK": f"USER#{actor_id}", "SK": "POINTS"}).get("Item")
        balance = int(item["balance"]) if item else 0
        return {"success": True, "balance": balance}
    except Exception as exc:
        return {"success": False, "error": {"code": "TOOL_INVOCATION_FAILED", "message": str(exc) or "Failed to read points balance."}}
