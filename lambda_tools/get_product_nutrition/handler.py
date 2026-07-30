"""Gateway tool handler for retrieving a single product's nutrition info."""
from __future__ import annotations

from shared_lambda.health_catalog import get_product


def lambda_handler(event, context):
    del context
    event = event or {}
    product_id = str(event.get("product_id") or "").strip()
    if not product_id:
        return {
            "success": False,
            "error": {
                "code": "INVALID_QUERY",
                "message": "product_id is required.",
            },
        }

    try:
        product = get_product(product_id)
        if not product:
            return {
                "success": False,
                "error": {
                    "code": "PRODUCT_NOT_FOUND",
                    "message": f"找不到 product_id: {product_id}",
                },
            }
        return {"success": True, **product}
    except Exception as exc:
        return {
            "success": False,
            "error": {
                "code": "TOOL_INVOCATION_FAILED",
                "message": str(exc) or "Failed to load product nutrition info.",
            },
        }
