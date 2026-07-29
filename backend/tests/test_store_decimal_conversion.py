from decimal import Decimal

from backend.app.services.store import convert_floats_to_decimal


def test_converts_top_level_float_to_decimal():
    assert convert_floats_to_decimal(25.033) == Decimal("25.033")
    assert isinstance(convert_floats_to_decimal(25.033), Decimal)


def test_leaves_int_and_str_unchanged():
    assert convert_floats_to_decimal(60) == 60
    assert isinstance(convert_floats_to_decimal(60), int)
    assert convert_floats_to_decimal("台北市") == "台北市"


def test_converts_floats_nested_in_dicts():
    result = convert_floats_to_decimal({"lat": 25.033, "lng": 121.565, "city": "台北市"})
    assert result == {"lat": Decimal("25.033"), "lng": Decimal("121.565"), "city": "台北市"}


def test_converts_floats_nested_in_lists_of_dicts():
    result = convert_floats_to_decimal([
        {"id": "item-001", "title": "招牌雞腿便當", "price": 110, "quantity": 1},
        {"id": "item-002", "title": "排骨便當", "price": 100.5, "quantity": 2},
    ])
    assert result[0]["price"] == 110
    assert isinstance(result[0]["price"], int)
    assert result[1]["price"] == Decimal("100.5")


def test_converts_floats_in_deeply_nested_structure():
    order = {
        "order_items": {
            "user": {"address": {"lat": 25.033, "lng": 121.565}},
            "goods": [{"price": 110}],
        },
        "total_amount": 170,
    }
    result = convert_floats_to_decimal(order)
    assert result["order_items"]["user"]["address"]["lat"] == Decimal("25.033")
    assert result["order_items"]["goods"][0]["price"] == 110
    assert result["total_amount"] == 170
