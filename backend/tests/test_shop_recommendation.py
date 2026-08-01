from unittest.mock import patch

from backend.app.agent import llm


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
