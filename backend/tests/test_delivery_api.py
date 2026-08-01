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


def test_customer_can_no_longer_advance_delivery_status_directly():
    """使用者端的模擬端點已經移除，狀態推進只能透過廠商後台。"""
    client = TestClient(app)
    headers = _auth_headers(client)
    created = _create_order(client, headers)

    response = client.post(
        f"/api/delivery/orders/{created['request_id']}/simulate",
        json={"vendor_status": 1},
        headers=headers,
    )
    assert response.status_code == 404


def test_delivery_webhook_requires_correct_secret(isolated_store):
    client = TestClient(app)
    headers = _auth_headers(client)
    created = _create_order(client, headers)

    # Get the current user's sub (actor_id) from the demo account, the same way
    # test_reservations_api.py's booking-callback tests do (don't hardcode a sub).
    demo_response = client.get("/api/auth/demo-accounts")
    demo_token = demo_response.json()["accounts"][0]["token"]
    from backend.app.config import get_settings
    resident_sub = get_settings().demo_users[demo_token]["sub"]

    ok = client.post(
        "/api/webhooks/delivery-callback",
        json={"actor_id": resident_sub, "request_id": created["request_id"], "vendor_status": 1},
        headers={"X-Webhook-Secret": "demo-webhook-secret"},
    )
    assert ok.status_code == 200, ok.text

    no_header = client.post(
        "/api/webhooks/delivery-callback",
        json={"actor_id": resident_sub, "request_id": created["request_id"], "vendor_status": 1},
    )
    assert no_header.status_code == 401

    wrong_secret = client.post(
        "/api/webhooks/delivery-callback",
        json={"actor_id": resident_sub, "request_id": created["request_id"], "vendor_status": 1},
        headers={"X-Webhook-Secret": "wrong-secret"},
    )
    assert wrong_secret.status_code == 401
