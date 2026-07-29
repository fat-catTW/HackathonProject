from backend.app.services import delivery_catalog


def test_list_stores_returns_three_seed_stores():
    stores = delivery_catalog.list_stores()
    assert len(stores) == 3
    assert {s["id"] for s in stores} == {"store-001", "store-002", "store-003"}


def test_get_store_found_includes_menu():
    store = delivery_catalog.get_store("store-001")
    assert store is not None
    assert store["name"] == "好味道便當"
    assert any(item["title"] == "招牌雞腿便當" for item in store["menu"])


def test_get_store_not_found_returns_none():
    assert delivery_catalog.get_store("does-not-exist") is None
