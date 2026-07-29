from datetime import date, timedelta

from hypothesis import given, strategies as st

from backend.app.services.reservation_validators import (
    build_service_time,
    validate_contact_name,
    validate_date,
    validate_people,
    validate_phone,
    validate_preference_note,
    validate_specific_time,
    validate_time_slot,
)

TODAY = date(2026, 7, 29)


# --- example-based boundary tests ---

def test_validate_date_accepts_today():
    assert validate_date(TODAY.isoformat(), today=TODAY) is True


def test_validate_date_accepts_today_plus_60():
    d = (TODAY + timedelta(days=60)).isoformat()
    assert validate_date(d, today=TODAY) is True


def test_validate_date_rejects_today_plus_61():
    d = (TODAY + timedelta(days=61)).isoformat()
    assert validate_date(d, today=TODAY) is False


def test_validate_date_rejects_yesterday():
    d = (TODAY - timedelta(days=1)).isoformat()
    assert validate_date(d, today=TODAY) is False


def test_validate_date_rejects_malformed_string():
    assert validate_date("not-a-date", today=TODAY) is False


def test_validate_people_accepts_boundaries():
    assert validate_people(1) is True
    assert validate_people(20) is True


def test_validate_people_rejects_out_of_range():
    assert validate_people(0) is False
    assert validate_people(21) is False


def test_validate_people_rejects_non_integer():
    assert validate_people(2.5) is False
    assert validate_people("2") is False
    assert validate_people(None) is False


def test_validate_phone_accepts_valid_taiwan_mobile():
    assert validate_phone("0912345678") is True


def test_validate_phone_rejects_wrong_prefix():
    assert validate_phone("0812345678") is False


def test_validate_phone_rejects_wrong_length():
    assert validate_phone("091234567") is False
    assert validate_phone("09123456789") is False


def test_validate_phone_rejects_non_digits():
    assert validate_phone("0912-345-678") is False


def test_validate_phone_rejects_trailing_newline():
    assert validate_phone("0912345678\n") is False


def test_validate_contact_name_accepts_normal_name():
    assert validate_contact_name("王大明") is True


def test_validate_contact_name_rejects_blank():
    assert validate_contact_name("   ") is False
    assert validate_contact_name("") is False


def test_validate_contact_name_rejects_too_long():
    assert validate_contact_name("王" * 51) is False


def test_validate_contact_name_accepts_50_chars():
    assert validate_contact_name("王" * 50) is True


def test_validate_time_slot_accepts_lunch_and_dinner():
    assert validate_time_slot("LUNCH") is True
    assert validate_time_slot("DINNER") is True


def test_validate_time_slot_rejects_unknown():
    assert validate_time_slot("BRUNCH") is False


def test_validate_specific_time_accepts_lunch_boundary():
    assert validate_specific_time("LUNCH", "11:00") is True
    assert validate_specific_time("LUNCH", "13:30") is True


def test_validate_specific_time_rejects_lunch_out_of_range():
    assert validate_specific_time("LUNCH", "14:00") is False
    assert validate_specific_time("LUNCH", "10:30") is False


def test_validate_specific_time_rejects_non_30min_increment():
    assert validate_specific_time("LUNCH", "12:15") is False


def test_validate_preference_note_accepts_none_and_short_text():
    assert validate_preference_note(None) is True
    assert validate_preference_note("靠窗座位") is True


def test_validate_preference_note_rejects_over_200_chars():
    assert validate_preference_note("字" * 201) is False


def test_build_service_time_uses_specific_time():
    result = build_service_time("2026-08-01", "12:30", "LUNCH")
    assert result == "2026-08-01T12:30:00+08:00"


def test_build_service_time_falls_back_to_slot_default():
    assert build_service_time("2026-08-01", None, "LUNCH") == "2026-08-01T12:00:00+08:00"
    assert build_service_time("2026-08-01", None, "DINNER") == "2026-08-01T18:00:00+08:00"


# --- property-based tests (Requirement design.md Property 1-4) ---

@given(st.integers(min_value=1, max_value=20))
def test_property_people_in_range_always_valid(n):
    assert validate_people(n) is True


@given(st.integers().filter(lambda n: n < 1 or n > 20))
def test_property_people_out_of_range_always_invalid(n):
    assert validate_people(n) is False


@given(st.from_regex(r"09\d{8}", fullmatch=True))
def test_property_valid_taiwan_phone_shape_always_accepted(phone):
    assert validate_phone(phone) is True


@given(st.text(min_size=1, max_size=50).filter(lambda s: s.strip()))
def test_property_nonblank_name_within_50_chars_always_valid(name):
    assert validate_contact_name(name) is True
