from backend.app.agent.agent import _normalize_field_value
from backend.app.agent.page_catalog import search_pages
from backend.app.agent.page_help import answer_page_question, looks_like_page_question


def test_quantity_rejects_decimal_text_value():
    field = {"id": "quantity", "type": "number"}
    assert _normalize_field_value(field, "0.1", "是0.1台沒錯") is None


def test_quantity_accepts_integer_text_value():
    field = {"id": "quantity", "type": "number"}
    assert _normalize_field_value(field, "2", "是2台沒錯") == 2


def test_page_question_detects_navigation_for_service_application():
    assert looks_like_page_question("我可以去哪裡申請居家清潔?", current_page_id="assistant")


def test_page_search_prioritizes_air_conditioner_form_for_application_navigation():
    matches = search_pages("我要去哪裡申請冷氣清潔?", current_page_id="assistant")
    assert matches
    assert matches[0]["page_id"] == "service_form_air_conditioner_cleaning"


def test_page_help_formats_service_application_steps():
    matches = search_pages("我要去哪裡申請冷氣清潔?", current_page_id="assistant")
    reply = answer_page_question(
        "我要去哪裡申請冷氣清潔?",
        current_page_id="assistant",
        tool_payload={"success": True, "matches": matches},
    )
    assert reply is not None
    assert "服務首頁" in reply
    assert "冷氣清潔表單" in reply
