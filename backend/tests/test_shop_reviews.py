from backend.app.services import shop_catalog, shop_reviews


def test_every_catalog_product_has_at_least_one_review():
    for product in shop_catalog.SHOP_PRODUCTS:
        reviews = shop_reviews.list_reviews(product["id"])
        assert len(reviews) >= 1, f"{product['id']} has no reviews"


def test_list_reviews_returns_expected_shape():
    reviews = shop_reviews.list_reviews("prod_mic_fifine_k669b")
    assert len(reviews) >= 3
    for review in reviews:
        assert {"review_id", "author", "rating", "comment", "created_at", "verified_purchase"} <= set(review.keys())
        assert 1 <= review["rating"] <= 5


def test_list_reviews_unknown_product_returns_empty_list():
    assert shop_reviews.list_reviews("does_not_exist") == []


def test_get_rating_summary_computes_average_and_count():
    summary = shop_reviews.get_rating_summary("prod_mic_fifine_k669b")
    reviews = shop_reviews.list_reviews("prod_mic_fifine_k669b")
    expected_avg = round(sum(r["rating"] for r in reviews) / len(reviews), 1)
    assert summary == {"rating_avg": expected_avg, "rating_count": len(reviews)}


def test_get_rating_summary_unknown_product_returns_zero():
    assert shop_reviews.get_rating_summary("does_not_exist") == {"rating_avg": 0.0, "rating_count": 0}


def test_review_ids_are_globally_unique():
    all_ids = [
        review["review_id"]
        for reviews in shop_reviews.SHOP_REVIEWS.values()
        for review in reviews
    ]
    assert len(all_ids) == len(set(all_ids))
