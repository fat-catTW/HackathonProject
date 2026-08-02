from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.app.main import app


def _login_and_session(client: TestClient):
    accounts = client.get("/api/auth/demo-accounts").json()["accounts"]
    token = accounts[0]["token"]
    headers = {"Authorization": f"Bearer {token}"}
    session = client.post("/api/sessions", headers=headers)
    return headers, session.json()["session_id"]


def test_chat_response_includes_task_cards_field():
    client = TestClient(app)
    headers, session_id = _login_and_session(client)
    fake_tasks = [
        {"service_id": "quick_purchase", "hint_fields": {}},
        {"service_id": "home_cleaning", "hint_fields": {}},
    ]
    # is_available 也要一起 patch：agent 只有在 LLM 可用時才會走 turn_router，
    # CI 沒有 AWS 憑證，少了這一行下面兩個 patch 根本不會被呼叫到。
    with patch("backend.app.agent.agent.llm.is_available", return_value=True), patch(
        "backend.app.agent.agent.llm.plan_turn",
        return_value={"mode": "multi_task", "reply": None, "service_id": None},
    ), patch("backend.app.agent.agent.llm.plan_multi_task", return_value=fake_tasks):
        response = client.post(
            "/api/chat",
            headers=headers,
            json={"session_id": session_id, "message": "幫我買供品，也約一下打掃"},
        )

    body = response.json()
    assert response.status_code == 200
    assert body["task_cards"] == [
        {"service_id": "quick_purchase", "service_name": "快速下單"},
        {"service_id": "home_cleaning", "service_name": "居家清潔"},
    ]
    assert body["share_text"] is None
