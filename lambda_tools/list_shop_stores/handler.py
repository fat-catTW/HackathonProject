"""Gateway tool handler for listing shop stores."""
from __future__ import annotations

from shared_lambda.shop_catalog import list_stores


def lambda_handler(event, context):
    del event, context
    try:
        return {"success": True, "stores": list_stores()}
    except Exception as exc:
        return {"success": False, "error": {"code": "TOOL_INVOCATION_FAILED", "message": str(exc) or "Failed to list shop stores."}}
