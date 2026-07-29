import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from backend.app.agent import agent, nlu
from backend.app.services import delivery, store as store_module


@pytest.fixture(autouse=True)
def isolated_store(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        test_store = store_module.MemoryStore(storage_path=Path(tmp) / "store.json")
        monkeypatch.setattr(store_module, "STORE", test_store)
        monkeypatch.setattr(delivery, "STORE", test_store)
        yield test_store


def _run_turn(state, message, actor_id="user-1", session_id="sess-1"):
    return agent.handle_message(actor_id, session_id, state, message)


def _fake_extract_fields(*, message, fields, collected_fields, **_kwargs):
    """Deterministic stand-in for the live Bedrock-backed llm.extract_fields
    (unreachable in this environment — same rationale as
    test_agent_reservation_submit.py). store_id/goods never flow through this
    path: agent.py excludes them via _LLM_EXCLUDED_FIELDS and collects them
    through the dedicated cart-building loop instead, so this fake only needs
    to cover the plain text fields: address, contact_name, note.
    """
    found = {}
    field_ids = {field["id"] for field in fields}

    if "address" in field_ids and "address" not in collected_fields:
        parsed = nlu.parse_address(message)
        if parsed:
            found["address"] = parsed

    if "contact_name" in field_ids and "contact_name" not in collected_fields:
        stripped = message.strip()
        if 2 <= len(stripped) <= 4 and all("一" <= ch <= "鿿" for ch in stripped):
            found["contact_name"] = stripped

    # note is asked last (after address/contact_name), so only capture it once
    # those are already collected — otherwise this eagerly grabs turn-1 text
    # (e.g. "我想叫外送") as the note before the cart/address/name are even done.
    if (
        "note" in field_ids
        and "note" not in collected_fields
        and "address" in collected_fields
        and "contact_name" in collected_fields
    ):
        found["note"] = message.strip()

    return found


def test_delivery_chat_flow_collects_store_then_cart_then_hands_off():
    state = agent.new_state()

    with patch("backend.app.agent.agent._available_services", return_value=[
        {"id": "food_delivery", "name": "美食外送", "description": "附近店家美食外送到府服務"},
    ]), patch("backend.app.agent.agent.llm.extract_fields", side_effect=_fake_extract_fields):
        result = _run_turn(state, "我想叫外送")
        state = result["state"]
        assert state["service_id"] == "food_delivery"
        assert state["pending_delivery_field"] == "store"

        result = _run_turn(state, "好味道便當")
        state = result["state"]
        assert state["collected_fields"]["store_id"] == "store-001"
        assert state["pending_delivery_field"] == "item"

        result = _run_turn(state, "招牌雞腿便當一個")
        state = result["state"]
        assert state["collected_fields"]["goods"] == [
            {"id": "item-001", "title": "招牌雞腿便當", "price": 110, "quantity": 1}
        ]
        assert state["pending_delivery_field"] == "more_items"

        result = _run_turn(state, "不用了")
        state = result["state"]

    assert state["pending_delivery_field"] is None
    assert "store_id" not in state["missing_fields"]
    assert "goods" not in state["missing_fields"]


def test_delivery_chat_flow_reprompts_on_unknown_store_name():
    state = agent.new_state()

    with patch("backend.app.agent.agent._available_services", return_value=[
        {"id": "food_delivery", "name": "美食外送", "description": "附近店家美食外送到府服務"},
    ]), patch("backend.app.agent.agent.llm.extract_fields", side_effect=_fake_extract_fields):
        result = _run_turn(state, "我想叫外送")
        state = result["state"]
        result = _run_turn(state, "麥當勞")
        state = result["state"]

    assert state["pending_delivery_field"] == "store"
    assert "store_id" not in state["collected_fields"]


def test_delivery_chat_flow_reprompts_on_unknown_menu_item():
    state = agent.new_state()

    with patch("backend.app.agent.agent._available_services", return_value=[
        {"id": "food_delivery", "name": "美食外送", "description": "附近店家美食外送到府服務"},
    ]), patch("backend.app.agent.agent.llm.extract_fields", side_effect=_fake_extract_fields):
        result = _run_turn(state, "我想叫外送")
        state = result["state"]
        result = _run_turn(state, "好味道便當")
        state = result["state"]
        result = _run_turn(state, "我要牛肉麵")
        state = result["state"]

    assert state["pending_delivery_field"] == "item"
    assert state["collected_fields"].get("goods") in (None, [])


def test_delivery_chat_flow_creates_order_end_to_end():
    state = agent.new_state()

    with patch("backend.app.agent.agent._available_services", return_value=[
        {"id": "food_delivery", "name": "美食外送", "description": "附近店家美食外送到府服務"},
    ]), patch("backend.app.agent.agent.llm.extract_fields", side_effect=_fake_extract_fields):
        result = _run_turn(state, "我想叫外送")
        state = result["state"]
        result = _run_turn(state, "好味道便當")
        state = result["state"]
        result = _run_turn(state, "招牌雞腿便當一個")
        state = result["state"]
        result = _run_turn(state, "不用了")
        state = result["state"]
        result = _run_turn(state, "台北市大安區忠孝東路四段100號")
        state = result["state"]
        result = _run_turn(state, "王小明")
        state = result["state"]
        result = _run_turn(state, "不辣")
        state = result["state"]
        assert state["awaiting_confirmation"] is True

        result = _run_turn(state, "確認送出")
        state = result["state"]

    assert state["request_id"] is not None
    order = delivery.get_delivery_order("user-1", state["request_id"])
    assert order["order_items"]["store"]["id"] == "store-001"
    assert order["order_items"]["goods"] == [
        {"id": "item-001", "title": "招牌雞腿便當", "price": 110, "quantity": 1}
    ]
    assert order["order_type"] == "06"
    assert order["order_status"] == "01"


def test_delivery_chat_flow_reports_error_without_crashing_when_cart_empty():
    state = agent.new_state()
    state["service_id"] = "food_delivery"
    state["service_name"] = "美食外送"
    state["service_schema"] = {"fields": [
        {"id": "store_id", "type": "select", "required": True},
        {"id": "goods", "type": "cart", "required": True},
    ]}
    # address/contact_name/note are deliberately filled in so the only thing
    # missing is a non-empty cart — isolates the EMPTY_CART path in
    # delivery.create_delivery_order() from the generic tool's unrelated
    # "missing required field" rejection (which would also produce
    # request_id is None, but for the wrong reason).
    state["collected_fields"] = {
        "store_id": "store-001",
        "goods": [],
        "address": "台北市大安區忠孝東路四段100號",
        "contact_name": "王小明",
        "note": "不辣",
    }
    state["missing_fields"] = []
    state["awaiting_confirmation"] = True

    result = _run_turn(state, "確認送出")

    assert result["state"]["request_id"] is None
    assert "reply" in result
