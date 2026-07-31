import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from get_shop_products.handler import lambda_handler


def test_lambda_handler_filters_by_store_id():
    result = lambda_handler({"store_id": "store_711_taipei"}, None)
    assert result["success"] is True
    assert result["products"]
    assert all(p["store_id"] == "store_711_taipei" for p in result["products"])


def test_lambda_handler_returns_all_products_without_filter():
    result = lambda_handler({}, None)
    assert result["success"] is True
    assert len(result["products"]) == 19
