from backend.app.agent import agent as agent_module
from backend.app.agent.agent import _extract_fields, _normalize_field_value, _recompute_missing
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


def test_page_help_supports_voice_filling_on_home_page():
    reply = answer_page_question(
        "我想要用這邊的語音來填打",
        current_page_id="home",
    )
    assert reply is not None
    assert "支援" in reply
    assert "語音" in reply
    assert "不支援" not in reply


def test_page_help_supports_switching_service_form_to_voice_filling():
    reply = answer_page_question(
        "我想要用語音來填",
        current_page_id="service_form_air_conditioner_cleaning",
    )
    assert reply is not None
    assert "冷氣清潔表單" in reply
    assert "語音" in reply
    assert "不支援" not in reply


def test_extract_fields_allows_updating_existing_value(monkeypatch):
    state = {
        "service_id": "home_cleaning",
        "service_name": "居家清潔",
        "service_schema": {
            "fields": [
                {
                    "id": "preferred_time_slot",
                    "label": "服務時間",
                    "type": "time",
                    "required": True,
                    "minValue": "08:30",
                    "maxValue": "18:00",
                    "step": 300,
                }
            ]
        },
        "collected_fields": {"preferred_time_slot": "14:00"},
        "missing_fields": [],
        "status": "COLLECTING_INFORMATION",
        "request_id": None,
    }

    monkeypatch.setattr(
        agent_module.llm,
        "extract_fields",
        lambda **kwargs: {"preferred_time_slot": "15:00"},
    )

    found = _extract_fields("user-1", state, "服務時間改成 15:00", events=[])
    assert found == {"preferred_time_slot": "15:00"}


def test_recompute_missing_skips_fields_hidden_by_visible_when():
    state = {
        "service_schema": {
            "fields": [
                {"id": "pickup_method", "type": "select", "required": True},
                {
                    "id": "sender_store",
                    "type": "text",
                    "required": True,
                    "visibleWhen": {"fieldId": "pickup_method", "value": "STORE_TO_STORE"},
                },
                {
                    "id": "sender_address",
                    "type": "address",
                    "required": True,
                    "visibleWhen": {"fieldId": "pickup_method", "value": "HOME_PICKUP"},
                },
            ]
        },
        "collected_fields": {"pickup_method": "HOME_PICKUP"},
    }

    _recompute_missing(state)

    assert state["missing_fields"] == ["sender_address"]


def test_normalize_field_value_parses_address_type_by_type_not_field_id():
    field = {"id": "receiver_address", "type": "address", "required": True}
    noisy_text = "地址是台北市信義區松仁路100號沒錯"
    result = _normalize_field_value(field, noisy_text, noisy_text)
    assert result == "台北市信義區松仁路100號"
