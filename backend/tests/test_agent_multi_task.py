import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from backend.app.agent import agent
from backend.app.services import shop, store as store_module

SERVICES = [
    {"id": "quick_purchase", "name": "快速下單", "description": "供品、水果等常用組合"},
    {"id": "home_cleaning", "name": "居家清潔", "description": "日常打掃與深度整理服務"},
]

TASKS = [
    {"service_id": "quick_purchase", "hint_fields": {}},
    {"service_id": "home_cleaning", "hint_fields": {}},
]


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


def test_multi_task_message_returns_task_cards_and_awaits_selection():
    state = agent.new_state()
    with patch("backend.app.agent.agent._available_services", return_value=SERVICES), patch(
        "backend.app.agent.agent.llm.plan_turn",
        return_value={"mode": "multi_task", "reply": None, "service_id": None},
    ), patch("backend.app.agent.agent.llm.plan_multi_task", return_value=TASKS):
        result = _run_turn(state, "幫我買供品，也約一下打掃")

    assert result["task_cards"] == [
        {"service_id": "quick_purchase", "service_name": "快速下單"},
        {"service_id": "home_cleaning", "service_name": "居家清潔"},
    ]
    assert result["state"]["awaiting_task_selection"] is True
    assert result["state"]["pending_tasks"] == TASKS


def test_multi_task_full_flow_runs_both_tasks_and_produces_share_text():
    state = agent.new_state()
    common_patches = [
        patch("backend.app.agent.agent._available_services", return_value=SERVICES),
        patch("backend.app.agent.agent.llm.extract_fields", return_value={}),
        patch("backend.app.agent.agent.llm.plan_form_turn", return_value=None),
    ]
    with patch(
        "backend.app.agent.agent.llm.plan_turn",
        return_value={"mode": "multi_task", "reply": None, "service_id": None},
    ), patch("backend.app.agent.agent.llm.plan_multi_task", return_value=TASKS), \
        common_patches[0], common_patches[1], common_patches[2]:
        result = _run_turn(state, "幫我買供品，也約一下打掃")
        state = result["state"]
        assert state["awaiting_task_selection"] is True

        # Accept both tasks in the given order.
        result = _run_turn(state, "都要")
        state = result["state"]
        assert state["service_id"] == "quick_purchase"

        # quick_purchase fields: query, address, phone.
        result = _run_turn(state, "供品跟水果")
        state = result["state"]
        result = _run_turn(state, "台中市西屯區文心路一段1號")
        state = result["state"]
        result = _run_turn(state, "0912345678")
        state = result["state"]
        assert state["awaiting_confirmation"] is True

        result = _run_turn(state, "確認送出")
        state = result["state"]
        # First task done, should have advanced straight into home_cleaning collection.
        assert state["service_id"] == "home_cleaning"
        assert len(state["completed_task_summaries"]) == 1

        # home_cleaning fields: cleaning_service_option, preferred_date, preferred_time_slot, address, phone.
        result = _run_turn(state, "地板清潔")
        state = result["state"]
        result = _run_turn(state, "明天")
        state = result["state"]
        result = _run_turn(state, "14:00")
        state = result["state"]
        result = _run_turn(state, "台中市西屯區文心路一段1號")
        state = result["state"]
        result = _run_turn(state, "0912345678")
        state = result["state"]
        assert state["awaiting_confirmation"] is True

        result = _run_turn(state, "確認送出")

    assert result["state"]["is_multi_task"] is False
    assert result["share_text"]
    assert "快速下單" in result["share_text"]
    assert "居家清潔" in result["share_text"]
