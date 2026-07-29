import tempfile
from pathlib import Path

import pytest

from backend.app.services import reservation, store as store_module


@pytest.fixture(autouse=True)
def isolated_store(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        test_store = store_module.MemoryStore(storage_path=Path(tmp) / "store.json")
        monkeypatch.setattr(store_module, "STORE", test_store)
        monkeypatch.setattr(reservation, "STORE", test_store)
        yield test_store


def valid_payload(**overrides):
    payload = {
        "restaurant_id": "r001",
        "reserved_date": "2026-08-01",
        "time_slot": "LUNCH",
        "specific_time": "12:30",
        "people": 4,
        "contact_name": "王大明",
        "phone": "0912345678",
        "is_premium": False,
        "preference_note": None,
    }
    payload.update(overrides)
    return payload


def test_create_reservation_order_confirms_immediately_for_supported_restaurant():
    result = reservation.create_reservation_order("user-1", valid_payload())

    assert result["success"] is True
    assert result["status"] == "CONFIRMED"
    assert result["order_status"] == "03"
    assert result["booking_url"] is not None

    order = reservation.get_reservation_order("user-1", result["request_id"])
    assert order["order_type"] == "02"
    assert order["order_items"]["restaurant_name"] == "22世紀風味館 信義旗艦店"
    assert order["service_time"] == "2026-08-01T12:30:00+08:00"


def test_create_reservation_order_pending_when_restaurant_unsupported():
    result = reservation.create_reservation_order("user-1", valid_payload(restaurant_id="r005"))

    assert result["success"] is True
    assert result["status"] == "PENDING_PROVIDER"
    assert result["order_status"] == "02"
    assert result["booking_url"] is None


def test_create_reservation_order_pending_and_retried_on_adapter_error():
    result = reservation.create_reservation_order("user-1", valid_payload(restaurant_id="r003"))

    assert result["status"] == "PENDING_PROVIDER"
    order = reservation.get_reservation_order("user-1", result["request_id"])
    assert order["retry_info"]["retry_count"] >= 0
    assert order["retry_info"]["needs_manual"] is False


def test_create_reservation_order_premium_skips_adapter_even_if_supported():
    result = reservation.create_reservation_order("user-1", valid_payload(is_premium=True))

    assert result["status"] == "PENDING_PROVIDER"
    order = reservation.get_reservation_order("user-1", result["request_id"])
    assert order["order_items"]["is_premium"] is True
    assert order["vendor_data"] == {}


def test_create_reservation_order_rejects_invalid_phone():
    result = reservation.create_reservation_order("user-1", valid_payload(phone="12345"))
    assert result["success"] is False
    assert result["error"]["code"] == "INVALID_PHONE"


def test_create_reservation_order_rejects_out_of_range_people():
    result = reservation.create_reservation_order("user-1", valid_payload(people=21))
    assert result["success"] is False
    assert result["error"]["code"] == "INVALID_PEOPLE_COUNT"


def test_create_reservation_order_rejects_unknown_restaurant():
    result = reservation.create_reservation_order("user-1", valid_payload(restaurant_id="nope"))
    assert result["success"] is False
    assert result["error"]["code"] == "RESTAURANT_NOT_FOUND"


def test_check_duplicate_blocks_same_restaurant_date_slot_for_same_user():
    reservation.create_reservation_order("user-1", valid_payload())

    result = reservation.create_reservation_order("user-1", valid_payload())

    assert result["success"] is False
    assert result["error"]["code"] == "DUPLICATE_RESERVATION"


def test_check_duplicate_allows_different_user_same_slot():
    reservation.create_reservation_order("user-1", valid_payload())

    result = reservation.create_reservation_order("user-2", valid_payload())

    assert result["success"] is True


def test_cancel_reservation_order_sets_cancelled_status():
    created = reservation.create_reservation_order("user-1", valid_payload())

    result = reservation.cancel_reservation_order("user-1", created["request_id"])

    assert result["success"] is True
    order = reservation.get_reservation_order("user-1", created["request_id"])
    assert order["status"] == "CANCELLED"
    assert order["order_status"] == "90"


def test_get_reservation_order_returns_none_for_missing_request():
    assert reservation.get_reservation_order("user-1", "REQ-NOPE") is None
