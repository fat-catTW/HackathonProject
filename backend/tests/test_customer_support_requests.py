import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.api import requests as requests_module
from backend.app.main import app
from backend.app.services import store as store_module
from backend.app.services import submission


@pytest.fixture(autouse=True)
def isolated_store(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        test_store = store_module.MemoryStore(storage_path=Path(tmp) / "store.json")
        monkeypatch.setattr(store_module, "STORE", test_store)
        monkeypatch.setattr(requests_module, "STORE", test_store)
        monkeypatch.setattr(submission, "STORE", test_store)
        yield test_store


def test_customer_support_request_keeps_context_and_type_metadata(isolated_store):
    client = TestClient(app)

    accounts_response = client.get("/api/auth/demo-accounts")
    token = accounts_response.json()["accounts"][0]["token"]
    headers = {"Authorization": f"Bearer {token}"}
    me = client.get("/api/auth/me", headers=headers).json()

    response = client.post(
        "/api/services/customer_support/requests",
        json={
            "payload": {
                "faq_reference": "How do I cancel an order?",
                "current_page_id": "request_detail",
                "current_page_label": "Request detail",
                "related_request_id": "REQ-20260730-001",
                "related_service_name": "Delivery order",
                "issue_topic": "訂單取消",
                "issue_summary": "Need help canceling an order",
                "issue_details": "User opened support from request detail and expects an agent to help cancel or follow up.",
            }
        },
        headers=headers,
    )
    assert response.status_code == 200

    request_id = response.json()["request_id"]
    detail = client.get(f"/api/requests/{request_id}", headers=headers)
    assert detail.status_code == 200

    stored_request = isolated_store.get_request(me["sub"], request_id)
    assert stored_request is not None
    assert stored_request["pms_form_type"] == 5
    assert stored_request["request_category"] == "CUSTOMER_SUPPORT"
    assert stored_request["form_data"]["current_page_id"] == "request_detail"
    assert stored_request["form_data"]["related_request_id"] == "REQ-20260730-001"
