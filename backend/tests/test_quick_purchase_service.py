import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from backend.app.services import quick_purchase, shop, store as store_module


@pytest.fixture(autouse=True)
def isolated_store(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        test_store = store_module.MemoryStore(storage_path=Path(tmp) / "store.json")
        monkeypatch.setattr(store_module, "STORE", test_store)
        monkeypatch.setattr(shop, "STORE", test_store)
        monkeypatch.setattr(quick_purchase, "STORE", test_store)
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


def test_quick_purchase_falls_back_to_bundle_not_found_without_bedrock():
    with patch("backend.app.services.quick_purchase.llm.is_available", return_value=False):
        result = quick_purchase.create_quick_purchase_order(
            "user-1", "完全不相關的字串xyz", contact_name="王大明", phone="0912345678", address="台北市"
        )
    assert result["success"] is False
    assert result["error"]["code"] == "BUNDLE_NOT_FOUND"


def test_quick_purchase_creates_pending_case_for_external_match(isolated_store):
    fake_external = [{"title": "現烤供品組合", "snippet": "在地烘焙供品組合", "link": "https://example.com/x"}]
    fake_pick = [{"result_id": "0", "name": "現烤供品組合", "detail": "在地烘焙供品組合",
                  "link": "https://example.com/x", "reason": "符合供品需求"}]
    with patch("backend.app.services.quick_purchase.llm.is_available", return_value=True), \
         patch("backend.app.services.quick_purchase.llm.plan_external_query", return_value="供品組合"), \
         patch("backend.app.services.quick_purchase.external_search.google_text_search", return_value=fake_external), \
         patch("backend.app.services.quick_purchase.llm.rank_external_results", return_value=fake_pick):
        result = quick_purchase.create_quick_purchase_order(
            "user-1", "完全不相關的字串xyz", contact_name="王大明", phone="0912345678", address="台北市"
        )

    assert result["success"] is True
    assert result["status"] == "PENDING_PROVIDER"
    assert result["source"] == "google_search"
    assert result["bundle_name"] == "現烤供品組合"

    order = isolated_store.get_request("user-1", result["request_id"])
    assert order["status"] == "PENDING_PROVIDER"
    assert order["form_data"]["external_link"] == "https://example.com/x"
