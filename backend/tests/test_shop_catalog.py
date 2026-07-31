import pytest

from backend.app.services import shop_catalog


def test_list_stores_returns_all_stores():
    stores = shop_catalog.list_stores()
    assert len(stores) >= 2
    assert all({"id", "name", "category"} <= set(s.keys()) for s in stores)


def test_get_store_found_and_not_found():
    store = shop_catalog.list_stores()[0]
    assert shop_catalog.get_store(store["id"]) == store
    assert shop_catalog.get_store("does_not_exist") is None


def test_list_products_all_and_filtered_by_store():
    all_products = shop_catalog.list_products()
    assert len(all_products) >= 3
    store_id = all_products[0]["store_id"]
    filtered = shop_catalog.list_products(store_id=store_id)
    assert filtered
    assert all(p["store_id"] == store_id for p in filtered)


def test_every_product_belongs_to_a_real_store():
    store_ids = {s["id"] for s in shop_catalog.list_stores()}
    for product in shop_catalog.list_products():
        assert product["store_id"] in store_ids


def test_every_product_has_at_least_one_sku_and_valid_product_type():
    for product in shop_catalog.list_products():
        assert product["product_type"] in ("PHYSICAL", "SERIAL_CODE")
        assert len(product["skus"]) >= 1
        for sku in product["skus"]:
            assert sku["unit_price"] > 0
            assert sku["unit_points"] >= 0


def test_sku_ids_are_globally_unique():
    sku_ids = [sku["sku_id"] for product in shop_catalog.list_products() for sku in product["skus"]]
    assert len(sku_ids) == len(set(sku_ids))


def test_get_sku_returns_product_and_sku_pair():
    product = shop_catalog.list_products()[0]
    sku = product["skus"][0]
    result = shop_catalog.get_sku(sku["sku_id"])
    assert result is not None
    found_product, found_sku = result
    assert found_product["id"] == product["id"]
    assert found_sku["sku_id"] == sku["sku_id"]


def test_get_sku_not_found_returns_none():
    assert shop_catalog.get_sku("does_not_exist") is None


def test_physical_products_have_specs_matching_sku_attribute_keys():
    for product in shop_catalog.list_products():
        if product["product_type"] != "PHYSICAL" or not product["specs"]:
            continue
        spec_names = {spec["name"] for spec in product["specs"]}
        for sku in product["skus"]:
            assert set(sku["attributes"].keys()) == spec_names


def test_list_categories_returns_all_categories():
    categories = shop_catalog.list_categories()
    assert len(categories) >= 5
    assert all({"id", "name"} <= set(c.keys()) for c in categories)


def test_every_product_has_a_valid_category_id():
    category_ids = {c["id"] for c in shop_catalog.list_categories()}
    for product in shop_catalog.list_products():
        assert product["category_id"] in category_ids


def test_each_category_has_at_least_two_distinct_vendors():
    products = shop_catalog.list_products()
    for category in shop_catalog.list_categories():
        store_ids = {p["store_id"] for p in products if p["category_id"] == category["id"]}
        assert len(store_ids) >= 2, f"{category['id']} 底下廠商不足兩家"


def test_list_products_filtered_by_category():
    all_products = shop_catalog.list_products()
    category_id = all_products[0]["category_id"]
    filtered = shop_catalog.list_products(category_id=category_id)
    assert filtered
    assert all(p["category_id"] == category_id for p in filtered)


def test_list_products_includes_store_name():
    product = shop_catalog.list_products()[0]
    store = shop_catalog.get_store(product["store_id"])
    assert product["store_name"] == store["name"]


def test_list_products_rejects_positional_arguments():
    with pytest.raises(TypeError):
        shop_catalog.list_products("some_id")


def test_list_compare_offers_sorted_by_price_ascending():
    offers = shop_catalog.list_compare_offers("cmp_vitamin_c")
    assert len(offers) == 3
    prices = [o["min_unit_price"] for o in offers]
    assert prices == sorted(prices)
    assert prices[0] == 239


def test_list_compare_offers_unknown_group_returns_empty_list():
    assert shop_catalog.list_compare_offers("does_not_exist") == []


def test_list_compare_offers_includes_store_name():
    offers = shop_catalog.list_compare_offers("cmp_clean_spray")
    assert all(o["store_name"] for o in offers)


def test_find_compare_group_id_by_query_matches_partial_name():
    assert shop_catalog.find_compare_group_id_by_query("維他命C") == "cmp_vitamin_c"
    assert shop_catalog.find_compare_group_id_by_query("我想比較維他命C發泡錠的價格") == "cmp_vitamin_c"


def test_find_compare_group_id_by_query_no_match_returns_none():
    assert shop_catalog.find_compare_group_id_by_query("完全不相關的字串xyz") is None


def test_find_compare_group_id_by_query_ignores_products_without_a_group():
    assert shop_catalog.find_compare_group_id_by_query("御飯糰任選兌換券") is None


def test_products_without_compare_group_id_report_none():
    products = shop_catalog.list_products()
    ungrouped = next(p for p in products if p["id"] == "prod_daiso_storage_box")
    assert ungrouped["compare_group_id"] is None


def test_three_categories_each_have_one_comparison_group_of_three_vendors():
    for group_id, category_id in (
        ("cmp_vitamin_c", "cat_health"),
        ("cmp_clean_spray", "cat_cleaning"),
        ("cmp_tumbler", "cat_daily"),
    ):
        offers = shop_catalog.list_compare_offers(group_id)
        assert len(offers) == 3
        assert all(o["category_id"] == category_id for o in offers)
        assert len({o["store_id"] for o in offers}) == 3
