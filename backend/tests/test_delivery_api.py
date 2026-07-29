import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services import delivery, store as store_module


@pytest.fixture(autouse=True)
def isolated_store(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        test_store = store_module.MemoryStore(storage_path=Path(tmp) / "store.json")
        monkeypatch.setattr(store_module, "STORE", test_store)
        monkeypatch.setattr(delivery, "STORE", test_store)
        yield test_store


def _auth_headers(client: TestClient) -> dict:
    accounts = client.get("/api/auth/demo-accounts").json()["accounts"]
    token = accounts[0]["token"]
    return {"Authorization": f"Bearer {token}"}


def _create_order(client: TestClient, headers: dict) -> dict:
    return client.post(
        "/api/delivery/submit",
        json={
            "address": {
                "lat": 25.033, "lng": 121.565,
                "city": "台北市", "area": "大安區", "street": "忠孝東路四段100號",
                "remark": "", "contact_name": "王小明",
            },
            "goods": [{"id": "item-001", "title": "招牌雞腿便當", "price": 110, "quantity": 1}],
            "store_id": "store-001",
            "store_name": "好味道便當",
            "store_address": "台北市大安區忠孝東路四段100號",
        },
        headers=headers,
    ).json()


def test_simulate_delivery_status_advances_order_status_and_driver_info():
    client = TestClient(app)
    headers = _auth_headers(client)
    created = _create_order(client, headers)
    assert created["order_status"] == "01"

    response = client.post(
        f"/api/delivery/orders/{created['request_id']}/simulate",
        json={
            "vendor_status": 1,
            "delivery": {"driver_name": "示範外送員", "driver_phone": "0912345678", "eta_minutes": 20},
        },
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["order_status"] == "02"

    detail = client.get(f"/api/delivery/orders/{created['request_id']}", headers=headers).json()
    assert detail["order_status"] == "02"
    assert detail["vendor_data"]["delivery"]["driver_name"] == "示範外送員"


def test_simulate_delivery_status_returns_404_for_missing_order():
    client = TestClient(app)
    headers = _auth_headers(client)

    response = client.post(
        "/api/delivery/orders/REQ-DOES-NOT-EXIST/simulate",
        json={"vendor_status": 1},
        headers=headers,
    )
    assert response.status_code == 404
