# backend/tests/test_clinics_api.py
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services import clinic_appointment, clinic_catalog, store as store_module
import tempfile
from pathlib import Path
import pytest


@pytest.fixture(autouse=True)
def isolated_store(monkeypatch):
    clinic_catalog._cache.clear()
    monkeypatch.setattr(clinic_catalog, "_fetch_all_clinics", lambda: None)
    with tempfile.TemporaryDirectory() as tmp:
        test_store = store_module.MemoryStore(storage_path=Path(tmp) / "store.json")
        monkeypatch.setattr(store_module, "STORE", test_store)
        monkeypatch.setattr(clinic_appointment, "STORE", test_store)
        yield test_store


@pytest.fixture
def client():
    return TestClient(app)


def auth_headers(client: TestClient) -> dict:
    response = client.get("/api/auth/demo-accounts")
    token = response.json()["accounts"][0]["token"]
    return {"Authorization": f"Bearer {token}"}


def valid_appointment_payload(**overrides):
    payload = {
        "clinic_id": "clinic-fallback-001",
        "appointment_date": "2026-08-02",
        "appointment_time": "15:00",
        "contact_name": "王添財",
        "phone": "0912345678",
        "symptom_note": "咳嗽、喉嚨癢",
    }
    payload.update(overrides)
    return payload


def test_list_clinics_endpoint_returns_filtered_results(client):
    headers = auth_headers(client)
    response = client.get("/api/clinics?city=台中市&district=西屯區", headers=headers)
    assert response.status_code == 200
    assert len(response.json()["clinics"]) > 0


def test_symptom_triage_endpoint_returns_specialty_and_clinics(client):
    headers = auth_headers(client)
    response = client.post(
        "/api/symptom-triage",
        json={"symptom_text": "我一直咳嗽，喉嚨很癢", "city": "台中市", "district": "西屯區"},
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["specialty"] == "耳鼻喉科"
    assert len(body["clinics"]) > 0
    assert body["recommended_clinic_id"] is not None


def test_symptom_triage_endpoint_requires_symptom_text(client):
    headers = auth_headers(client)
    response = client.post(
        "/api/symptom-triage", json={"symptom_text": "", "city": "台中市", "district": "西屯區"}, headers=headers
    )
    assert response.status_code == 400


def test_submit_appointment_creates_order(client):
    headers = auth_headers(client)
    response = client.post("/api/clinic-appointments", json=valid_appointment_payload(), headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "CONFIRMED"


def test_submit_appointment_unknown_clinic_returns_404(client):
    headers = auth_headers(client)
    response = client.post(
        "/api/clinic-appointments", json=valid_appointment_payload(clinic_id="nope"), headers=headers
    )
    assert response.status_code == 404


def test_get_appointment_detail(client):
    headers = auth_headers(client)
    created = client.post("/api/clinic-appointments", json=valid_appointment_payload(), headers=headers).json()
    response = client.get(f"/api/clinic-appointments/{created['request_id']}", headers=headers)
    assert response.status_code == 200
    assert response.json()["order_items"]["clinic_id"] == "clinic-fallback-001"


def test_get_appointment_detail_not_found_returns_404(client):
    headers = auth_headers(client)
    response = client.get("/api/clinic-appointments/nope", headers=headers)
    assert response.status_code == 404


def test_cross_sell_endpoint_returns_recommendations(client):
    headers = auth_headers(client)
    created = client.post("/api/clinic-appointments", json=valid_appointment_payload(), headers=headers).json()
    response = client.post(f"/api/clinic-appointments/{created['request_id']}/cross-sell", headers=headers)
    assert response.status_code == 200
    assert len(response.json()["recommendations"]) > 0


def test_cross_sell_endpoint_not_found_returns_404(client):
    headers = auth_headers(client)
    response = client.post("/api/clinic-appointments/nope/cross-sell", headers=headers)
    assert response.status_code == 404
