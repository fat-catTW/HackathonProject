"""Gateway tool handler for retrieving a service form schema."""
from __future__ import annotations

from shared_lambda.catalog import load_service


def lambda_handler(event, context):
    del context
    event = event or {}
    service_id = event.get("service_id")
    if not service_id:
        return {
            "success": False,
            "error": {
                "code": "INVALID_FORM_DATA",
                "message": "service_id is required.",
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
        return {
            "success": True,
            "service_id": service["id"],
            "title": service["name"],
            "fields": service["schema"]["fields"],
        }
    except Exception as exc:
        return {
            "success": False,
            "error": {
                "code": "SERVICE_CATALOG_UNAVAILABLE",
                "message": str(exc) or "Failed to load service schema.",
            },
        }
