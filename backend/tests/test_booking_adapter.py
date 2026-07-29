import asyncio

from backend.app.services.booking_adapter import BookingStatus, MockEZTableAdapter


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def test_create_booking_confirms_for_verification_enabled_restaurant():
    adapter = MockEZTableAdapter()
    result = run(adapter.create_booking(
        restaurant_id="r001", date="2026-08-01", time="12:30",
        people=4, contact_name="王大明", phone="0912345678",
    ))
    assert result.status == BookingStatus.CONFIRMED
    assert result.booking_id is not None
    assert result.share_reservation_url is not None


def test_create_booking_errors_for_verification_disabled_restaurant():
    adapter = MockEZTableAdapter()
    result = run(adapter.create_booking(
        restaurant_id="r003", date="2026-08-01", time="12:30",
        people=2, contact_name="王大明", phone="0912345678",
    ))
    assert result.status == BookingStatus.ERROR
    assert result.booking_id is None


def test_create_booking_errors_for_unknown_restaurant():
    adapter = MockEZTableAdapter()
    result = run(adapter.create_booking(
        restaurant_id="does-not-exist", date="2026-08-01", time="12:30",
        people=2, contact_name="王大明", phone="0912345678",
    ))
    assert result.status == BookingStatus.ERROR


def test_check_availability_always_available_in_mock():
    adapter = MockEZTableAdapter()
    result = run(adapter.check_availability("r001", "2026-08-01", "LUNCH"))
    assert result.available is True
