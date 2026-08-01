from fastapi.testclient import TestClient

from backend.app.main import app


def auth_headers(client: TestClient) -> dict:
    response = client.get("/api/auth/demo-accounts")
    token = response.json()["accounts"][0]["token"]
    return {"Authorization": f"Bearer {token}"}


def test_get_weather_returns_default_city_data():
    client = TestClient(app)
    headers = auth_headers(client)
    response = client.get("/api/weather", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["city"] == "台中市"
    assert "temperature" in body


def test_get_weather_accepts_city_query_param():
    client = TestClient(app)
    headers = auth_headers(client)
    response = client.get("/api/weather?city=台北市", headers=headers)
    assert response.status_code == 200
    assert response.json()["city"] == "台北市"


def test_get_weather_requires_auth():
    client = TestClient(app)
    response = client.get("/api/weather")
    assert response.status_code in (401, 403)
