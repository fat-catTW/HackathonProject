"""Tests for cross-vendor price comparison: service registration, the embedded
compare_product_prices tool, and the agent's chat interception."""
from unittest.mock import patch

from backend.app.agent import agent, tools
from backend.app.services import catalog


def test_shop_price_compare_registered_in_service_list():
    services = catalog.list_services()
    ids = [s["id"] for s in services]
    assert "shop_price_compare" in ids


def test_shop_price_compare_schema_has_single_query_field():
    schema = catalog.get_service_schema("shop_price_compare")
    field_ids = [f["id"] for f in schema["fields"]]
    assert field_ids == ["query"]


def test_embedded_compare_tool_requires_query():
    result = tools.call("compare_product_prices", {"query": ""})
    assert result["success"] is False
    assert result["error"]["code"] == "INVALID_QUERY"


def test_embedded_compare_tool_returns_offers_sorted_ascending():
    result = tools.call("compare_product_prices", {"query": "維他命C發泡錠"})
    assert result["success"] is True
    assert result["group_id"] == "cmp_vitamin_c"
    assert result["product_name"] == "維他命C發泡錠"
    prices = [o["unit_price"] for o in result["offers"]]
    assert prices == sorted(prices)
    assert prices[0] == 239


def test_embedded_compare_tool_not_found():
    result = tools.call("compare_product_prices", {"query": "完全不相關的字串xyz"})
    assert result["success"] is False
    assert result["error"]["code"] == "PRODUCT_NOT_FOUND"


def test_agent_detects_price_compare_and_replies_with_redirect():
    state = agent.new_state()

    with patch(
        "backend.app.agent.agent._available_services",
        return_value=[
            {
                "id": "shop_price_compare",
                "name": "商品比價",
                "description": "說出想比價的商品名稱，馬上看到各店家價格",
            }
        ],
    ):
        result = agent.handle_message("user-1", "sess-1", state, "我想比價維他命C發泡錠")

    assert result["state"]["service_id"] is None
    assert result["state"]["request_id"] is None
    assert result["redirect_path"] == "/services/shop_purchase?compare=cmp_vitamin_c"
    assert result["redirect_requires_confirmation"] is True
    assert "健康藥妝" in result["reply"] or "樂活保健" in result["reply"]
    assert "最便宜" in result["reply"]


def test_agent_detects_natural_compare_phrasing_with_product_name_in_the_middle():
    """Regression test: "我想比較X的價格" splits 比較 and 價格 with the product
    name, so it never contains the contiguous "比較價格"/"比價" keyword
    substrings. Manual testing against the live agent showed this natural
    phrasing fell through to a generic "not understood" reply instead of
    triggering shop_price_compare."""
    state = agent.new_state()

    with patch(
        "backend.app.agent.agent._available_services",
        return_value=[
            {
                "id": "shop_price_compare",
                "name": "商品比價",
                "description": "說出想比價的商品名稱，馬上看到各店家價格",
            }
        ],
    ):
        result = agent.handle_message("user-1", "sess-1", state, "我想比較維他命C的價格")

    assert result["redirect_path"] == "/services/shop_purchase?compare=cmp_vitamin_c"
    assert "最便宜" in result["reply"]


def test_embedded_compare_tool_matches_colloquial_short_product_name():
    """Regression test: querying with just the leading noun ("維他命C")
    instead of the full product name ("維他命C發泡錠") previously fell
    through to PRODUCT_NOT_FOUND even though intent detection succeeded."""
    result = tools.call("compare_product_prices", {"query": "維他命C比價"})
    assert result["success"] is True
    assert result["group_id"] == "cmp_vitamin_c"


def test_every_service_entry_has_a_keywords_list():
    """Regression test: customer_support previously had no "keywords" key,
    which crashed nlu.detect_service's unguarded `for kw in s["keywords"]`
    for every service whenever a message reached that fallback path."""
    for service in catalog.SERVICES:
        assert isinstance(service.get("keywords"), list), (
            f"{service['id']} is missing a keywords list; "
            "nlu.detect_service iterates every enabled service's keywords unconditionally"
        )


def test_agent_price_compare_not_found_has_no_redirect():
    state = agent.new_state()

    with patch(
        "backend.app.agent.agent._available_services",
        return_value=[
            {
                "id": "shop_price_compare",
                "name": "商品比價",
                "description": "說出想比價的商品名稱，馬上看到各店家價格",
            }
        ],
    ):
        result = agent.handle_message("user-1", "sess-1", state, "我想比價完全不相關的字串xyz")

    assert result["redirect_path"] is None
    assert result["redirect_requires_confirmation"] is False
    assert result["state"]["service_id"] is None
