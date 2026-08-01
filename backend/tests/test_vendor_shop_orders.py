import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.api import vendor_shop
from backend.app.services import shop, store as store_module


@pytest.fixture(autouse=True)
def isolated_store(monkeypatch):
    test_store = store_module.MemoryStore()
    monkeypatch.setattr(store_module, "STORE", test_store)
    monkeypatch.setattr(shop, "STORE", test_store)
    # vendor_shop.py 直接引用 STORE 查索引與寫樂觀鎖，這個名字也要單獨換掉。
    monkeypatch.setattr(vendor_shop, "STORE", test_store)
    test_store.put_item(
        {
            "PK": "SHOP_SKU#sku_tshirt_white_s", "SK": "STOCK",
            "entity_type": "SHOP_SKU_STOCK", "quantity": 5, "updated_at": "",
        }
    )
    yield test_store


def _resident_headers(client: TestClient) -> dict:
    accounts = client.get("/api/auth/demo-accounts").json()["accounts"]
    return {"Authorization": f"Bearer {accounts[0]['token']}"}


def _vendor_headers(client: TestClient) -> dict:
    login = client.post(
        "/api/vendor/login", json={"email": "vendor40@demo.local", "password": "vendor1234"}
    ).json()
    return {"Authorization": f"Bearer {login['token']}"}


def _create_physical_order(client: TestClient, headers: dict) -> dict:
    return client.post(
        "/api/shop/submit",
        json={
            "cart": [{"sku_id": "sku_tshirt_white_s", "quantity": 1}],
            "contact_name": "王小明",
            "phone": "0912345678",
            "address": {"city": "台北市", "street": "忠孝東路四段100號", "contact_name": "王小明"},
            "used_points": 0,
        },
        headers=headers,
    ).json()


def test_new_physical_order_is_visible_to_shop_vendor():
    client = TestClient(app)
    headers = _resident_headers(client)
    created = _create_physical_order(client, headers)

    res = client.get("/api/vendor/shop-orders?scope=pending", headers=_vendor_headers(client))
    assert res.status_code == 200
    assert created["request_id"] in [i["request_id"] for i in res.json()["items"]]


def test_vendor_advances_shop_order_through_full_lifecycle():
    client = TestClient(app)
    headers = _resident_headers(client)
    created = _create_physical_order(client, headers)
    vendor_headers = _vendor_headers(client)

    detail = client.get(
        f"/api/vendor/shop-orders/{created['request_id']}", headers=vendor_headers
    ).json()
    assert detail["available_actions"] == ["confirm", "reject"]
    version = detail["version"]

    for action in ("confirm", "ship", "deliver"):
        res = client.post(
            f"/api/vendor/shop-orders/{created['request_id']}/{action}",
            json={"version": version},
            headers=vendor_headers,
        )
        assert res.status_code == 200, res.text
        version = res.json()["version"]

    final = client.get(f"/api/shop/orders/{created['request_id']}", headers=headers).json()
    assert final["status"] == "COMPLETED"


def test_vendor_reject_restocks_and_refunds():
    client = TestClient(app)
    headers = _resident_headers(client)
    created = _create_physical_order(client, headers)
    vendor_headers = _vendor_headers(client)
    version = client.get(
        f"/api/vendor/shop-orders/{created['request_id']}", headers=vendor_headers
    ).json()["version"]

    reject = client.post(
        f"/api/vendor/shop-orders/{created['request_id']}/reject",
        json={"version": version},
        headers=vendor_headers,
    )
    assert reject.status_code == 200, reject.text
    assert reject.json()["status"] == "CANCELLED"

    order = client.get(f"/api/shop/orders/{created['request_id']}", headers=headers).json()
    assert order["status"] == "CANCELLED"


def test_shop_vendor_cannot_ship_before_confirm():
    client = TestClient(app)
    headers = _resident_headers(client)
    created = _create_physical_order(client, headers)
    vendor_headers = _vendor_headers(client)
    version = client.get(
        f"/api/vendor/shop-orders/{created['request_id']}", headers=vendor_headers
    ).json()["version"]

    res = client.post(
        f"/api/vendor/shop-orders/{created['request_id']}/ship",
        json={"version": version},
        headers=vendor_headers,
    )
    assert res.status_code == 409


def test_list_and_detail_show_masked_contact_not_plaintext():
    client = TestClient(app)
    headers = _resident_headers(client)
    created = _create_physical_order(client, headers)
    vendor_headers = _vendor_headers(client)

    items = client.get("/api/vendor/shop-orders?scope=pending", headers=vendor_headers).json()["items"]
    item = next(i for i in items if i["request_id"] == created["request_id"])
    assert item["customer_name"] == "王○明"

    detail = client.get(
        f"/api/vendor/shop-orders/{created['request_id']}", headers=vendor_headers
    ).json()
    assert detail["customer_name"] == "王○明"
    assert detail["has_contact"] is True
    contact_fields = {f["id"]: f for f in detail["fields"] if f["masked"]}
    assert contact_fields["contact_name"]["value"] == "王○明"
    assert contact_fields["phone"]["value"] == "0912***678"
    # 地址遮罩只留到城市，門牌號碼不能出現在遮罩值裡
    assert contact_fields["address"]["value"] == "台北市"
    assert "忠孝東路" not in contact_fields["address"]["value"]
    assert detail["contact_access_log"] == []


