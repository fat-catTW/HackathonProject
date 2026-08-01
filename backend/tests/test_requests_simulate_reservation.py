import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services import reservation, store as store_module
from backend.app.api import requests as requests_module
from backend.app.api import vendor as vendor_module


@pytest.fixture(autouse=True)
def isolated_store(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        test_store = store_module.MemoryStore(storage_path=Path(tmp) / "store.json")
        monkeypatch.setattr(store_module, "STORE", test_store)
        monkeypatch.setattr(reservation, "STORE", test_store)
        monkeypatch.setattr(requests_module, "STORE", test_store)
        # test_vendor_accept_syncs_order_status_for_reservation 會打 /api/vendor/requests/...，
        # vendor.py 也直接引用 STORE，同樣要換成隔離的測試用 store。
        monkeypatch.setattr(vendor_module, "STORE", test_store)
        yield test_store


def _submit_reservation(client: TestClient, headers: dict) -> dict:
    return client.post(
        "/api/reservations/submit",
        json={
            "restaurant_id": "r005",
            "reserved_date": "2026-08-01",
            "time_slot": "LUNCH",
            "people": 2,
            "contact_name": "王大明",
            "phone": "0912345678",
            "is_premium": False,
        },
        headers=headers,
    ).json()


def test_customer_simulate_endpoint_is_removed():
    client = TestClient(app)
    accounts = client.get("/api/auth/demo-accounts").json()["accounts"]
    headers = {"Authorization": f"Bearer {accounts[0]['token']}"}

    created = _submit_reservation(client, headers)
    response = client.post(f"/api/requests/{created['request_id']}/simulate/CONFIRMED", headers=headers)
    assert response.status_code == 404


def test_vendor_accept_syncs_order_status_for_reservation():
    client = TestClient(app)
    accounts = client.get("/api/auth/demo-accounts").json()["accounts"]
    headers = {"Authorization": f"Bearer {accounts[0]['token']}"}

    created = _submit_reservation(client, headers)
    assert created["status"] == "PENDING_PROVIDER"

    vendor_login = client.post(
        "/api/vendor/login", json={"email": "vendor22@demo.local", "password": "vendor1234"}
    ).json()
    vendor_headers = {"Authorization": f"Bearer {vendor_login['token']}"}

    detail = client.get(
        f"/api/vendor/requests/{created['request_id']}", headers=vendor_headers
    ).json()
    accept = client.post(
        f"/api/vendor/requests/{created['request_id']}/accept",
        json={"version": detail["version"]},
        headers=vendor_headers,
    )
    assert accept.status_code == 200, accept.text

    order = client.get(f"/api/reservations/{created['request_id']}", headers=headers).json()
    assert order["status"] == "CONFIRMED"
    assert order["order_status"] == "03"
    assert order["status_history"][-1]["status"] == "03"
