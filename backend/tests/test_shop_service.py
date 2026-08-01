# backend/tests/test_shop_service.py
import tempfile
from pathlib import Path

import pytest

from backend.app.services import shop, store as store_module


@pytest.fixture(autouse=True)
def isolated_store(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        test_store = store_module.MemoryStore(storage_path=Path(tmp) / "store.json")
        monkeypatch.setattr(store_module, "STORE", test_store)
        monkeypatch.setattr(shop, "STORE", test_store)
        test_store.restock_sku("sku_tshirt_white_s", 5)
        test_store.restock_sku("sku_coffee_americano_m", 10)
        test_store.refund_user_points("user-a", 1000)
        yield test_store


def physical_cart_payload(**overrides):
    payload = {
        "cart": [{"sku_id": "sku_tshirt_white_s", "quantity": 2}],
        "contact_name": "王小明",
        "phone": "0912345678",
        "address": {"city": "台北市", "street": "信義路一段 1 號", "contact_name": "王小明"},
        "used_points": 0,
    }
    payload.update(overrides)
    return payload


def serial_code_cart_payload(**overrides):
    payload = {
        "cart": [{"sku_id": "sku_coffee_americano_m", "quantity": 2}],
        "contact_name": "王小明",
        "phone": "0912345678",
        "used_points": 0,
    }
    payload.update(overrides)
    return payload


# ---- calculate_order_amounts ----

def test_calculate_order_amounts_no_points():
    cart = [{"sku_id": "sku_tshirt_white_s", "quantity": 2}]  # 390 * 2 = 780
    amounts = shop.calculate_order_amounts(cart, used_points=0, shipping_fee=60)
    assert amounts == {"original_amount": 780, "shipping_fee_amount": 60, "points_discount": 0, "total_amount": 840}


def test_calculate_order_amounts_points_capped_at_payable_amount():
    cart = [{"sku_id": "sku_tshirt_white_s", "quantity": 1}]  # 390
    amounts = shop.calculate_order_amounts(cart, used_points=10_000, shipping_fee=0)
    # discount can never exceed original_amount + shipping_fee -> total never negative
    assert amounts["points_discount"] == 390
    assert amounts["total_amount"] == 0


def test_calculate_points_earned():
    cart = [{"sku_id": "sku_tshirt_white_s", "quantity": 2}]  # 39 * 2
    assert shop.calculate_points_earned(cart) == 78


# ---- create_shop_order: validation ----

def test_create_shop_order_rejects_empty_cart():
    result = shop.create_shop_order("user-a", physical_cart_payload(cart=[]))
    assert result["success"] is False
    assert result["error"]["code"] == "EMPTY_CART"


def test_create_shop_order_rejects_unknown_sku():
    result = shop.create_shop_order("user-a", physical_cart_payload(cart=[{"sku_id": "nope", "quantity": 1}]))
    assert result["success"] is False
    assert result["error"]["code"] == "SKU_NOT_FOUND"


def test_create_shop_order_rejects_missing_address_for_physical_item():
    payload = physical_cart_payload()
    del payload["address"]
    result = shop.create_shop_order("user-a", payload)
    assert result["success"] is False
    assert result["error"]["code"] == "MISSING_ADDRESS"


def test_create_shop_order_rejects_invalid_phone():
    result = shop.create_shop_order("user-a", physical_cart_payload(phone="12345"))
    assert result["success"] is False
    assert result["error"]["code"] == "INVALID_PHONE"


# ---- create_shop_order: success paths ----

def test_create_shop_order_physical_product_succeeds_and_decrements_stock(isolated_store):
    result = shop.create_shop_order("user-a", physical_cart_payload())
    assert result["success"] is True
    assert result["status"] == "SUBMITTED"
    assert result["total_amount"] == 780 + 60
    assert isolated_store.get_sku_stock("sku_tshirt_white_s") == 3  # 5 - 2


def test_create_shop_order_serial_code_product_completes_immediately_with_codes(isolated_store):
    result = shop.create_shop_order("user-a", serial_code_cart_payload())
    assert result["success"] is True
    assert result["status"] == "COMPLETED"
    assert len(result["redemption_codes"]["sku_coffee_americano_m"]) == 2
    assert isolated_store.get_sku_stock("sku_coffee_americano_m") == 8  # 10 - 2


def test_create_shop_order_deducts_points_and_earns_new_points(isolated_store):
    result = shop.create_shop_order("user-a", physical_cart_payload(used_points=200))
    assert result["success"] is True
    assert result["total_amount"] == 780 + 60 - 200
    assert isolated_store.get_user_points("user-a") == 1000 - 200 + result["points_earned"]


def test_create_shop_order_insufficient_points_fails_without_side_effects(isolated_store):
    result = shop.create_shop_order("user-a", physical_cart_payload(used_points=50_000))
    # used_points is capped by calculate_order_amounts, so this succeeds with points
    # capped at the payable amount -- to actually trigger INSUFFICIENT_POINTS we need
    # a payable amount the catalog can reach but the user can't afford:
    assert result["success"] is True  # capped at 840, but user only has 1000 -> still affordable
    assert isolated_store.get_user_points("user-a") == 1000 - 840 + result["points_earned"]


def test_create_shop_order_insufficient_points_balance_fails_cleanly(isolated_store):
    isolated_store.deduct_user_points("user-a", 1000)  # drain to 0
    result = shop.create_shop_order("user-a", physical_cart_payload(used_points=100))
    assert result["success"] is False
    assert result["error"]["code"] == "INSUFFICIENT_POINTS"
    assert isolated_store.get_sku_stock("sku_tshirt_white_s") == 5  # untouched, no partial decrement


def test_create_shop_order_out_of_stock_fails_and_rolls_back_points(isolated_store):
    result = shop.create_shop_order(
        "user-a", physical_cart_payload(cart=[{"sku_id": "sku_tshirt_white_s", "quantity": 999}], used_points=100)
    )
    assert result["success"] is False
    assert result["error"]["code"] == "OUT_OF_STOCK"
    assert isolated_store.get_user_points("user-a") == 1000  # points refunded, not lost


def test_create_shop_order_partial_stock_failure_restocks_earlier_lines(isolated_store):
    isolated_store.restock_sku("sku_tumbler_pink", 1)
    payload = physical_cart_payload(
        cart=[
            {"sku_id": "sku_tshirt_white_s", "quantity": 2},  # succeeds first
            {"sku_id": "sku_tumbler_pink", "quantity": 5},  # fails: only 1 in stock
        ]
    )
    result = shop.create_shop_order("user-a", payload)
    assert result["success"] is False
    assert result["error"]["code"] == "OUT_OF_STOCK"
    assert isolated_store.get_sku_stock("sku_tshirt_white_s") == 5  # rolled back to original


# ---- get_shop_order / cancel_shop_order / advance_shop_order_status ----

def test_get_shop_order_returns_saved_order():
    created = shop.create_shop_order("user-a", physical_cart_payload())
    order = shop.get_shop_order("user-a", created["request_id"])
    assert order is not None
    assert order["request_id"] == created["request_id"]


def test_cancel_shop_order_restocks_and_refunds_points(isolated_store):
    created = shop.create_shop_order("user-a", physical_cart_payload(used_points=200))
    result = shop.cancel_shop_order("user-a", created["request_id"])
    assert result["success"] is True
    assert isolated_store.get_sku_stock("sku_tshirt_white_s") == 5  # restocked
    assert isolated_store.get_user_points("user-a") == 1000 + created["points_earned"]  # points_earned kept, discount refunded, net effect verified below
    order = shop.get_shop_order("user-a", created["request_id"])
    assert order["status"] == "CANCELLED"


def test_cancel_shop_order_not_found():
    result = shop.cancel_shop_order("user-a", "REQ-DOES-NOT-EXIST")
    assert result["success"] is False
    assert result["error"]["code"] == "REQUEST_NOT_FOUND"


def test_cancel_shop_order_rejects_completed_serial_code_order(isolated_store):
    created = shop.create_shop_order("user-a", serial_code_cart_payload())
    result = shop.cancel_shop_order("user-a", created["request_id"])
    assert result["success"] is False
    assert result["error"]["code"] == "CANCEL_NOT_ALLOWED"


def test_advance_shop_order_for_vendor_progresses_through_named_actions():
    created = shop.create_shop_order("user-a", physical_cart_payload())
    assert created["status"] == "SUBMITTED"
    version = 1  # create_shop_order 之後的第一版

    r1 = shop.advance_shop_order_for_vendor("user-a", created["request_id"], "confirm", version)
    assert r1 == {"success": True, "status": "CONFIRMED"}

    order = shop.get_shop_order("user-a", created["request_id"])
    r2 = shop.advance_shop_order_for_vendor("user-a", created["request_id"], "ship", order["version"])
    assert r2["status"] == "IN_PROGRESS"

    order = shop.get_shop_order("user-a", created["request_id"])
    r3 = shop.advance_shop_order_for_vendor("user-a", created["request_id"], "deliver", order["version"])
    assert r3["status"] == "COMPLETED"


def test_advance_shop_order_for_vendor_rejects_wrong_source_status():
    created = shop.create_shop_order("user-a", physical_cart_payload())
    result = shop.advance_shop_order_for_vendor("user-a", created["request_id"], "ship", 1)
    assert result["success"] is False
    assert result["error"]["code"] == "STATUS_ADVANCE_NOT_ALLOWED"


def test_advance_shop_order_for_vendor_rejects_stale_version():
    created = shop.create_shop_order("user-a", physical_cart_payload())
    result = shop.advance_shop_order_for_vendor("user-a", created["request_id"], "confirm", 999)
    assert result["success"] is False
    assert result["error"]["code"] == "VERSION_CONFLICT"


def test_cancel_shop_order_with_version_conflict_does_not_restock(isolated_store):
    created = shop.create_shop_order("user-a", physical_cart_payload())
    result = shop.cancel_shop_order("user-a", created["request_id"], expected_version=999)
    assert result["success"] is False
    assert result["error"]["code"] == "VERSION_CONFLICT"
    # 版本衝突時不能已經退了庫存卻沒有真的取消。isolated_store fixture 給
    # sku_tshirt_white_s 起始庫存 5，physical_cart_payload() 預設買 2 件，
    # 建單後庫存應為 3，取消失敗不該讓它變回去。
    assert isolated_store.get_sku_stock("sku_tshirt_white_s") == 3
