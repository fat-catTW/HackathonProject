import tempfile
from pathlib import Path

import pytest

from backend.app.services import delivery, store as store_module


@pytest.fixture(autouse=True)
def isolated_store(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        test_store = store_module.MemoryStore(storage_path=Path(tmp) / "store.json")
        monkeypatch.setattr(store_module, "STORE", test_store)
        monkeypatch.setattr(delivery, "STORE", test_store)
        yield test_store


def _valid_payload(**overrides):
    payload = {
        "address": {
            "lat": 25.033, "lng": 121.565,
            "city": "台北市", "area": "大安區", "street": "忠孝東路四段100號",
            "remark": "", "contact_name": "王小明",
        },
        "goods": [{"id": "item-001", "title": "招牌雞腿便當", "price": 110, "quantity": 1}],
        "store_id": "store-001",
    }
    payload.update(overrides)
    return payload


def test_create_delivery_order_amounts_are_not_floats():
    """Real DynamoDB rejects native Python float values ("Float types are not
    supported. Use Decimal types instead.") on put_item — this regression
    guard catches a reintroduced float() cast on shipping_fee/amount fields
    before it reaches production, since the MemoryStore used in tests
    doesn't itself enforce this DynamoDB-specific constraint.
    """
    result = delivery.create_delivery_order("user-1", _valid_payload())
    assert result["success"] is True

    order = delivery.get_delivery_order("user-1", result["request_id"])
    assert not isinstance(order["original_amount"], float)
    assert not isinstance(order["shipping_fee_amount"], float)
    assert not isinstance(order["total_amount"], float)
    assert order["shipping_fee_amount"] == 60
    assert order["total_amount"] == 170


def test_create_delivery_order_amounts_are_not_floats_with_explicit_shipping_fee():
    result = delivery.create_delivery_order("user-1", _valid_payload(shipping_fee=60))
    order = delivery.get_delivery_order("user-1", result["request_id"])
    assert not isinstance(order["shipping_fee_amount"], float)
    assert not isinstance(order["total_amount"], float)
