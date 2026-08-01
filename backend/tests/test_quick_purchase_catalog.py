from backend.app.services import quick_purchase_catalog, shop_catalog


def test_match_bundle_finds_fruit_offering_by_keyword():
    bundle = quick_purchase_catalog.match_bundle("幫我買拜拜用的水果")
    assert bundle is not None
    assert bundle["sku_id"] == "sku_fruit_offering_set"


def test_match_bundle_finds_three_sacrifice_by_keyword():
    bundle = quick_purchase_catalog.match_bundle("要準備三牲")
    assert bundle is not None
    assert bundle["sku_id"] == "sku_three_sacrifice_set"


def test_match_bundle_returns_none_for_unrelated_query():
    assert quick_purchase_catalog.match_bundle("我要一台洗衣機") is None


def test_quick_purchase_skus_resolve_in_shop_catalog():
    for sku_id in ("sku_fruit_offering_set", "sku_three_sacrifice_set"):
        resolved = shop_catalog.get_sku(sku_id)
        assert resolved is not None
        product, sku = resolved
        assert product["category_id"] == "cat_offering"
        assert product["product_type"] == "PHYSICAL"
        assert sku["unit_price"] > 0
