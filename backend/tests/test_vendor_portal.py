"""廠商後台：資料隔離、清單可見性，以及接單／拒單的狀態機與樂觀鎖。"""
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.store import STORE, now_iso

RESIDENT_TOKEN = "demo-token-vincent"
VENDOR_CLEANING = ("vendor1@demo.local", "vendor1234")  # service_vendor_id = 1
VENDOR_PLUMBING = ("vendor11@demo.local", "vendor1234")  # service_vendor_id = 11
VENDOR_RESERVATION = ("vendor22@demo.local", "vendor1234")  # service_vendor_id = 22

AC_CLEANING_FORM = {
    "quantity": 2,
    "air_conditioner_type": "WALL_MOUNTED",
    "antibacterial_film_addon": "NO",
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


def vendor_detail(client: TestClient, token: str, request_id: str) -> dict:
    res = client.get(f"/api/vendor/requests/{request_id}", headers=auth(token))
    assert res.status_code == 200, res.text
    return res.json()


def vendor_act(client: TestClient, token: str, request_id: str, action: str, version: int):
    return client.post(
        f"/api/vendor/requests/{request_id}/{action}",
        json={"version": version},
        headers=auth(token),
    )


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
    # 地址在清單上只到行政區（Milestone 15），完整門牌要開明細解密才看得到。
    assert "台北市信義區…" in item["summary"]
    assert "市府路1號" not in item["summary"]
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
    phone = next(f for f in fields if f["id"] == "phone")
    # 明細也只給遮罩值；完整號碼走 /contact（見 test_contact_privacy.py）。
    assert phone["value"] == "0912***678"
    assert phone["masked"] is True


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


# ---- 接單／拒單：狀態機 + 樂觀鎖 ----


def test_accept_moves_request_from_pending_to_orders(client):
    request_id = submit_air_conditioner_request(client)
    token = vendor_token(client, VENDOR_CLEANING)
    detail = vendor_detail(client, token, request_id)
    assert detail["available_actions"] == ["accept", "reject"]

    res = vendor_act(client, token, request_id, "accept", detail["version"])
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["status"] == "CONFIRMED"
    assert body["status_label"] == "已確認"
    assert body["version"] == detail["version"] + 1
    assert body["available_actions"] == ["start"]  # 接單後可以開始服務

    orders = client.get("/api/vendor/requests?scope=orders", headers=auth(token))
    assert request_id in [i["request_id"] for i in orders.json()["items"]]
    pending = client.get("/api/vendor/requests?scope=pending", headers=auth(token))
    assert request_id not in [i["request_id"] for i in pending.json()["items"]]


def test_accept_is_visible_to_the_resident(client):
    request_id = submit_air_conditioner_request(client)
    token = vendor_token(client, VENDOR_CLEANING)
    vendor_act(client, token, request_id, "accept", vendor_detail(client, token, request_id)["version"])

    res = client.get(f"/api/requests/{request_id}", headers=auth(RESIDENT_TOKEN))
    assert res.json()["status"] == "CONFIRMED"


def test_reject_closes_the_request(client):
    request_id = submit_air_conditioner_request(client)
    token = vendor_token(client, VENDOR_CLEANING)
    version = vendor_detail(client, token, request_id)["version"]

    res = vendor_act(client, token, request_id, "reject", version)
    assert res.status_code == 200, res.text
    assert res.json()["status"] == "REJECTED"
    assert res.json()["status_label"] == "廠商已婉拒"

    all_items = client.get("/api/vendor/requests?scope=all", headers=auth(token)).json()["items"]
    assert request_id in [i["request_id"] for i in all_items]  # 全部分頁仍看得到
    pending = client.get("/api/vendor/requests?scope=pending", headers=auth(token)).json()["items"]
    assert request_id not in [i["request_id"] for i in pending]
    # 已婉拒是終點狀態，住戶端也不能再取消
    cancel = client.post(f"/api/requests/{request_id}/cancel", headers=auth(RESIDENT_TOKEN))
    assert cancel.status_code == 409


def test_second_accept_with_the_same_version_is_rejected(client):
    """重複送出（連點兩下、重整後再按）不會重跑一次狀態切換。"""
    request_id = submit_air_conditioner_request(client)
    token = vendor_token(client, VENDOR_CLEANING)
    version = vendor_detail(client, token, request_id)["version"]

    assert vendor_act(client, token, request_id, "accept", version).status_code == 200

    replay = vendor_act(client, token, request_id, "accept", version)
    assert replay.status_code == 409
    error = replay.json()["detail"]["error"]
    assert error["code"] == "REQUEST_STATUS_CONFLICT"
    # 錯誤訊息帶著案件現況，前端可以直接更新畫面
    assert error["status"] == "CONFIRMED"
    assert error["version"] == version + 1


def test_stale_version_is_rejected_even_when_the_status_still_allows_it(client):
    """狀態沒變但案件被改過（表單更新等）時，舊版本一樣不能寫入。"""
    request_id = submit_air_conditioner_request(client)
    token = vendor_token(client, VENDOR_CLEANING)
    stale_version = vendor_detail(client, token, request_id)["version"]

    request = STORE.get_request("user-vincent", request_id)
    STORE.save_request("user-vincent", request)  # 狀態仍是 SUBMITTED，但版本前進一號

    res = vendor_act(client, token, request_id, "accept", stale_version)
    assert res.status_code == 409
    assert res.json()["detail"]["error"]["code"] == "REQUEST_VERSION_CONFLICT"
    assert STORE.get_request("user-vincent", request_id)["status"] == "SUBMITTED"

    fresh = vendor_detail(client, token, request_id)["version"]
    assert vendor_act(client, token, request_id, "accept", fresh).status_code == 200


def test_concurrent_accept_and_reject_only_one_wins(client):
    request_id = submit_air_conditioner_request(client)
    token = vendor_token(client, VENDOR_CLEANING)
    version = vendor_detail(client, token, request_id)["version"]

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = [
            f.result()
            for f in [
                pool.submit(vendor_act, client, token, request_id, action, version)
                for action in ("accept", "reject")
            ]
        ]

    codes = sorted(r.status_code for r in results)
    assert codes == [200, 409]
    winner = next(r for r in results if r.status_code == 200).json()
    assert STORE.get_request("user-vincent", request_id)["status"] == winner["status"]


def test_cancelled_request_cannot_be_accepted(client):
    request_id = submit_air_conditioner_request(client)
    token = vendor_token(client, VENDOR_CLEANING)
    version = vendor_detail(client, token, request_id)["version"]

    assert client.post(
        f"/api/requests/{request_id}/cancel", headers=auth(RESIDENT_TOKEN)
    ).status_code == 200

    res = vendor_act(client, token, request_id, "accept", version)
    assert res.status_code == 409
    assert res.json()["detail"]["error"]["code"] == "REQUEST_STATUS_CONFLICT"
    assert STORE.get_request("user-vincent", request_id)["status"] == "CANCELLED"


def test_vendor_cannot_act_on_another_vendors_request(client):
    request_id = submit_air_conditioner_request(client)
    version = vendor_detail(client, vendor_token(client, VENDOR_CLEANING), request_id)["version"]

    res = vendor_act(client, vendor_token(client, VENDOR_PLUMBING), request_id, "accept", version)
    assert res.status_code == 404
    assert STORE.get_request("user-vincent", request_id)["status"] == "SUBMITTED"


def test_unknown_action_is_rejected(client):
    request_id = submit_air_conditioner_request(client)
    token = vendor_token(client, VENDOR_CLEANING)
    res = vendor_act(client, token, request_id, "explode", 1)
    assert res.status_code == 422


def test_resident_token_cannot_accept(client):
    request_id = submit_air_conditioner_request(client)
    res = vendor_act(client, RESIDENT_TOKEN, request_id, "accept", 1)
    assert res.status_code == 403


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


def test_vendor_advances_full_lifecycle_for_generic_service(client):
    request_id = submit_air_conditioner_request(client)
    token = vendor_token(client, VENDOR_CLEANING)

    accept = vendor_act(client, token, request_id, "accept", vendor_detail(client, token, request_id)["version"])
    assert accept.status_code == 200, accept.text
    assert accept.json()["available_actions"] == ["start"]

    start = vendor_act(client, token, request_id, "start", accept.json()["version"])
    assert start.status_code == 200, start.text
    assert start.json()["status"] == "IN_PROGRESS"
    assert start.json()["available_actions"] == ["complete"]

    complete = vendor_act(client, token, request_id, "complete", start.json()["version"])
    assert complete.status_code == 200, complete.text
    assert complete.json()["status"] == "COMPLETED"
    # 冷氣清洗沒有核銷概念，完工後沒有可再做的動作
    assert complete.json()["available_actions"] == []


def test_verify_action_is_only_available_for_restaurant_reservation(client):
    request_id = submit_air_conditioner_request(client)
    token = vendor_token(client, VENDOR_CLEANING)
    version = vendor_detail(client, token, request_id)["version"]

    for action in ("accept", "start", "complete"):
        res = vendor_act(client, token, request_id, action, version)
        assert res.status_code == 200, res.text
        version = res.json()["version"]

    verify = vendor_act(client, token, request_id, "verify", version)
    assert verify.status_code == 409
    assert verify.json()["detail"]["error"]["code"] == "REQUEST_STATUS_CONFLICT"


def test_reservation_vendor_can_verify_after_completion(client):
    submitted = client.post(
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
        headers=auth(RESIDENT_TOKEN),
    ).json()
    assert submitted["status"] == "PENDING_PROVIDER"
    request_id = submitted["request_id"]

    token = vendor_token(client, VENDOR_RESERVATION)
    version = vendor_detail(client, token, request_id)["version"]
    for action, expected_order_status in (("accept", "03"), ("start", "04"), ("complete", "70")):
        step = vendor_act(client, token, request_id, action, version)
        assert step.status_code == 200, step.text
        version = step.json()["version"]

    verify = vendor_act(client, token, request_id, "verify", version)
    assert verify.status_code == 200, verify.text
    assert verify.json()["status"] == "VERIFIED"
    assert verify.json()["available_actions"] == []

    order = client.get(f"/api/reservations/{request_id}", headers=auth(RESIDENT_TOKEN)).json()
    assert order["order_status"] == "80"
    assert order["status_history"][-1]["status"] == "80"
