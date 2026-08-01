from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.app.main import app


def _auth_headers(client: TestClient) -> dict:
    accounts = client.get("/api/auth/demo-accounts").json()["accounts"]
    token = accounts[0]["token"]
    return {"Authorization": f"Bearer {token}"}


def test_scam_check_returns_classification():
    client = TestClient(app)
    headers = _auth_headers(client)
    with patch(
        "backend.app.api.scam_check.llm.check_scam_message",
        return_value={"category": "投資詐騙", "explanation": "請勿匯款，先跟家人確認。"},
    ):
        response = client.post("/api/scam-check", headers=headers, json={"message": "老師說穩賺不賠"})

    assert response.status_code == 200
    assert response.json() == {"category": "投資詐騙", "explanation": "請勿匯款，先跟家人確認。"}


def test_scam_check_returns_503_when_llm_unavailable():
    client = TestClient(app)
    headers = _auth_headers(client)
    with patch("backend.app.api.scam_check.llm.check_scam_message", return_value=None):
        response = client.post("/api/scam-check", headers=headers, json={"message": "隨便的訊息"})

    assert response.status_code == 503
