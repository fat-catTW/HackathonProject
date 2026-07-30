import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.api import onboarding
from backend.app.main import app
from backend.app.services import store as store_module


@pytest.fixture(autouse=True)
def isolated_store(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        test_store = store_module.MemoryStore(storage_path=Path(tmp) / "store.json")
        monkeypatch.setattr(store_module, "STORE", test_store)
        monkeypatch.setattr(onboarding, "STORE", test_store)
        yield test_store


def _auth_headers(client: TestClient) -> dict:
    accounts = client.get("/api/auth/demo-accounts").json()["accounts"]
    token = accounts[0]["token"]
    return {"Authorization": f"Bearer {token}"}


def test_onboarding_status_defaults_to_incomplete():
    client = TestClient(app)
    headers = _auth_headers(client)

    response = client.get("/api/onboarding/status", headers=headers)
    assert response.status_code == 200
    assert response.json() == {"completed": False, "version": 0}


def test_onboarding_complete_persists_version():
    client = TestClient(app)
    headers = _auth_headers(client)

    complete_response = client.post(
        "/api/onboarding/complete", json={"version": 1}, headers=headers
    )
    assert complete_response.status_code == 200
    assert complete_response.json() == {"success": True, "completed": True, "version": 1}

    status_response = client.get("/api/onboarding/status", headers=headers)
    assert status_response.json() == {"completed": True, "version": 1}


def test_onboarding_complete_with_newer_version_overwrites_old_flag():
    client = TestClient(app)
    headers = _auth_headers(client)

    client.post("/api/onboarding/complete", json={"version": 1}, headers=headers)
    client.post("/api/onboarding/complete", json={"version": 2}, headers=headers)

    status_response = client.get("/api/onboarding/status", headers=headers)
    assert status_response.json() == {"completed": True, "version": 2}


def test_onboarding_status_requires_auth():
    client = TestClient(app)

    response = client.get("/api/onboarding/status")
    assert response.status_code == 401


def test_onboarding_status_is_per_user():
    client = TestClient(app)
    accounts = client.get("/api/auth/demo-accounts").json()["accounts"]
    assert len(accounts) >= 2
    headers_a = {"Authorization": f"Bearer {accounts[0]['token']}"}
    headers_b = {"Authorization": f"Bearer {accounts[1]['token']}"}

    client.post("/api/onboarding/complete", json={"version": 1}, headers=headers_a)

    assert client.get("/api/onboarding/status", headers=headers_a).json()["completed"] is True
    assert client.get("/api/onboarding/status", headers=headers_b).json()["completed"] is False
