"""Clinic appointment order — mirrors reservation.py's shape but always
confirms immediately (no third-party booking system to call for a demo
clinic), and reuses STORE.save_request's existing contact-field
encryption/masking (keyed by field name, not service_id)."""
from __future__ import annotations

from . import clinic_catalog
from .store import STORE, now_iso

_REQUIRED_FIELDS = (
    "clinic_id",
    "appointment_date",
    "appointment_time",
    "contact_name",
    "phone",
    "symptom_note",
)


def _error(code: str, message: str) -> dict:
    return {"success": False, "error": {"code": code, "message": message}}


def _validate_payload(payload: dict) -> dict | None:
    for field_id in _REQUIRED_FIELDS:
        if payload.get(field_id) in (None, ""):
            return _error("INVALID_FORM_DATA", f"Missing required field: {field_id}")
    if not clinic_catalog.get_clinic(payload["clinic_id"]):
        return _error("CLINIC_NOT_FOUND", "找不到指定的診所。")
    return None


def create_appointment(actor_id: str, payload: dict) -> dict:
    validation_error = _validate_payload(payload)
    if validation_error:
        return validation_error

    clinic = clinic_catalog.get_clinic(payload["clinic_id"])

    order_items = {
        "clinic_id": clinic["id"],
        "clinic_name": clinic["name"],
        "clinic_address": clinic["address"],
        "clinic_phone": clinic["phone"],
        "appointment_date": payload["appointment_date"],
        "appointment_time": payload["appointment_time"],
    }

    request_id = STORE.next_request_id()
    created_at = now_iso()
    order = {
        "request_id": request_id,
        "session_id": None,
        "service_id": "clinic_appointment",
        "service_name": "診所掛號",
        "order_items": order_items,
        "form_data": {
            "clinic_name": clinic["name"],
            "clinic_address": clinic["address"],
            "clinic_phone": clinic["phone"],
            "appointment_date": payload["appointment_date"],
            "appointment_time": payload["appointment_time"],
            "symptom_note": payload["symptom_note"],
            "contact_name": payload["contact_name"],
            "phone": payload["phone"],
        },
        "vendor_data": {},
        "status": "CONFIRMED",
        "status_history": [],
        "created_at": created_at,
    }
    order["status_history"].append({"status": "CONFIRMED", "at": created_at})

    try:
        STORE.save_request(actor_id, order)
    except Exception as exc:
        return _error("REQUEST_SAVE_FAILED", str(exc))

    return {"success": True, "request_id": request_id, "status": "CONFIRMED"}


def get_appointment(actor_id: str, request_id: str) -> dict | None:
    return STORE.get_request(actor_id, request_id)
