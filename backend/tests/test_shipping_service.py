import tempfile
from pathlib import Path

import pytest

from backend.app.services import shipping, store as store_module


@pytest.fixture(autouse=True)
def isolated_store(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        test_store = store_module.MemoryStore(storage_path=Path(tmp) / "store.json")
        monkeypatch.setattr(store_module, "STORE", test_store)
        monkeypatch.setattr(shipping, "STORE", test_store)
        yield test_store


def valid_home_pickup_payload(**overrides):
    payload = {
        "pickup_method": "HOME_PICKUP",
        "sender_address": "台北市信義區松仁路100號",
        "receiver_address": "新北市板橋區文化路一段1號",
        "weight_kg": 3,
        "length_cm": 20,
        "width_cm": 20,
        "height_cm": 15,
        "item_description": "衣物",
        "declared_value": 500,
        "pickup_time_slot": "14:00",
        "contact_name": "王大明",
        "phone": "0912345678",
    }
    payload.update(overrides)
    return payload


def valid_store_to_store_payload(**overrides):
    payload = {
        "pickup_method": "STORE_TO_STORE",
        "sender_store": "7-ELEVEN 信義門市",
        "receiver_store": "7-ELEVEN 板橋門市",
        "weight_kg": 2,
        "length_cm": 20,
        "width_cm": 15,
        "height_cm": 10,
        "item_description": "書籍",
        "declared_value": 300,
        "pickup_time_slot": "14:00",
        "contact_name": "王大明",
        "phone": "0912345678",
    }
    payload.update(overrides)
    return payload


# ---- estimate_shipping_fee ----

def test_estimate_fee_home_pickup_tiers():
    assert shipping.estimate_shipping_fee("HOME_PICKUP", 3, 20, 20, 15) == (110, 110)  # 55cm
    assert shipping.estimate_shipping_fee("HOME_PICKUP", 3, 30, 30, 25) == (150, 150)  # 85cm
    assert shipping.estimate_shipping_fee("HOME_PICKUP", 3, 40, 40, 30) == (190, 190)  # 110cm


def test_estimate_fee_store_to_store_tiers():
    assert shipping.estimate_shipping_fee("STORE_TO_STORE", 2, 20, 15, 10) == (60, 60)  # 45cm
    assert shipping.estimate_shipping_fee("STORE_TO_STORE", 2, 40, 40, 30) == (125, 135)  # 110cm


# ---- contains_prohibited_keywords ----

def test_prohibited_keywords_detects_battery():
    matched = shipping.contains_prohibited_keywords("裡面有一顆鋰電池")
    assert matched


def test_prohibited_keywords_ignores_plain_clothing():
    assert shipping.contains_prohibited_keywords("衣物一件") == []


# ---- create_shipping_order: happy paths ----

def test_create_shipping_order_home_pickup_success():
    result = shipping.create_shipping_order("user-1", valid_home_pickup_payload())

    assert result["success"] is True
    assert result["status"] == "AWAITING_QUOTE"
    assert result["order_status"] == "01"
    assert result["estimated_fee_min"] == 110

    order = store_module.STORE.get_request("user-1", result["request_id"])
    assert order["service_id"] == "package_shipping"
    assert order["service_vendor_id"] == 2
    assert order["order_type"] == "20"


def test_create_shipping_order_store_to_store_success():
    result = shipping.create_shipping_order("user-1", valid_store_to_store_payload())
    assert result["success"] is True
    assert result["estimated_fee_min"] == 60


# ---- create_shipping_order: validation errors ----

def test_create_shipping_order_rejects_missing_required_field():
    result = shipping.create_shipping_order("user-1", valid_home_pickup_payload(contact_name=""))
    assert result["success"] is False
    assert result["error"]["code"] == "INVALID_FORM_DATA"


def test_create_shipping_order_rejects_oversized_home_pickup_package():
    result = shipping.create_shipping_order(
        "user-1", valid_home_pickup_payload(length_cm=80, width_cm=80, height_cm=80)
    )
    assert result["success"] is False
    assert result["error"]["code"] == "PACKAGE_TOO_LARGE"


def test_create_shipping_order_rejects_overweight_store_to_store_package():
    result = shipping.create_shipping_order("user-1", valid_store_to_store_payload(weight_kg=6))
    assert result["success"] is False
    assert result["error"]["code"] == "PACKAGE_TOO_LARGE"


def test_create_shipping_order_rejects_declared_value_over_limit_for_store_to_store():
    result = shipping.create_shipping_order("user-1", valid_store_to_store_payload(declared_value=6000))
    assert result["success"] is False
    assert result["error"]["code"] == "DECLARED_VALUE_TOO_HIGH"


def test_create_shipping_order_rejects_excluded_county_for_home_pickup():
    result = shipping.create_shipping_order(
        "user-1", valid_home_pickup_payload(sender_address="金門縣金城鎮民生路1號")
    )
    assert result["success"] is False
    assert result["error"]["code"] == "OUT_OF_SERVICE_AREA"
