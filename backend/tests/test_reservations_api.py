import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services import reservation, store as store_module


@pytest.fixture(autouse=True)
def isolated_store(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        test_store = store_module.MemoryStore(storage_path=Path(tmp) / "store.json")
        monkeypatch.setattr(store_module, "STORE", test_store)
        monkeypatch.setattr(reservation, "STORE", test_store)
        yield test_store


@pytest.fixture
def client():
    return TestClient(app)


def auth_headers(client: TestClient) -> dict:
    # Demo auth: get token from /api/auth/demo-accounts endpoint.
    # The brief assumed /api/auth/demo-login but the actual implementation only has
    # /api/auth/demo-accounts which returns a list of demo accounts with their tokens.
    response = client.get("/api/auth/demo-accounts")
    assert response.status_code == 200
    accounts = response.json()["accounts"]
    token = accounts[0]["token"]  # Get first available demo token
    return {"Authorization": f"Bearer {token}"}


def valid_payload(**overrides):
    payload = {
        "restaurant_id": "r001",
        "reserved_date": "2026-09-15",
        "time_slot": "LUNCH",
        "specific_time": "12:30",
        "people": 2,
        "contact_name": "王大明",
        "phone": "0912345678",
        "is_premium": False,
    }
    payload.update(overrides)
    return payload


def test_list_restaurants_returns_seed_data(client):
    headers = auth_headers(client)
    response = client.get("/api/restaurants", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert len(body["restaurants"]) <= 6
    assert body["restaurants"][0]["id"] == "r001"


def test_get_restaurant_detail(client):
    headers = auth_headers(client)
    response = client.get("/api/restaurants/r001", headers=headers)
    assert response.status_code == 200
    assert response.json()["name"] == "22世紀風味館 信義旗艦店"


def test_get_restaurant_not_found_returns_404(client):
    headers = auth_headers(client)
    response = client.get("/api/restaurants/nope", headers=headers)
    assert response.status_code == 404


def test_submit_reservation_creates_order(client):
    headers = auth_headers(client)
    response = client.post("/api/reservations/submit", json=valid_payload(), headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["order_status"] == "03"


def test_submit_reservation_invalid_payload_returns_400(client):
    headers = auth_headers(client)
    response = client.post("/api/reservations/submit", json=valid_payload(phone="bad"), headers=headers)
    assert response.status_code == 400


def test_get_reservation_detail(client):
    headers = auth_headers(client)
    created = client.post("/api/reservations/submit", json=valid_payload(), headers=headers).json()
    response = client.get(f"/api/reservations/{created['request_id']}", headers=headers)
    assert response.status_code == 200
    assert response.json()["order_items"]["restaurant_id"] == "r001"


def test_cancel_reservation(client):
    headers = auth_headers(client)
    created = client.post("/api/reservations/submit", json=valid_payload(), headers=headers).json()
    response = client.post(f"/api/reservations/{created['request_id']}/cancel", headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"


def test_booking_callback_updates_pending_order(client):
    headers = auth_headers(client)

    # Get the current user's sub (actor_id) from the demo account
    demo_response = client.get("/api/auth/demo-accounts")
    # Get the first demo token to determine the user
    demo_token = demo_response.json()["accounts"][0]["token"]
    # Map demo token to sub via settings
    from backend.app.config import get_settings
    actor_id = get_settings().demo_users[demo_token]["sub"]

    created = client.post(
        "/api/reservations/submit", json=valid_payload(restaurant_id="r005"), headers=headers
    ).json()
    assert created["status"] == "PENDING_PROVIDER"

    response = client.post(
        "/api/webhooks/booking-callback",
        json={
            "request_id": created["request_id"],
            "actor_id": actor_id,
            "status": "CONFIRMED",
            "booking_id": "EZ-CB-1",
            "share_reservation_url": "https://eztable.example.com/booking/EZ-CB-1",
        },
    )
    assert response.status_code == 200

    detail = client.get(f"/api/reservations/{created['request_id']}", headers=headers).json()
    assert detail["status"] == "CONFIRMED"
    assert detail["vendor_data"]["booking_id"] == "EZ-CB-1"
