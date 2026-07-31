import io
import json
from types import SimpleNamespace

import pytest

from backend.app.agent import tools


def test_gateway_tool_name_supports_new_health_and_shop_overrides(monkeypatch):
    monkeypatch.setattr(
        tools,
        "get_settings",
        lambda: SimpleNamespace(
            mcp_list_services_tool_name="list_services",
            mcp_get_service_schema_tool_name="get_service_schema",
            mcp_submit_service_request_tool_name="submit_service_request",
            mcp_get_page_context_tool_name="get_page_context",
            mcp_search_pages_tool_name="search_pages",
            mcp_recommend_products_by_health_need_tool_name=(
                "health-recommend___recommend_products_by_health_need"
            ),
            mcp_get_product_nutrition_tool_name="health-nutrition___get_product_nutrition",
            mcp_list_shop_stores_tool_name="shop-stores___list_shop_stores",
            mcp_get_shop_products_tool_name="shop-products___get_shop_products",
            mcp_get_user_points_tool_name="user-points___get_user_points",
        ),
    )

    assert (
        tools._gateway_tool_name("recommend_products_by_health_need")
        == "health-recommend___recommend_products_by_health_need"
    )
    assert tools._gateway_tool_name("get_product_nutrition") == "health-nutrition___get_product_nutrition"
    assert tools._gateway_tool_name("list_shop_stores") == "shop-stores___list_shop_stores"
    assert tools._gateway_tool_name("get_shop_products") == "shop-products___get_shop_products"
    assert tools._gateway_tool_name("get_user_points") == "user-points___get_user_points"


def test_invoke_lambda_supports_new_health_and_shop_function_names(monkeypatch):
    calls: list[dict] = []

    class FakeLambdaClient:
        def invoke(self, **kwargs):
            calls.append(kwargs)
            return {"Payload": io.BytesIO(b'{"success": true}')}

    monkeypatch.setattr(
        tools,
        "get_settings",
        lambda: SimpleNamespace(
            list_services_lambda_name="list-services-fn",
            get_service_schema_lambda_name="get-service-schema-fn",
            submit_service_request_lambda_name="submit-service-request-fn",
            get_page_context_lambda_name="get-page-context-fn",
            search_pages_lambda_name="search-pages-fn",
            recommend_products_by_health_need_lambda_name="recommend-products-fn",
            get_product_nutrition_lambda_name="product-nutrition-fn",
            list_shop_stores_lambda_name="list-shop-stores-fn",
            get_shop_products_lambda_name="get-shop-products-fn",
            get_user_points_lambda_name="get-user-points-fn",
        ),
    )
    monkeypatch.setattr(tools, "get_aws_client", lambda service_name: FakeLambdaClient())

    assert tools._invoke_lambda("recommend_products_by_health_need", {"query": "low sodium"})["success"] is True
    assert tools._invoke_lambda("get_product_nutrition", {"product_id": "P001"})["success"] is True
    assert tools._invoke_lambda("list_shop_stores", {})["success"] is True
    assert tools._invoke_lambda("get_shop_products", {"store_id": "store-001"})["success"] is True
    assert tools._invoke_lambda("get_user_points", {"actor_id": "user-1"})["success"] is True

    assert [call["FunctionName"] for call in calls] == [
        "recommend-products-fn",
        "product-nutrition-fn",
        "list-shop-stores-fn",
        "get-shop-products-fn",
        "get-user-points-fn",
    ]
    last_payload = json.loads(calls[-1]["Payload"].decode("utf-8"))
    assert last_payload["requestContext"]["identity"]["actorId"] == "user-1"
