"""Tests for the health product recommendation feature: catalog, service schema,
NLU/agent intent routing, embedded tool handlers, and the keyword fallback path."""
from unittest.mock import patch

from backend.app.agent import agent, tools
from backend.app.services import catalog, health_catalog, health_recommendation


def test_health_product_recommendation_registered_in_service_list():
    services = catalog.list_services()
    ids = [s["id"] for s in services]
    assert "health_product_recommendation" in ids


def test_health_product_recommendation_schema_has_single_query_field():
    schema = catalog.get_service_schema("health_product_recommendation")
    field_ids = [f["id"] for f in schema["fields"]]
    assert field_ids == ["query"]


def test_list_products_returns_38_static_products_without_dynamodb():
    products = health_catalog.list_products()
    assert len(products) == 38
    assert any(p["id"] == "P001" and p["name"] == "雞胸沙拉" for p in products)


def test_get_product_returns_none_for_unknown_id():
    assert health_catalog.get_product("P999") is None


def test_get_product_returns_expected_fields_for_known_id():
    product = health_catalog.get_product("P001")
    assert product["name"] == "雞胸沙拉"
    assert product["calories"] == 210
    assert "高蛋白" in product["tags"]


def test_fallback_recommend_matches_by_health_keyword():
    products = health_catalog.list_products()
    recs = health_recommendation.fallback_recommend("我想減脂", products)
    assert len(recs) > 0
    assert all(rec["product_id"] for rec in recs)


def test_fallback_recommend_excludes_unhealthy_tags_when_nothing_matches():
    products = health_catalog.list_products()
    recs = health_recommendation.fallback_recommend("完全不相關的字串xyz", products)
    matched_ids = {rec["product_id"] for rec in recs}
    unhealthy_ids = {
        p["id"] for p in products if any(tag in health_recommendation.UNHEALTHY_TAGS for tag in p["tags"])
    }
    assert not (matched_ids & unhealthy_ids)


def test_recommend_falls_back_to_keyword_matching_without_bedrock_or_google():
    """Neither Bedrock nor a Google key is configured in the test env, so
    recommend() must use the rule-based fallback and mark fallback_used=True."""
    result = health_recommendation.recommend("我想減脂", health_catalog.list_products())
    assert result["fallback_used"] is True
    assert len(result["recommendations"]) > 0


def test_recommend_uses_bedrock_and_google_when_available():
    products = health_catalog.list_products()[:2]
    fake_external = [{"title": "外部商品A", "snippet": "低卡高蛋白", "link": "https://example.com/a"}]
    fake_picks = [
        {"product_id": products[0]["id"], "name": products[0]["name"], "source": "internal",
         "detail": "x", "reason": "符合減脂需求"},
    ]
    with patch("backend.app.services.health_recommendation.llm.is_available", return_value=True), \
         patch("backend.app.services.health_recommendation.llm.plan_external_query", return_value="低卡商品"), \
         patch("backend.app.services.health_recommendation.external_search.google_text_search", return_value=fake_external), \
         patch("backend.app.services.health_recommendation.llm.rank_external_results", return_value=fake_picks):
        result = health_recommendation.recommend("我想減脂", products)

    assert result["fallback_used"] is False
    assert result["recommendations"][0]["product_id"] == products[0]["id"]
    assert result["recommendations"][0]["reason"] == "符合減脂需求"
    assert result["recommendations"][0]["source"] == "internal"


def test_recommend_falls_back_when_bedrock_ranking_returns_nothing():
    products = health_catalog.list_products()[:2]
    with patch("backend.app.services.health_recommendation.llm.is_available", return_value=True), \
         patch("backend.app.services.health_recommendation.llm.plan_external_query", return_value="q"), \
         patch("backend.app.services.health_recommendation.external_search.google_text_search", return_value=None), \
         patch("backend.app.services.health_recommendation.llm.rank_external_results", return_value=None):
        result = health_recommendation.recommend("我想減脂", products)
    assert result["fallback_used"] is True


def test_embedded_recommend_tool_requires_query():
    result = tools.call("recommend_products_by_health_need", {"query": ""})
    assert result["success"] is False
    assert result["error"]["code"] == "INVALID_QUERY"


def test_embedded_recommend_tool_returns_recommendations():
    result = tools.call("recommend_products_by_health_need", {"query": "我想增肌"})
    assert result["success"] is True
    assert isinstance(result["recommendations"], list)


def test_embedded_get_product_nutrition_tool_not_found():
    result = tools.call("get_product_nutrition", {"product_id": "P999"})
    assert result["success"] is False
    assert result["error"]["code"] == "PRODUCT_NOT_FOUND"


def test_embedded_get_product_nutrition_tool_returns_product():
    result = tools.call("get_product_nutrition", {"product_id": "P001"})
    assert result["success"] is True
    assert result["name"] == "雞胸沙拉"


def test_agent_detects_health_service_and_answers_without_creating_a_case():
    """health_product_recommendation is a query-and-answer service: the agent
    must answer directly and reset service_id, never setting request_id."""
    state = agent.new_state()

    with patch(
        "backend.app.agent.agent._available_services",
        return_value=[
            {
                "id": "health_product_recommendation",
                "name": "健康商品推薦",
                "description": "說出健康或飲食需求，推薦適合的 7-11 商品",
                "keywords": ["健康", "減脂", "增肌", "商品", "推薦"],
            }
        ],
    ):
        result = agent.handle_message("user-1", "sess-1", state, "我在減脂，有推薦的商品嗎？")

    state = result["state"]
    assert state["service_id"] is None
    assert state["request_id"] is None
    assert state["health_last_recommendations"]
    assert "推薦" in result["reply"]


def test_agent_health_followup_answers_nutrition_for_named_product():
    """After a recommendation reply, naming one of the recommended products
    by name should answer with nutrition info instead of restarting intent
    detection."""
    state = agent.new_state()
    state["health_last_recommendations"] = [
        {"product_id": "P001", "name": "雞胸沙拉", "reason": "高蛋白低碳", "match_tags": ["高蛋白"]},
    ]

    result = agent.handle_message("user-1", "sess-1", state, "雞胸沙拉的營養資訊是什麼？")

    assert "熱量" in result["reply"]
    assert result["state"]["request_id"] is None
