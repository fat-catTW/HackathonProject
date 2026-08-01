import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from backend.app.agent import agent
from backend.app.services import shop, store as store_module


@pytest.fixture(autouse=True)
def isolated_store(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        test_store = store_module.MemoryStore(storage_path=Path(tmp) / "store.json")
        monkeypatch.setattr(store_module, "STORE", test_store)
        monkeypatch.setattr(shop, "STORE", test_store)
        test_store.restock_sku("sku_fruit_offering_set", 5)
        yield test_store


def _run_turn(state, message, actor_id="user-1", session_id="sess-1"):
    return agent.handle_message(actor_id, session_id, state, message)


def test_quick_purchase_chat_flow_creates_order_end_to_end():
    state = agent.new_state()

    with patch(
        "backend.app.agent.agent._available_services",
        return_value=[{"id": "quick_purchase", "name": "快速下單", "description": "供品、水果等常用組合"}],
    ), patch("backend.app.agent.agent.llm.extract_fields", return_value={}), patch(
        "backend.app.agent.agent.llm.plan_form_turn", return_value=None
    ), patch(
        "backend.app.agent.agent.llm.plan_turn", return_value=None
    ):
        result = _run_turn(state, "幫我買拜拜用的水果")
        state = result["state"]
        assert state["service_id"] == "quick_purchase"

        result = _run_turn(state, "台中市西屯區文心路一段1號")
        state = result["state"]
        result = _run_turn(state, "0912345678")
        state = result["state"]
        assert state["awaiting_confirmation"] is True

        result = _run_turn(state, "確認送出")
        assert result["state"]["request_id"]
        assert result["state"]["status"] == "SUBMITTED"
