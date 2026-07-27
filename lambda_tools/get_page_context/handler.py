"""Gateway tool handler for retrieving app page knowledge."""
from __future__ import annotations

from shared_lambda.page_catalog import load_page


def lambda_handler(event, context):
    del context
    event = event or {}
    page_id = str(event.get("page_id") or "").strip()
    if not page_id:
        return {
            "success": False,
            "error": {
                "code": "INVALID_PAGE_REQUEST",
                "message": "page_id is required.",
            },
        }

    try:
        page = load_page(page_id)
        if not page:
            return {
                "success": False,
                "error": {
                    "code": "PAGE_NOT_FOUND",
                    "message": f"Unknown page_id: {page_id}.",
                },
            }
        return {"success": True, "page": page}
    except Exception as exc:
        return {
            "success": False,
            "error": {
                "code": "PAGE_CATALOG_UNAVAILABLE",
                "message": str(exc) or "Failed to load page context.",
            },
        }
