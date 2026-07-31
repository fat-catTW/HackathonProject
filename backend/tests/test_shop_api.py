from fastapi.testclient import TestClient

from backend.app.main import app


def test_list_shop_categories_returns_all_categories():
    client = TestClient(app)
    response = client.get("/api/shop/categories")
    assert response.status_code == 200
    categories = response.json()["categories"]
    assert len(categories) >= 5
    assert all({"id", "name"} <= set(c.keys()) for c in categories)


def test_list_shop_products_filtered_by_category_id():
    client = TestClient(app)
    all_products = client.get("/api/shop/products").json()["products"]
    category_id = all_products[0]["category_id"]

    response = client.get(f"/api/shop/products?category_id={category_id}")
    assert response.status_code == 200
    filtered = response.json()["products"]
    assert filtered
    assert all(p["category_id"] == category_id for p in filtered)
    assert all("store_name" in p for p in filtered)


def test_list_shop_products_filtered_by_store_id_still_works():
    client = TestClient(app)
    all_products = client.get("/api/shop/products").json()["products"]
    store_id = all_products[0]["store_id"]

    response = client.get(f"/api/shop/products?store_id={store_id}")
    assert response.status_code == 200
    filtered = response.json()["products"]
    assert filtered
    assert all(p["store_id"] == store_id for p in filtered)


def test_get_shop_compare_group_returns_offers_sorted_by_price():
    client = TestClient(app)
    response = client.get("/api/shop/compare/cmp_vitamin_c")
    assert response.status_code == 200
    body = response.json()
    assert body["group_id"] == "cmp_vitamin_c"
    assert body["category_id"] == "cat_health"
    offers = body["offers"]
    assert len(offers) == 3
    prices = [o["min_unit_price"] for o in offers]
    assert prices == sorted(prices)


def test_get_shop_compare_group_unknown_id_returns_404():
    client = TestClient(app)
    response = client.get("/api/shop/compare/does_not_exist")
    assert response.status_code == 404
    assert response.json()["detail"]["error"]["code"] == "COMPARE_GROUP_NOT_FOUND"
