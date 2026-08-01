import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.api import vendor_delivery
from backend.app.services import delivery, store as store_module


@pytest.fixture(autouse=True)
def isolated_store(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        test_store = store_module.MemoryStore(storage_path=Path(tmp) / "store.json")
        monkeypatch.setattr(store_module, "STORE", test_store)
        monkeypatch.setattr(delivery, "STORE", test_store)
        # vendor_delivery.py 直接引用 STORE（不是全部透過 delivery.py 的 service 函式），
        # 這個名字也要單獨換掉，否則廠商端點還是打到沒被隔離的預設 STORE。
        monkeypatch.setattr(vendor_delivery, "STORE", test_store)
        yield test_store


def _resident_headers(client: TestClient) -> dict:
    accounts = client.get("/api/auth/demo-accounts").json()["accounts"]
    return {"Authorization": f"Bearer {accounts[0]['token']}"}


def _vendor_headers(client: TestClient) -> dict:
    login = client.post(
        "/api/vendor/login", json={"email": "vendor30@demo.local", "password": "vendor1234"}
    ).json()
    return {"Authorization": f"Bearer {login['token']}"}


def _create_order(client: TestClient, headers: dict) -> dict:
    return client.post(
        "/api/delivery/submit",
        json={
            "address": {
                "lat": 25.033, "lng": 121.565,
                "city": "台北市", "area": "大安區", "street": "忠孝東路四段100號",
                "remark": "", "contact_name": "王小明", "phone": "0912345678",
            },
            "goods": [{"id": "item-001", "title": "招牌雞腿便當", "price": 110, "quantity": 1}],
            "store_id": "store-001",
            "store_name": "好味道便當",
            "store_address": "台北市大安區忠孝東路四段100號",
        },
        headers=headers,
    ).json()


def test_new_delivery_order_is_visible_in_pending_scope():
    client = TestClient(app)
    headers = _resident_headers(client)
    created = _create_order(client, headers)
    vendor_headers = _vendor_headers(client)

    res = client.get("/api/vendor/delivery-orders?scope=pending", headers=vendor_headers)
    assert res.status_code == 200
    assert created["request_id"] in [i["request_id"] for i in res.json()["items"]]


def test_vendor_advances_delivery_order_through_full_lifecycle():
    client = TestClient(app)
    headers = _resident_headers(client)
    created = _create_order(client, headers)
    vendor_headers = _vendor_headers(client)

    detail = client.get(
        f"/api/vendor/delivery-orders/{created['request_id']}", headers=vendor_headers
    ).json()
    assert detail["available_actions"] == ["accept", "reject"]
    version = detail["version"]

    for action in ("accept", "prepare", "pickup", "dispatch", "deliver"):
        res = client.post(
            f"/api/vendor/delivery-orders/{created['request_id']}/{action}",
            json={"version": version},
            headers=vendor_headers,
        )
        assert res.status_code == 200, res.text
        version = res.json()["version"]

    final = client.get(
        f"/api/vendor/delivery-orders/{created['request_id']}", headers=vendor_headers
    ).json()
    assert final["status_label"] == "已送達"
    assert final["available_actions"] == []

    order = client.get(f"/api/delivery/orders/{created['request_id']}", headers=headers).json()
    assert order["status"] == "COMPLETED"
    assert order["order_status"] == "70"


def test_reject_is_blocked_after_pickup():
    client = TestClient(app)
    headers = _resident_headers(client)
    created = _create_order(client, headers)
    vendor_headers = _vendor_headers(client)

    version = client.get(
        f"/api/vendor/delivery-orders/{created['request_id']}", headers=vendor_headers
    ).json()["version"]
    for action in ("accept", "prepare", "pickup"):
        res = client.post(
            f"/api/vendor/delivery-orders/{created['request_id']}/{action}",
            json={"version": version},
            headers=vendor_headers,
        )
        assert res.status_code == 200, res.text
        version = res.json()["version"]

    reject = client.post(
        f"/api/vendor/delivery-orders/{created['request_id']}/reject",
        json={"version": version},
        headers=vendor_headers,
    )
    assert reject.status_code == 409
    assert reject.json()["detail"]["error"]["code"] == "REQUEST_STATUS_CONFLICT"


def test_customer_token_is_rejected_by_delivery_vendor_api():
    client = TestClient(app)
    res = client.get("/api/vendor/delivery-orders", headers=_resident_headers(client))
    assert res.status_code == 403


def test_list_and_detail_show_masked_contact_not_plaintext():
    client = TestClient(app)
    headers = _resident_headers(client)
    created = _create_order(client, headers)
    vendor_headers = _vendor_headers(client)

    items = client.get("/api/vendor/delivery-orders?scope=pending", headers=vendor_headers).json()["items"]
    item = next(i for i in items if i["request_id"] == created["request_id"])
    assert item["customer_name"] == "王○明"

    detail = client.get(
        f"/api/vendor/delivery-orders/{created['request_id']}", headers=vendor_headers
    ).json()
    assert detail["customer_name"] == "王○明"
    assert detail["has_contact"] is True
    contact_fields = {f["id"]: f for f in detail["fields"] if f["masked"]}
    assert contact_fields["contact_name"]["value"] == "王○明"
    assert contact_fields["phone"]["value"] == "0912***678"
    # 地址遮罩只留到縣市區，門牌號碼（"忠孝東路四段100號"）不能出現在遮罩值裡
    assert contact_fields["address"]["value"] == "台北市大安區"
    assert "忠孝東路" not in contact_fields["address"]["value"]
    assert detail["contact_access_log"] == []


def test_reveal_contact_returns_full_value_and_logs_access():
    client = TestClient(app)
    headers = _resident_headers(client)
    created = _create_order(client, headers)
    vendor_headers = _vendor_headers(client)

    res = client.post(
        f"/api/vendor/delivery-orders/{created['request_id']}/contact", headers=vendor_headers
    )
    assert res.status_code == 200, res.text
    body = res.json()
    contact = {c["id"]: c["value"] for c in body["contact"]}
    assert contact["contact_name"] == "王小明"
    assert contact["phone"] == "0912345678"
    assert "忠孝東路四段100號" in contact["address"]
    assert len(body["contact_access_log"]) == 1
    assert body["contact_access_log"][0]["fields"] == ["收件人", "聯絡電話", "外送地址"]

    detail = client.get(
        f"/api/vendor/delivery-orders/{created['request_id']}", headers=vendor_headers
    ).json()
    assert len(detail["contact_access_log"]) == 1
    # 明細本身還是遮罩值——reveal 是另外一個明確動作，不會讓明細預設就變成明文
    assert detail["customer_name"] == "王○明"


def test_reveal_contact_rejects_other_vendors():
    client = TestClient(app)
    headers = _resident_headers(client)
    created = _create_order(client, headers)

    # 用通用案件的示範廠商帳號（不是 vendor30）嘗試看這張外送單的聯絡資訊
    login = client.post(
        "/api/vendor/login", json={"email": "vendor1@demo.local", "password": "vendor1234"}
    ).json()
    other_vendor_headers = {"Authorization": f"Bearer {login['token']}"}

    res = client.post(
        f"/api/vendor/delivery-orders/{created['request_id']}/contact", headers=other_vendor_headers
    )
    assert res.status_code == 404
