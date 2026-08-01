import tempfile
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest

from backend.app.agent import agent, nlu
from backend.app.services import reservation, store as store_module


@pytest.fixture(autouse=True)
def isolated_store(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        test_store = store_module.MemoryStore(storage_path=Path(tmp) / "store.json")
        monkeypatch.setattr(store_module, "STORE", test_store)
        monkeypatch.setattr(reservation, "STORE", test_store)
        yield test_store


def _run_turn(state, message, actor_id="user-1", session_id="sess-1"):
    return agent.handle_message(actor_id, session_id, state, message)


def _fake_extract_fields(*, message, fields, collected_fields, **_kwargs):
    """Deterministic stand-in for the live Bedrock-backed llm.extract_fields.

    This environment has no reachable Bedrock endpoint, so the real
    llm.extract_fields always resolves to {}. nlu.extract_fields is the
    project's own offline/rule-based fallback (its docstring calls it out
    as the "unit test baseline"), so we reuse it here and only add the two
    reservation-only fields (contact_name, is_premium) it doesn't yet know
    about. This keeps the test exercising real routing/normalization logic
    end-to-end without depending on network access.
    """
    found = nlu.extract_fields("restaurant_reservation", fields, message, collected_fields)
    field_ids = {field["id"] for field in fields}

    if "reserved_date" in field_ids and "reserved_date" not in collected_fields and "reserved_date" not in found:
        parsed_date = nlu.parse_date(message, today=date.today())
        if parsed_date is not None:
            found["reserved_date"] = parsed_date

    if "people" in field_ids and "people" not in collected_fields and "people" not in found:
        number = nlu.parse_quantity(message, unit_chars="位人")
        if number is not None:
            found["people"] = number

    if "contact_name" in field_ids and "contact_name" not in collected_fields and "contact_name" not in found:
        stripped = message.strip()
        if 2 <= len(stripped) <= 4 and all("一" <= ch <= "鿿" for ch in stripped):
            found["contact_name"] = stripped

    if "is_premium" in field_ids and "is_premium" not in collected_fields and "is_premium" not in found:
        if any(keyword in message for keyword in ("一般", "標準", "普通")):
            found["is_premium"] = "STANDARD"
        elif any(keyword in message for keyword in ("高級", "指定", "貴賓")):
            found["is_premium"] = "PREMIUM"

    return found


def test_reservation_chat_flow_creates_confirmed_order_end_to_end():
    state = agent.new_state()

    with patch("backend.app.agent.agent._available_services", return_value=[
        {"id": "restaurant_reservation", "name": "餐廳訂位", "description": "22世紀風味館 精選餐廳訂位服務"},
    ]), patch("backend.app.agent.agent.llm.extract_fields", side_effect=_fake_extract_fields):
        result = _run_turn(state, "我想訂22世紀風味館 信義旗艦店吃午餐")
        state = result["state"]
        assert state["service_id"] == "restaurant_reservation"

        result = _run_turn(state, "8月1日")
        state = result["state"]
        result = _run_turn(state, "4位")
        state = result["state"]
        result = _run_turn(state, "王大明")
        state = result["state"]
        result = _run_turn(state, "0912345678")
        state = result["state"]
        result = _run_turn(state, "一般訂位就好")
        state = result["state"]
        assert state["awaiting_confirmation"] is True

        result = _run_turn(state, "確認送出")
        state = result["state"]

    assert state["request_id"] is not None
    order = reservation.get_reservation_order("user-1", state["request_id"])
    assert order["order_items"]["restaurant_id"] == "r001"
    assert order["order_items"]["people"] == 4
    assert order["status"] in ("CONFIRMED", "PENDING_PROVIDER")


_FAKE_SEARCH_RESULT = {
    "restaurants": [
        {"id": "r001", "name": "22世紀風味館 信義旗艦店", "address": "台北市信義區松高路12號3樓",
         "phone": "02-2723-0022", "source": "internal", "reason": ""},
        {"id": "ChIJ-fake-place-id", "name": "台中好料理", "address": "台中市西區某路1號",
         "phone": "", "source": "google_places", "reason": "評價很高的台中餐廳"},
    ]
}


def test_reservation_chat_flow_falls_back_to_restaurant_search_when_name_not_recognized():
    state = agent.new_state()

    with patch("backend.app.agent.agent._available_services", return_value=[
        {"id": "restaurant_reservation", "name": "餐廳訂位", "description": "22世紀風味館 精選餐廳訂位服務"},
    ]), patch("backend.app.agent.agent.llm.is_available", return_value=False), \
         patch("backend.app.agent.agent.llm.extract_fields", side_effect=_fake_extract_fields), \
         patch("backend.app.agent.agent.restaurant_search.search_restaurants", return_value=_FAKE_SEARCH_RESULT) as mock_search:
        result = _run_turn(state, "我人在臺中，想找一家不錯的餐廳")
        state = result["state"]

    assert state["service_id"] == "restaurant_reservation"
    assert state["pending_restaurant_options"] == _FAKE_SEARCH_RESULT["restaurants"]
    assert "台中好料理" in result["reply"]
    assert "22世紀風味館 信義旗艦店" in result["reply"]
    mock_search.assert_called_once()
    assert mock_search.call_args.args[0] == "user-1"


def test_reservation_chat_flow_resolves_restaurant_pick_by_number():
    state = agent.new_state()
    state["service_id"] = "restaurant_reservation"
    state["service_name"] = "餐廳訂位"
    state["service_schema"] = {"fields": [
        {"id": "restaurant_id", "type": "select", "options": ["r001"], "required": True},
        {"id": "reserved_date", "type": "date", "required": True, "question": "哪一天？"},
    ]}
    state["collected_fields"] = {}
    state["missing_fields"] = ["restaurant_id", "reserved_date"]
    state["pending_restaurant_options"] = _FAKE_SEARCH_RESULT["restaurants"]

    result = _run_turn(state, "2")

    assert result["state"]["collected_fields"]["restaurant_id"] == "ChIJ-fake-place-id"
    assert result["state"]["pending_restaurant_options"] is None


def test_reservation_chat_flow_resolves_restaurant_pick_by_name():
    state = agent.new_state()
    state["service_id"] = "restaurant_reservation"
    state["service_name"] = "餐廳訂位"
    state["service_schema"] = {"fields": [
        {"id": "restaurant_id", "type": "select", "options": ["r001"], "required": True},
        {"id": "reserved_date", "type": "date", "required": True, "question": "哪一天？"},
    ]}
    state["collected_fields"] = {}
    state["missing_fields"] = ["restaurant_id", "reserved_date"]
    state["pending_restaurant_options"] = _FAKE_SEARCH_RESULT["restaurants"]

    result = _run_turn(state, "我要台中好料理那家")

    assert result["state"]["collected_fields"]["restaurant_id"] == "ChIJ-fake-place-id"
    assert result["state"]["pending_restaurant_options"] is None


def test_reservation_chat_flow_reprompts_on_unrecognized_restaurant_pick():
    state = agent.new_state()
    state["service_id"] = "restaurant_reservation"
    state["service_name"] = "餐廳訂位"
    state["service_schema"] = {"fields": [
        {"id": "restaurant_id", "type": "select", "options": ["r001"], "required": True},
    ]}
    state["collected_fields"] = {}
    state["missing_fields"] = ["restaurant_id"]
    state["pending_restaurant_options"] = _FAKE_SEARCH_RESULT["restaurants"]

    result = _run_turn(state, "都不喜歡")

    assert result["state"]["pending_restaurant_options"] == _FAKE_SEARCH_RESULT["restaurants"]
    assert "restaurant_id" not in result["state"]["collected_fields"]
    assert "台中好料理" in result["reply"]


def test_reservation_chat_flow_reports_error_without_crashing_when_order_invalid():
    state = agent.new_state()
    state["service_id"] = "restaurant_reservation"
    state["service_name"] = "餐廳訂位"
    state["service_schema"] = {"fields": [
        {"id": "restaurant_id", "type": "select", "options": ["r001"], "required": True},
    ]}
    state["collected_fields"] = {"restaurant_id": "does-not-exist"}
    state["missing_fields"] = []
    state["awaiting_confirmation"] = True

    result = _run_turn(state, "確認送出")

    assert result["state"]["request_id"] is None
    assert "reply" in result


def test_existing_service_submit_flow_still_works_unaffected():
    """Regression guard: a non-reservation service must still go through the
    generic tools.call('submit_service_request', ...) path untouched."""
    from backend.app.agent import tools as agent_tools

    called_with = {}

    def fake_tool_call(name, params, auth_token=None):
        called_with["name"] = name
        called_with["params"] = params
        return {"success": True, "request_id": "REQ-FAKE-1", "status": "SUBMITTED"}

    state = agent.new_state()
    state["service_id"] = "home_cleaning"
    state["service_name"] = "居家清潔"
    state["service_schema"] = {"fields": [{"id": "hours", "type": "number", "required": True}]}
    state["collected_fields"] = {"hours": 3}
    state["missing_fields"] = []
    state["awaiting_confirmation"] = True

    with patch.object(agent_tools, "call", side_effect=fake_tool_call):
        result = agent._submit("user-1", "sess-1", state, latest_user_message="確認送出")

    assert called_with["name"] == "submit_service_request"
    assert result["state"]["request_id"] == "REQ-FAKE-1"
