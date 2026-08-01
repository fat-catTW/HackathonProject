import tempfile
from pathlib import Path
from datetime import date, timedelta

import pytest

from backend.app.services import clinic_appointment, clinic_catalog, store as store_module


@pytest.fixture(autouse=True)
def isolated_store(monkeypatch):
    clinic_catalog._cache.clear()
    monkeypatch.setattr(clinic_catalog, "_fetch_all_clinics", lambda: None)
    with tempfile.TemporaryDirectory() as tmp:
        test_store = store_module.MemoryStore(storage_path=Path(tmp) / "store.json")
        monkeypatch.setattr(store_module, "STORE", test_store)
        monkeypatch.setattr(clinic_appointment, "STORE", test_store)
        yield test_store


def valid_payload(**overrides):
    payload = {
        "clinic_id": "clinic-fallback-001",
        "appointment_date": (date.today() + timedelta(days=1)).isoformat(),
        "appointment_time": "15:00",
        "contact_name": "王添財",
        "phone": "0912345678",
        "symptom_note": "咳嗽、喉嚨癢",
    }
    payload.update(overrides)
    return payload


def test_create_appointment_succeeds_and_confirms_immediately():
    result = clinic_appointment.create_appointment("user-1", valid_payload())
    assert result["success"] is True
    assert result["status"] == "CONFIRMED"


def test_create_appointment_fails_for_unknown_clinic():
    result = clinic_appointment.create_appointment("user-1", valid_payload(clinic_id="nope"))
    assert result["success"] is False
    assert result["error"]["code"] == "CLINIC_NOT_FOUND"


def test_create_appointment_fails_for_missing_required_field():
    result = clinic_appointment.create_appointment("user-1", valid_payload(phone=""))
    assert result["success"] is False
    assert result["error"]["code"] == "INVALID_FORM_DATA"


def test_get_appointment_returns_saved_order_with_clinic_details():
    created = clinic_appointment.create_appointment("user-1", valid_payload())
    order = clinic_appointment.get_appointment("user-1", created["request_id"])
    assert order["order_items"]["clinic_name"] == "王耳鼻喉科診所"
    assert order["form_data"]["symptom_note"] == "咳嗽、喉嚨癢"


def test_get_appointment_returns_none_for_unknown_request_id():
    assert clinic_appointment.get_appointment("user-1", "nope") is None


def test_create_appointment_fails_for_invalid_date():
    result = clinic_appointment.create_appointment(
        "user-1", valid_payload(appointment_date="2020-01-01")
    )
    assert result["success"] is False
    assert result["error"]["code"] == "INVALID_DATE"


def test_create_appointment_fails_for_invalid_phone_format():
    result = clinic_appointment.create_appointment("user-1", valid_payload(phone="12345"))
    assert result["success"] is False
    assert result["error"]["code"] == "INVALID_PHONE"


def test_create_appointment_fails_for_invalid_time_format():
    result = clinic_appointment.create_appointment(
        "user-1", valid_payload(appointment_time="25:99")
    )
    assert result["success"] is False
    assert result["error"]["code"] == "INVALID_TIME"


def test_create_appointment_fails_for_blank_after_strip_contact_name():
    result = clinic_appointment.create_appointment("user-1", valid_payload(contact_name="   "))
    assert result["success"] is False
    assert result["error"]["code"] == "INVALID_CONTACT_NAME"
