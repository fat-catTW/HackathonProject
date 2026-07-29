"""廠商後台：資料隔離與清單可見性。"""
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.store import STORE, now_iso

RESIDENT_TOKEN = "demo-token-vincent"
VENDOR_CLEANING = ("vendor1@demo.local", "vendor1234")  # service_vendor_id = 1
VENDOR_PLUMBING = ("vendor11@demo.local", "vendor1234")  # service_vendor_id = 11

AC_CLEANING_FORM = {
    "quantity": 2,
    "preferred_date": "2026-08-01",
    "preferred_time_slot": "MORNING",
    "address": "台北市信義區市府路1號",
    "phone": "0912345678",
}


@pytest.fixture
def client():
    return TestClient(app)


def vendor_token(client: TestClient, account: tuple[str, str]) -> str:
    email, password = account
    res = client.post("/api/vendor/login", json={"email": email, "password": password})
    assert res.status_code == 200, res.text
    return res.json()["token"]


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def submit_air_conditioner_request(client: TestClient) -> str:
    res = client.post(
        "/api/services/air_conditioner_cleaning/requests",
        json={"payload": AC_CLEANING_FORM},
        headers=auth(RESIDENT_TOKEN),
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["success"], body
    return body["request_id"]


def test_vendor_sees_only_own_service_vendor_id(client):
    request_id = submit_air_conditioner_request(client)

    cleaning = client.get("/api/vendor/requests", headers=auth(vendor_token(client, VENDOR_CLEANING)))
    assert cleaning.status_code == 200
    assert request_id in [item["request_id"] for item in cleaning.json()["items"]]

    plumbing = client.get("/api/vendor/requests", headers=auth(vendor_token(client, VENDOR_PLUMBING)))
    assert plumbing.status_code == 200
    assert request_id not in [item["request_id"] for item in plumbing.json()["items"]]


def test_vendor_cannot_open_another_vendors_request(client):
    request_id = submit_air_conditioner_request(client)
    res = client.get(
        f"/api/vendor/requests/{request_id}",
        headers=auth(vendor_token(client, VENDOR_PLUMBING)),
    )
    assert res.status_code == 404


def test_vendor_list_carries_customer_and_summary(client):
    request_id = submit_air_conditioner_request(client)
    res = client.get("/api/vendor/requests", headers=auth(vendor_token(client, VENDOR_CLEANING)))
    item = next(i for i in res.json()["items"] if i["request_id"] == request_id)
    assert item["customer_name"] == "Vincent"
    assert item["status_label"] == "等待廠商確認"
    assert "台北市信義區市府路1號" in item["summary"]
    assert "上午" in item["summary"]  # MORNING 轉成中文標籤


def test_vendor_detail_lists_form_fields_in_schema_order(client):
    request_id = submit_air_conditioner_request(client)
    res = client.get(
        f"/api/vendor/requests/{request_id}",
        headers=auth(vendor_token(client, VENDOR_CLEANING)),
    )
    assert res.status_code == 200
    fields = res.json()["fields"]
    assert [f["id"] for f in fields] == list(AC_CLEANING_FORM)
    assert dict(zip([f["id"] for f in fields], [f["value"] for f in fields]))["phone"] == "0912345678"


def test_status_change_propagates_to_vendor_list(client):
    request_id = submit_air_conditioner_request(client)
    token = vendor_token(client, VENDOR_CLEANING)

    pending = client.get("/api/vendor/requests?scope=pending", headers=auth(token))
    assert request_id in [i["request_id"] for i in pending.json()["items"]]

    confirmed = client.post(
        f"/api/requests/{request_id}/simulate/CONFIRMED", headers=auth(RESIDENT_TOKEN)
    )
    assert confirmed.status_code == 200

    orders = client.get("/api/vendor/requests?scope=orders", headers=auth(token))
    order = next(i for i in orders.json()["items"] if i["request_id"] == request_id)
    assert order["status"] == "CONFIRMED"
    pending_after = client.get("/api/vendor/requests?scope=pending", headers=auth(token))
    assert request_id not in [i["request_id"] for i in pending_after.json()["items"]]


def test_unsubmitted_draft_is_hidden_from_vendor(client):
    request_id = "REQ-DRAFT-TEST"
    STORE.save_request(
        "user-vincent",
        {
            "request_id": request_id,
            "session_id": None,
            "service_id": "air_conditioner_cleaning",
            "service_name": "冷氣清洗",
            "service_vendor_id": 1,
            "status": "DRAFT",
            "form_data": AC_CLEANING_FORM,
            "created_at": now_iso(),
        },
    )
    res = client.get("/api/vendor/requests", headers=auth(vendor_token(client, VENDOR_CLEANING)))
    assert request_id not in [i["request_id"] for i in res.json()["items"]]


def test_resident_token_is_rejected_by_vendor_api(client):
    res = client.get("/api/vendor/requests", headers=auth(RESIDENT_TOKEN))
    assert res.status_code == 403
    assert res.json()["detail"]["error"]["code"] == "VENDOR_FORBIDDEN"


def test_vendor_token_is_rejected_by_resident_api(client):
    res = client.get("/api/requests", headers=auth(vendor_token(client, VENDOR_CLEANING)))
    assert res.status_code == 403
    assert res.json()["detail"]["error"]["code"] == "VENDOR_ACCOUNT_NOT_ALLOWED"


def test_vendor_login_rejects_wrong_password(client):
    res = client.post(
        "/api/vendor/login", json={"email": VENDOR_CLEANING[0], "password": "wrong-password"}
    )
    assert res.status_code == 401


def test_vendor_login_rejects_unknown_email(client):
    res = client.post(
        "/api/vendor/login", json={"email": "nobody@demo.local", "password": "vendor1234"}
    )
    assert res.status_code == 401
