"""Gateway tool handler for recommending 7-11 products by health need."""
from __future__ import annotations

from shared_lambda.health_catalog import list_products
from shared_lambda.health_recommendation import recommend


def lambda_handler(event, context):
    del context
    event = event or {}
    query = str(event.get("query") or "").strip()
    if not query:
        return {
            "success": False,
            "error": {
                "code": "INVALID_QUERY",
                "message": "query is required.",
            },
        }

    try:
        result = recommend(query, list_products())
        return {"success": True, **result}
    except Exception as exc:
        return {
            "success": False,
            "error": {
                "code": "TOOL_INVOCATION_FAILED",
                "message": str(exc) or "Failed to generate recommendations.",
            },
        }
