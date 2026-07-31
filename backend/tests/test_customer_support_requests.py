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


def test_keyword_detection_survives_services_without_keywords():
    """customer_support 沒有 keywords，關鍵字比對不能因此炸掉。

    這個服務 show_in_catalog=False，只從 FAQ 升級流程建立，刻意不列關鍵字；
    detect_service 以前直接讀 s["keywords"]，讓所有走 NLU 的對話都 KeyError。
    """
    from backend.app.agent import nlu
    from backend.app.services.catalog import SERVICES

    assert not any("keywords" in s for s in SERVICES if s["id"] == "customer_support")

    service_id, candidates = nlu.detect_service("我想訂餐廳吃飯")
    assert service_id == "restaurant_reservation"
    # 沒有關鍵字的服務永遠不會被選中，不會誤攔一般對話。
    assert "customer_support" not in [s["id"] for s in candidates]
