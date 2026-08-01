from backend.app.services import health_catalog, health_recommendation


def test_cold_relief_products_exist_in_catalog():
    products = health_catalog.list_products()
    ids = {p["id"] for p in products}
    assert {"P039", "P040", "P041", "P042"} <= ids


def test_throat_lozenge_product_has_expected_tags():
    product = health_catalog.get_product("P039")
    assert product["name"] == "無糖喉糖"
    assert "喉嚨不適" in product["tags"]


def test_fallback_recommend_matches_cough_query_to_cold_products():
    products = health_catalog.list_products()
    recs = health_recommendation.fallback_recommend("我一直咳嗽，喉嚨很癢", products)
    matched_ids = {r["product_id"] for r in recs}
    assert matched_ids & {"P039", "P040", "P041", "P042"}
