from unittest.mock import patch

from backend.app.agent import agent as agent_module
from backend.app.agent.page_catalog import search_pages
from backend.app.agent.page_help import answer_page_question


def test_home_order_navigation_prefers_my_services_over_home_summary():
    query = "我要從哪裡看我已經下訂的服務"
    matches = search_pages(query, current_page_id="home")
    assert matches
    assert matches[0]["page_id"] == "my_services"

    with patch(
        "backend.app.agent.agent._safe_memory_snapshot",
        return_value={
            "preferences": {
                "last_address": "桃園市中壢區",
                "last_phone": "0912345678",
            },
            "long_term_memory": {
                "last_service_name": "水電修繕",
                "last_request_summary": "馬桶壞掉了",
            },
        },
    ), patch(
        "backend.app.agent.agent._available_services",
        return_value=[
            {"id": "plumbing_repair", "name": "水電維修", "description": "到府修繕服務"},
        ],
    ):
        result = agent_module.handle_message(
            "user-1",
            "sess-1",
            agent_module.new_state(),
            query,
            current_page_id="home",
        )

    assert "我的服務" in result["reply"]
    assert "服務首頁" not in result["reply"]
    assert "你上次申請的服務是" not in result["reply"]


def test_page_help_search_reply_does_not_expose_internal_matching_reasons():
    query = "我要從哪裡看我已經下訂的服務"
    matches = search_pages(query, current_page_id="home")
    reply = answer_page_question(
        query,
        current_page_id="home",
        tool_payload={"success": True, "matches": matches},
    )

    assert reply is not None
    assert "我的服務" in reply
    assert "我會這樣判斷" not in reply
    assert "matched keyword" not in reply
