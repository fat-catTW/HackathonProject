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


# ---- Finding #1: task cards / announcement must show the real catalog name, not the ----
# ---- generic "服務" fallback, for services that aren't in _display_service_name's dict. ----

SERVICES_WITH_RESTAURANT = [
    {"id": "quick_purchase", "name": "快速下單", "description": "供品、水果等常用組合"},
    {"id": "restaurant_reservation", "name": "餐廳訂位", "description": "22世紀風味館 精選餐廳訂位服務"},
]

TASKS_WITH_RESTAURANT = [
    {"service_id": "quick_purchase", "hint_fields": {}},
    {"service_id": "restaurant_reservation", "hint_fields": {}},
]


def test_task_cards_show_real_name_for_service_not_in_local_dict():
    state = agent.new_state()
    with patch(
        "backend.app.agent.agent._available_services", return_value=SERVICES_WITH_RESTAURANT
    ), patch(
        "backend.app.agent.agent.llm.plan_turn",
        return_value={"mode": "multi_task", "reply": None, "service_id": None},
    ), patch("backend.app.agent.agent.llm.plan_multi_task", return_value=TASKS_WITH_RESTAURANT):
        result = _run_turn(state, "幫我買供品，也訂個餐廳位子")

    assert result["task_cards"] == [
        {"service_id": "quick_purchase", "service_name": "快速下單"},
        {"service_id": "restaurant_reservation", "service_name": "餐廳訂位"},
    ]
    assert "服務" not in "".join(card["service_name"] for card in result["task_cards"])
    assert "餐廳訂位" in result["reply"]


# ---- Finding #2: a second multi-task run in the same session must not leak the first ----
# ---- run's completed_task_summaries. ----


def test_second_multi_task_detection_resets_completed_task_summaries():
    state = agent.new_state()
    # Simulate leftover summaries from an earlier, already-completed multi-task run in
    # this same session (is_multi_task already flipped back to False by the time the
    # queue emptied, but completed_task_summaries was never cleared before this fix).
    state["completed_task_summaries"] = ["快速下單：已幫你建立案件 REQ-OLD。"]

    with patch(
        "backend.app.agent.agent._available_services", return_value=SERVICES
    ), patch(
        "backend.app.agent.agent.llm.plan_turn",
        return_value={"mode": "multi_task", "reply": None, "service_id": None},
    ), patch("backend.app.agent.agent.llm.plan_multi_task", return_value=TASKS):
        result = _run_turn(state, "幫我買供品，也約一下打掃")

    assert result["state"]["completed_task_summaries"] == []


# ---- Finding #3: a failed submit inside a multi-task queue must not block the rest of ----
# ---- the queue — it should be marked 待重試 and the queue should advance. ----


def test_failed_submit_marks_pending_retry_and_advances_queue():
    state = agent.new_state()
    common_patches = [
        patch("backend.app.agent.agent._available_services", return_value=SERVICES),
        patch("backend.app.agent.agent.llm.extract_fields", return_value={}),
        patch("backend.app.agent.agent.llm.plan_form_turn", return_value=None),
        patch(
            "backend.app.agent.agent.quick_purchase.create_quick_purchase_order",
            return_value={"success": False, "error": {"message": "查無此組合"}},
        ),
    ]
    with patch(
        "backend.app.agent.agent.llm.plan_turn",
        return_value={"mode": "multi_task", "reply": None, "service_id": None},
    ), patch("backend.app.agent.agent.llm.plan_multi_task", return_value=TASKS), \
        common_patches[0], common_patches[1], common_patches[2], common_patches[3]:
        result = _run_turn(state, "幫我買供品，也約一下打掃")
        state = result["state"]

        result = _run_turn(state, "都要")
        state = result["state"]
        assert state["service_id"] == "quick_purchase"

        result = _run_turn(state, "供品跟水果")
        state = result["state"]
        result = _run_turn(state, "台中市西屯區文心路一段1號")
        state = result["state"]
        result = _run_turn(state, "0912345678")
        state = result["state"]
        assert state["awaiting_confirmation"] is True

        result = _run_turn(state, "確認送出")
        state = result["state"]

    # The failed quick_purchase task must not block the queue: it advances straight
    # into the next queued task (home_cleaning) instead of getting stuck retrying.
    assert state["service_id"] == "home_cleaning"
    assert len(state["completed_task_summaries"]) == 1
    assert "待重試" in state["completed_task_summaries"][0]
    assert "快速下單" in state["completed_task_summaries"][0]
    # The queue must have advanced into collecting the next task rather than getting
    # stuck re-asking about the failed one.
    assert result["reply"]


# ---- Finding #4: task selection must not silently default to "run everything" on an ----
# ---- explicit cancel reply, and must correctly parse an ordinal-style reply. ----


