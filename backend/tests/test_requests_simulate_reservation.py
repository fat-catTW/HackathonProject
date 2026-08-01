import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services import reservation, store as store_module
from backend.app.api import requests as requests_module


@pytest.fixture(autouse=True)
def isolated_store(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        test_store = store_module.MemoryStore(storage_path=Path(tmp) / "store.json")
        monkeypatch.setattr(store_module, "STORE", test_store)
        monkeypatch.setattr(reservation, "STORE", test_store)
        monkeypatch.setattr(requests_module, "STORE", test_store)
        yield test_store


def test_simulate_status_syncs_order_status_for_reservation():
    client = TestClient(app)

    # Get demo accounts and use the first one
    accounts_response = client.get("/api/auth/demo-accounts")
    accounts = accounts_response.json()["accounts"]
    token = accounts[0]["token"]
    headers = {"Authorization": f"Bearer {token}"}

    created = client.post(
        "/api/reservations/submit",
        json={
            "restaurant_id": "r005",
            "reserved_date": "2026-09-15",
            "time_slot": "LUNCH",
            "people": 2,
            "contact_name": "王大明",
            "phone": "0912345678",
            "is_premium": False,
        },
        headers=headers,
    ).json()
    assert created["status"] == "PENDING_PROVIDER"

    response = client.post(
        f"/api/requests/{created['request_id']}/simulate/CONFIRMED", headers=headers
    )
    assert response.status_code == 200

    detail = client.get(f"/api/reservations/{created['request_id']}", headers=headers).json()
    assert detail["status"] == "CONFIRMED"
    assert detail["order_status"] == "03"
    assert detail["status_history"][-1]["status"] == "03"
