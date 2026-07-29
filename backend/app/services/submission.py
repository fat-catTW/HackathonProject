"""Manual form submission flow for the non-AI service pages."""
from __future__ import annotations

from . import catalog
from .store import STORE, now_iso


def _field_is_visible(field: dict, payload: dict) -> bool:
    visible_when = field.get("visibleWhen")
    if not isinstance(visible_when, dict):
        return True
    parent_field_id = visible_when.get("fieldId")
    expected_value = visible_when.get("value")
    if not isinstance(parent_field_id, str):
        return True
    return payload.get(parent_field_id) == expected_value


def _missing_required_fields(fields: list[dict], payload: dict) -> list[str]:
    required = [
        field["id"]
        for field in fields
        if field.get("required") and _field_is_visible(field, payload)
    ]
    return [field_id for field_id in required if payload.get(field_id) in (None, "")]


def _missing_required_fields_message(fields: list[dict], missing: list[str]) -> str:
    field_labels = {
        field["id"]: field.get("label", field["id"])
        for field in fields
    }
    labels = [field_labels.get(field_id, field_id) for field_id in missing]
    return f"缺少必填欄位：{'、'.join(labels)}。"


def create_manual_service_request(
    actor_id: str,
    service_id: str,
    payload: dict,
    session_id: str | None = None,
) -> dict:
    service = catalog.get_service(service_id)
    if not service:
        return {
            "success": False,
            "error": {"code": "SERVICE_NOT_FOUND", "message": "Service was not found."},
        }

    missing = _missing_required_fields(service["schema"]["fields"], payload)
    if missing:
        return {
            "success": False,
            "error": {
                "code": "INVALID_FORM_DATA",
                "message": _missing_required_fields_message(service["schema"]["fields"], missing),
                "missing_fields": missing,
            },
        }

    request_id = STORE.next_request_id()
    try:
        STORE.save_request(
            actor_id,
            {
                "request_id": request_id,
                "session_id": session_id,
                "service_id": service["id"],
                "service_name": service["name"],
                "service_vendor_id": service.get("service_vendor_id"),
                "status": "SUBMITTED",
                "form_data": payload,
                "created_at": now_iso(),
            },
        )
    except Exception as exc:
        return {
            "success": False,
            "error": {"code": "REQUEST_SAVE_FAILED", "message": str(exc)},
        }

    return {
        "success": True,
        "request_id": request_id,
        "status": "SUBMITTED",
        "message": "Service request submitted.",
    }
