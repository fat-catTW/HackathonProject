"""Gateway tool handler for listing available services."""
from __future__ import annotations

from shared_lambda.catalog import load_services


def lambda_handler(event, context):
    del event, context
    try:
        services = load_services()
        return {
            "success": True,
            "services": [
                {
                    "id": service["id"],
                    "name": service["name"],
                    "description": service.get("description", ""),
                }
                for service in services
            ],
        }
    except Exception as exc:
        return {
            "success": False,
            "error": {
                "code": "SERVICE_CATALOG_UNAVAILABLE",
                "message": str(exc) or "Failed to load service catalog.",
            },
        }
