from unittest.mock import patch

from backend.app.agent import llm
from backend.app.services import shop_catalog, shop_recommendation


def _electronics_products():
    return shop_catalog.list_products(category_id="cat_electronics")


def test_recommend_shop_products_returns_none_without_bedrock_credentials():
    """No AWS credentials are configured in the test env (see backend/.env.example
    defaults), so llm._get_client() returns None and this must return None,
    exactly like every other llm.py function's no-client fallback."""
    products = [
        {"id": "prod_mic_fifine_k669b", "name": "FIFINE K669B USB 電容式麥克風", "tags": ["麥克風", "podcast"]},
    ]
    assert llm.recommend_shop_products("我想要錄podcast用的麥克風", products) is None


def test_recommend_shop_products_maps_llm_recommendations_to_full_product_dicts():
    products = [
        {"id": "prod_a", "name": "A 商品", "tags": []},
        {"id": "prod_b", "name": "B 商品", "tags": []},
    ]
    with patch(
        "backend.app.agent.llm._converse_json",
        return_value={"recommendations": [{"product_id": "prod_b", "reason": "比較適合"}]},
    ):
        result = llm.recommend_shop_products("隨便問問", products)
    assert result == [{"id": "prod_b", "name": "B 商品", "tags": [], "reason": "比較適合"}]


def test_recommend_shop_products_ignores_unknown_product_ids_from_llm():
    products = [{"id": "prod_a", "name": "A 商品", "tags": []}]
    with patch(
        "backend.app.agent.llm._converse_json",
        return_value={"recommendations": [{"product_id": "does_not_exist", "reason": "x"}]},
    ):
        result = llm.recommend_shop_products("隨便問問", products)
    assert result is None


def test_fallback_recommend_matches_by_tag_keyword():
    recs = shop_recommendation.fallback_recommend("我想要錄podcast用的麥克風", _electronics_products())
    assert len(recs) > 0
    assert all("麥克風" in rec.get("tags", []) or "podcast" in rec.get("tags", []) for rec in recs)


def test_fallback_recommend_falls_back_to_top_rated_when_no_match():
    products = _electronics_products()
    recs = shop_recommendation.fallback_recommend("完全不相關的字串xyz", products)
    assert len(recs) == min(5, len(products))
    ratings = [rec["rating_avg"] for rec in recs]
    assert ratings == sorted(ratings, reverse=True)


def test_fallback_recommend_includes_a_reason_string():
    recs = shop_recommendation.fallback_recommend("麥克風", _electronics_products())
    assert all(rec["reason"] for rec in recs)


def test_recommend_uses_llm_result_when_available():
    products = [{"id": "prod_a", "name": "A 商品", "tags": [], "rating_avg": 4.5, "rating_count": 10}]
    with patch(
        "backend.app.services.shop_recommendation.llm.recommend_shop_products",
        return_value=[{**products[0], "reason": "LLM 理由"}],
    ):
        result = shop_recommendation.recommend("query", products)
    assert result["fallback_used"] is False
    assert result["recommendations"] == [{**products[0], "reason": "LLM 理由"}]


def test_recommend_falls_back_when_llm_unavailable():
    products = _electronics_products()
    with patch("backend.app.services.shop_recommendation.llm.recommend_shop_products", return_value=None):
        result = shop_recommendation.recommend("我想要錄podcast用的麥克風", products)
    assert result["fallback_used"] is True
    assert len(result["recommendations"]) > 0
