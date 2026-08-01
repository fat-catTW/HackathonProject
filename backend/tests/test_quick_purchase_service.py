import tempfile
from pathlib import Path

import pytest

from backend.app.services import quick_purchase, shop, store as store_module


@pytest.fixture(autouse=True)
def isolated_store(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        test_store = store_module.MemoryStore(storage_path=Path(tmp) / "store.json")
        monkeypatch.setattr(store_module, "STORE", test_store)
        monkeypatch.setattr(shop, "STORE", test_store)
        test_store.restock_sku("sku_fruit_offering_set", 5)
        yield test_store


def test_create_quick_purchase_order_matches_bundle_and_submits():
    result = quick_purchase.create_quick_purchase_order(
        "user-a",
        "拜拜要用的水果",
        contact_name="王添財",
        phone="0912345678",
        address="台中市西屯區文心路一段1號",
    )
    assert result["success"] is True
    assert result["bundle_name"] == "清明祭祖水果盆"
    assert result["request_id"]


def test_create_quick_purchase_order_unmatched_query_fails():
    result = quick_purchase.create_quick_purchase_order(
        "user-a", "我要買一台冷氣", contact_name="王添財", phone="0912345678", address="台中市"
    )
    assert result["success"] is False
    assert result["error"]["code"] == "BUNDLE_NOT_FOUND"
