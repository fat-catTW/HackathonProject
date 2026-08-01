from datetime import datetime

import pytest

from backend.app.services import clinic_catalog


@pytest.fixture(autouse=True)
def clear_cache():
    clinic_catalog._cache.clear()
    yield
    clinic_catalog._cache.clear()


MONDAY_10AM = datetime(2026, 8, 3, 10, 0)  # 2026-08-03 is a Monday


def test_list_clinics_falls_back_to_static_list_when_fetch_fails(monkeypatch):
    monkeypatch.setattr(clinic_catalog, "_fetch_all_clinics", lambda: None)
    results = clinic_catalog.list_clinics("台中市", "西屯區", now=MONDAY_10AM)
    assert len(results) > 0
    assert all("台中市西屯區" in c["address"] for c in results)


def test_list_clinics_filters_by_specialty(monkeypatch):
    monkeypatch.setattr(clinic_catalog, "_fetch_all_clinics", lambda: None)
    results = clinic_catalog.list_clinics("台中市", "西屯區", "耳鼻喉科", now=MONDAY_10AM)
    assert len(results) >= 1
    assert all("耳鼻喉科" in c["specialties"] for c in results)


def test_list_clinics_excludes_other_districts(monkeypatch):
    monkeypatch.setattr(clinic_catalog, "_fetch_all_clinics", lambda: None)
    results = clinic_catalog.list_clinics("高雄市", "苓雅區", now=MONDAY_10AM)
    assert results == []


def test_get_clinic_returns_none_for_unknown_id(monkeypatch):
    monkeypatch.setattr(clinic_catalog, "_fetch_all_clinics", lambda: None)
    assert clinic_catalog.get_clinic("nope", now=MONDAY_10AM) is None


def test_get_clinic_returns_expected_shape(monkeypatch):
    monkeypatch.setattr(clinic_catalog, "_fetch_all_clinics", lambda: None)
    clinic = clinic_catalog.get_clinic("clinic-fallback-001", now=MONDAY_10AM)
    assert clinic["name"] == "王耳鼻喉科診所"
    assert clinic["is_open_now"] is True


def test_is_open_now_true_when_duty_string_matches_current_session():
    assert clinic_catalog._is_open_now("星期一上午看診", now=MONDAY_10AM) is True


def test_is_open_now_false_when_duty_string_says_closed():
    assert clinic_catalog._is_open_now("星期一上午休診", now=MONDAY_10AM) is False


def test_normalize_record_splits_comma_separated_specialties():
    record = {
        "HOSP_ID": "12345",
        "HOSP_NAME": "測試診所",
        "ADDRESS": "台中市西屯區測試路1號",
        "TEL": "04-1234567",
        "FUNCTYPE_CNAME": "內科,眼科,復健科",
        "HOLIDAYDUTY_CNAME": "星期一上午看診",
    }
    normalized = clinic_catalog._normalize_record(record)
    assert normalized["specialties"] == ["內科", "眼科", "復健科"]


def test_normalize_record_returns_none_when_missing_required_fields():
    assert clinic_catalog._normalize_record({"HOSP_ID": "1"}) is None


def _raw_record(hosp_id, name, address, holiday_duty_cname=""):
    return {
        "HOSP_ID": hosp_id,
        "HOSP_NAME": name,
        "ADDRESS": address,
        "TEL": "04-0000000",
        "FUNCTYPE_CNAME": "家醫科",
        "HOLIDAYDUTY_CNAME": holiday_duty_cname,
    }


def test_list_clinics_matches_taiwan_variant_char_from_live_fetch(monkeypatch):
    records = [
        _raw_record("fetch-001", "臺中西屯某診所", "臺中市西屯區某路1號"),
        _raw_record("fetch-002", "台北大安某診所", "台北市大安區某路2號"),
    ]
    monkeypatch.setattr(clinic_catalog, "_fetch_all_clinics", lambda: records)
    results = clinic_catalog.list_clinics("台中市", "西屯區", now=MONDAY_10AM)
    assert any(c["id"] == "fetch-001" for c in results)


def test_list_clinics_matches_specialty_within_compound_string(monkeypatch):
    """Real NHI data reports specialties like "耳鼻喉科(耳鼻喉頭頸外科)" rather
    than a bare "耳鼻喉科" — the filter must match by substring, not exact
    list membership, or every real ENT clinic gets silently excluded."""
    record = _raw_record("fetch-ent-001", "真實耳鼻喉科診所", "台中市西屯區某路9號")
    record["FUNCTYPE_CNAME"] = "耳鼻喉科(耳鼻喉頭頸外科)"
    monkeypatch.setattr(clinic_catalog, "_fetch_all_clinics", lambda: [record])
    results = clinic_catalog.list_clinics("台中市", "西屯區", "耳鼻喉科", now=MONDAY_10AM)
    assert any(c["id"] == "fetch-ent-001" for c in results)


def test_list_clinics_caps_results_at_ten_and_sorts_open_first(monkeypatch):
    records = []
    for i in range(15):
        # Odd-indexed clinics are open (星期一上午看診); even-indexed are closed.
        duty = "星期一上午看診" if i % 2 == 1 else "星期一上午休診"
        records.append(
            _raw_record(
                f"fetch-{i:03d}",
                f"西屯診所{i}",
                "台中市西屯區某路1號",
                holiday_duty_cname=duty,
            )
        )
    monkeypatch.setattr(clinic_catalog, "_fetch_all_clinics", lambda: records)
    results = clinic_catalog.list_clinics("台中市", "西屯區", now=MONDAY_10AM)
    assert len(results) == 10
    open_flags = [c["is_open_now"] for c in results]
    # All open entries should be sorted before closed entries.
    assert open_flags == sorted(open_flags, reverse=True)
    assert any(flag is True for flag in open_flags)
