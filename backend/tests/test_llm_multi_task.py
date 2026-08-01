from unittest.mock import patch

from backend.app.agent import llm

SERVICES = [
    {"id": "quick_purchase", "name": "快速下單", "description": "供品、水果等常用組合"},
    {"id": "restaurant_reservation", "name": "餐廳訂位", "description": "22世紀風味館 精選餐廳訂位服務"},
    {"id": "home_cleaning", "name": "居家清潔", "description": "日常打掃與深度整理服務"},
]


def test_plan_multi_task_returns_validated_tasks():
    fake_payload = {
        "tasks": [
            {"service_id": "quick_purchase", "hint_fields": {"query": "供品跟水果"}},
            {"service_id": "restaurant_reservation", "hint_fields": {}},
            {"service_id": "not_a_real_service", "hint_fields": {}},
        ]
    }
    with patch("backend.app.agent.llm._converse_json", return_value=fake_payload):
        tasks = llm.plan_multi_task(message="買供品、訂餐廳", services=SERVICES)

    assert tasks == [
        {"service_id": "quick_purchase", "hint_fields": {"query": "供品跟水果"}},
        {"service_id": "restaurant_reservation", "hint_fields": {}},
    ]


def test_plan_multi_task_returns_empty_list_when_client_unavailable():
    with patch("backend.app.agent.llm._converse_json", return_value=None):
        assert llm.plan_multi_task(message="隨便說說", services=SERVICES) == []


def test_plan_turn_accepts_multi_task_mode():
    fake_payload = {"mode": "multi_task", "reply": None, "service_id": None}
    with patch("backend.app.agent.llm._converse_json", return_value=fake_payload):
        plan = llm.plan_turn(message="買供品、訂餐廳、約打掃", services=SERVICES)

    assert plan == {"mode": "multi_task", "reply": None, "service_id": None}