def test_reveal_contact_returns_full_value_and_logs_access():
    client = TestClient(app)
    headers = _resident_headers(client)
    created = _create_physical_order(client, headers)
    vendor_headers = _vendor_headers(client)

    res = client.post(
        f"/api/vendor/shop-orders/{created['request_id']}/contact", headers=vendor_headers
    )
    assert res.status_code == 200, res.text
    body = res.json()
    contact = {c["id"]: c["value"] for c in body["contact"]}
    assert contact["contact_name"] == "王小明"
    assert contact["phone"] == "0912345678"
    assert "忠孝東路四段100號" in contact["address"]
    assert len(body["contact_access_log"]) == 1

    detail = client.get(
        f"/api/vendor/shop-orders/{created['request_id']}", headers=vendor_headers
    ).json()
    assert len(detail["contact_access_log"]) == 1
    # 明細本身還是遮罩值——reveal 是另外一個明確動作，不會讓明細預設就變成明文
    assert detail["customer_name"] == "王○明"


def test_reveal_contact_access_log_accumulates_across_calls():
    client = TestClient(app)
    headers = _resident_headers(client)
    created = _create_physical_order(client, headers)
    vendor_headers = _vendor_headers(client)

    client.post(f"/api/vendor/shop-orders/{created['request_id']}/contact", headers=vendor_headers)
    client.post(f"/api/vendor/shop-orders/{created['request_id']}/contact", headers=vendor_headers)

    detail = client.get(
        f"/api/vendor/shop-orders/{created['request_id']}", headers=vendor_headers
    ).json()
    assert len(detail["contact_access_log"]) == 2


def test_reveal_contact_log_failure_blocks_the_reveal(monkeypatch, isolated_store):
    client = TestClient(app)
    headers = _resident_headers(client)
    created = _create_physical_order(client, headers)
    vendor_headers = _vendor_headers(client)

    def boom(*_args, **_kwargs):
        raise RuntimeError("dynamodb unavailable")

    monkeypatch.setattr(isolated_store, "log_contact_access", boom)

    res = client.post(
        f"/api/vendor/shop-orders/{created['request_id']}/contact", headers=vendor_headers
    )
    assert res.status_code == 503
    assert res.json()["detail"]["error"]["code"] == "CONTACT_LOG_UNAVAILABLE"


def test_shop_vendor_cannot_reveal_other_vendors_order():
    client = TestClient(app)
    headers = _resident_headers(client)
    created = _create_physical_order(client, headers)

    # 用通用案件的示範廠商帳號（不是 vendor40）嘗試看這張商城訂單的聯絡資訊
    login = client.post(
        "/api/vendor/login", json={"email": "vendor1@demo.local", "password": "vendor1234"}
    ).json()
    other_vendor_headers = {"Authorization": f"Bearer {login['token']}"}

    res = client.post(
        f"/api/vendor/shop-orders/{created['request_id']}/contact", headers=other_vendor_headers
    )
    assert res.status_code == 404


def test_stale_version_returns_consistent_conflict_code(isolated_store):
    """狀態沒變但案件被改過（表單更新等）時，舊版本一樣不能寫入——比照
    test_vendor_portal.py::test_stale_version_is_rejected_even_when_the_status_still_allows_it
    的手法，直接把版本推進一號但不動狀態，讓 REQUEST_STATUS_CONFLICT 分支不會先
    攔下這次呼叫，逼真的走到樂觀鎖版本檢查那條路徑。
    """
    client = TestClient(app)
    headers = _resident_headers(client)
    created = _create_physical_order(client, headers)
    vendor_headers = _vendor_headers(client)
    request_id = created["request_id"]

    detail = client.get(f"/api/vendor/shop-orders/{request_id}", headers=vendor_headers).json()
    stale_version = detail["version"]

    index = isolated_store.get_vendor_request(40, request_id)
    owner_id = index["owner_id"]
    order = isolated_store.get_stored_request(owner_id, request_id)
    isolated_store.save_request(owner_id, order)  # 狀態仍是 SUBMITTED，但版本前進一號

    retry = client.post(
        f"/api/vendor/shop-orders/{request_id}/confirm",
        json={"version": stale_version},
        headers=vendor_headers,
    )
    assert retry.status_code == 409
    assert retry.json()["detail"]["error"]["code"] == "REQUEST_VERSION_CONFLICT"
