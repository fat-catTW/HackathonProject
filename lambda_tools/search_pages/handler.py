"""Gateway tool handler for searching app pages."""
from __future__ import annotations

from shared_lambda.page_catalog import search_pages


def lambda_handler(event, context):
    del context
    event = event or {}
    query = str(event.get("query") or "").strip()
    current_page_id = str(event.get("current_page_id") or "").strip() or None
    if not query:
        return {
            "success": False,
            "error": {
                "code": "INVALID_PAGE_REQUEST",
                "message": "query is required.",
            },
        }

    try:
        matches = search_pages(query, current_page_id=current_page_id)
        return {"success": True, "matches": matches}
    except Exception as exc:
        return {
            "success": False,
            "error": {
                "code": "PAGE_CATALOG_UNAVAILABLE",
                "message": str(exc) or "Failed to search pages.",
            },
        }
