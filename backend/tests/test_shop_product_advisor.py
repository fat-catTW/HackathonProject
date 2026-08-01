"""Tests for the AI shop product advisor: service registration, the embedded
recommend_shop_products_by_need tool, and the agent's chat interception."""
from unittest.mock import patch

from backend.app.agent import agent, tools
from backend.app.services import catalog


def test_shop_product_advisor_registered_in_service_list():
    services = catalog.list_services()
    ids = [s["id"] for s in services]
    assert "shop_product_advisor" in ids


def test_shop_product_advisor_schema_has_single_query_field():
    schema = catalog.get_service_schema("shop_product_advisor")
    field_ids = [f["id"] for f in schema["fields"]]
    assert field_ids == ["query"]


def test_embedded_shop_advisor_tool_requires_query():
    result = tools.call("recommend_shop_products_by_need", {"query": ""})
    assert result["success"] is False
    assert result["error"]["code"] == "INVALID_QUERY"


def test_embedded_shop_advisor_tool_returns_recommendations_for_mic_query():
    result = tools.call("recommend_shop_products_by_need", {"query": "我想要錄podcast用的麥克風"})
    assert result["success"] is True
    assert isinstance(result["recommendations"], list)
    assert len(result["recommendations"]) > 0
    assert any("麥克風" in rec["name"] for rec in result["recommendations"])


def test_agent_detects_shop_product_advisor_and_replies_with_redirect():
    state = agent.new_state()

    with patch(
        "backend.app.agent.agent._available_services",
        return_value=[
            {
                "id": "shop_product_advisor",
                "name": "AI 選購顧問",
                "description": "說出你的使用情境或想要的商品，AI 幫你比較不同品牌、參考評分與評價推薦",
                "keywords": ["推薦", "選購", "麥克風"],
            }
        ],
    ):
        result = agent.handle_message("user-1", "sess-1", state, "我想要錄podcast用的麥克風，可以推薦一下嗎")

    assert result["state"]["service_id"] is None
    assert result["state"]["request_id"] is None
    assert result["redirect_path"] == "/services/shop_purchase?category_id=cat_electronics"
    assert result["redirect_requires_confirmation"] is True
    assert "★" in result["reply"]


def test_agent_shop_product_advisor_tool_failure_has_no_redirect():
    state = agent.new_state()

    with patch(
        "backend.app.agent.agent._available_services",
        return_value=[
            {
                "id": "shop_product_advisor",
                "name": "AI 選購顧問",
                "description": "說出你的使用情境或想要的商品，AI 幫你比較不同品牌、參考評分與評價推薦",
                "keywords": ["推薦", "選購", "麥克風"],
            }
        ],
    ), patch(
        "backend.app.agent.agent.tools.call",
        return_value={"success": False, "error": {"code": "INVALID_QUERY", "message": "query is required."}},
    ):
        result = agent.handle_message("user-1", "sess-1", state, "我想要錄podcast用的麥克風")

    assert result["redirect_path"] is None
    assert result["redirect_requires_confirmation"] is False
    assert "查詢失敗" in result["reply"] or "沒有成功" in result["reply"]