def test_explicit_cancel_reply_clears_queue_instead_of_running_everything():
    state = agent.new_state()
    with patch(
        "backend.app.agent.agent._available_services", return_value=SERVICES
    ), patch(
        "backend.app.agent.agent.llm.plan_turn",
        return_value={"mode": "multi_task", "reply": None, "service_id": None},
    ), patch("backend.app.agent.agent.llm.plan_multi_task", return_value=TASKS):
        result = _run_turn(state, "幫我買供品，也約一下打掃")
        state = result["state"]
        assert state["awaiting_task_selection"] is True

        result = _run_turn(state, "不要")
        state = result["state"]

    assert state["pending_tasks"] == []
    assert state["is_multi_task"] is False
    assert state["awaiting_task_selection"] is False
    assert state["service_id"] is None


THREE_SERVICES = SERVICES_WITH_RESTAURANT
THREE_TASKS = [
    {"service_id": "quick_purchase", "hint_fields": {}},
    {"service_id": "home_cleaning", "hint_fields": {}},
    {"service_id": "restaurant_reservation", "hint_fields": {}},
]


def test_ordinal_reply_selects_exactly_the_first_two_tasks():
    state = agent.new_state()
    common_patches = [
        patch("backend.app.agent.agent._available_services", return_value=THREE_SERVICES),
        patch("backend.app.agent.agent.llm.extract_fields", return_value={}),
        patch("backend.app.agent.agent.llm.plan_form_turn", return_value=None),
    ]
    with patch(
        "backend.app.agent.agent.llm.plan_turn",
        return_value={"mode": "multi_task", "reply": None, "service_id": None},
    ), patch("backend.app.agent.agent.llm.plan_multi_task", return_value=THREE_TASKS), \
        common_patches[0], common_patches[1], common_patches[2]:
        result = _run_turn(state, "幫我買供品、約打掃，也訂個餐廳")
        state = result["state"]
        assert state["awaiting_task_selection"] is True

        result = _run_turn(state, "先做前兩個")
        state = result["state"]

    # First of the two selected tasks (quick_purchase) is already active...
    assert state["service_id"] == "quick_purchase"
    # ...and only the second selected task (home_cleaning) remains queued — the third
    # task (restaurant_reservation) must have been dropped, not silently included.
    assert state["pending_tasks"] == [THREE_TASKS[1]]


# ---- Finding #5: a queued one-shot service (health_product_recommendation) must be ----
# ---- answered directly instead of being driven through generic field collection. ----

SERVICES_WITH_HEALTH = [
    {"id": "health_product_recommendation", "name": "健康商品推薦", "description": "說出健康或飲食需求，推薦適合的 7-11 商品"},
    {"id": "home_cleaning", "name": "居家清潔", "description": "日常打掃與深度整理服務"},
]

TASKS_WITH_HEALTH = [
    {"service_id": "health_product_recommendation", "hint_fields": {"query": "我在減脂想吃點心"}},
    {"service_id": "home_cleaning", "hint_fields": {}},
]


def test_queued_one_shot_service_is_answered_directly_not_via_field_collection():
    state = agent.new_state()
    common_patches = [
        patch("backend.app.agent.agent._available_services", return_value=SERVICES_WITH_HEALTH),
        patch("backend.app.agent.agent.llm.extract_fields", return_value={}),
        patch("backend.app.agent.agent.llm.plan_form_turn", return_value=None),
    ]
    with patch(
        "backend.app.agent.agent.llm.plan_turn",
        return_value={"mode": "multi_task", "reply": None, "service_id": None},
    ), patch("backend.app.agent.agent.llm.plan_multi_task", return_value=TASKS_WITH_HEALTH), \
        common_patches[0], common_patches[1], common_patches[2]:
        result = _run_turn(state, "幫我推薦健康點心，也約一下打掃")
        state = result["state"]
        assert state["awaiting_task_selection"] is True

        result = _run_turn(state, "都要")
        state = result["state"]

    # If health_product_recommendation had been driven through generic field
    # collection, its only field ("query") would already be filled by the hint, so
    # the queue would be stuck awaiting confirmation *for that service* instead of
    # answering immediately and moving on to the next queued task.
    assert state["service_id"] == "home_cleaning"
    assert state["awaiting_confirmation"] is False
    assert len(state["completed_task_summaries"]) == 1
    assert "健康商品推薦" in state["completed_task_summaries"][0]


# ---- Finding #6: a mid-queue message that merely *looks* like a restart request must ----
# ---- not silently wipe pending_tasks. ----


def test_mid_queue_restart_looking_message_does_not_wipe_pending_tasks():
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

        result = _run_turn(state, "都要")
        state = result["state"]
        assert state["service_id"] == "quick_purchase"
        assert state["pending_tasks"] == [TASKS[1]]

        # This message matches _looks_like_restart_service_request's pattern (an
        # "我想...訂位" style request) while we're still mid-collection on the active
        # multi-task item — it must not silently discard the queue.
        result = _run_turn(state, "我想訂位吃飯")
        state = result["state"]

    assert state["is_multi_task"] is True
    assert state["pending_tasks"] == [TASKS[1]]
    assert state["service_id"] == "quick_purchase"
    assert len(state["completed_task_summaries"]) == 0
