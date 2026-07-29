from backend.app.agent import nlu


def test_parse_delivery_store_matches_full_name():
    assert nlu.parse_delivery_store("我想跟好味道便當訂餐") == "store-001"


def test_parse_delivery_store_matches_drink_shop():
    assert nlu.parse_delivery_store("鮮茶道有開嗎") == "store-002"


def test_parse_delivery_store_returns_none_when_no_match():
    assert nlu.parse_delivery_store("我想吃拉麵") is None


def test_parse_menu_item_matches_title_with_explicit_quantity():
    item = nlu.parse_menu_item("我要兩個招牌雞腿便當", "store-001")
    assert item == {"id": "item-001", "title": "招牌雞腿便當", "price": 110, "quantity": 2}


def test_parse_menu_item_defaults_quantity_to_one():
    item = nlu.parse_menu_item("排骨便當", "store-001")
    assert item == {"id": "item-002", "title": "排骨便當", "price": 100, "quantity": 1}


def test_parse_menu_item_returns_none_for_unknown_item():
    assert nlu.parse_menu_item("我要牛肉麵", "store-001") is None


def test_parse_menu_item_returns_none_for_unknown_store():
    assert nlu.parse_menu_item("排骨便當", "does-not-exist") is None
