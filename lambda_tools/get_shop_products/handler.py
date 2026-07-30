"""Gateway tool handler for listing shop products, optionally filtered by store."""
from __future__ import annotations

from shared_lambda.shop_catalog import list_products


def lambda_handler(event, context):
    del context
    event = event or {}
    store_id = event.get("store_id")
    try:
        return {"success": True, "products": list_products(store_id)}
    except Exception as exc:
        return {"success": False, "error": {"code": "TOOL_INVOCATION_FAILED", "message": str(exc) or "Failed to list shop products."}}
