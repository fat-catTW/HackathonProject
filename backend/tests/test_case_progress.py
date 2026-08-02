"""V8 服務進度追蹤：已聯繫／已報價／施工中／已完成的推進、報價金額與住戶端進度條。"""
import pytest
from fastapi.testclient import TestClient

from backend.app.api.vendor import _available_actions
from backend.app.main import app
from backend.app.services.statuses import build_progress, progress_chain
from backend.app.services.store import STORE, now_iso

RESIDENT_TOKEN = "demo-token-vincent"
VENDOR_CLEANING = ("vendor1@demo.local", "vendor1234")  # service_vendor_id = 1

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


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def vendor_token(client: TestClient) -> str:
    email, password = VENDOR_CLEANING
    res = client.post("/api/vendor/login", json={"email": email, "password": password})
    assert res.status_code == 200, res.text
    return res.json()["token"]


def submit(client: TestClient) -> str:
    res = client.post(
        "/api/services/air_conditioner_cleaning/requests",
        json={"payload": AC_CLEANING_FORM},
        headers=auth(RESIDENT_TOKEN),
    )
    assert res.status_code == 200, res.text
    return res.json()["request_id"]


def act(client: TestClient, token: str, request_id: str, action: str, version: int, **body):
    return client.post(
        f"/api/vendor/requests/{request_id}/{action}",
        json={"version": version, **body},
        headers=auth(token),
    )


def version_of_case(client: TestClient, token: str, request_id: str) -> int:
    res = client.get(f"/api/vendor/requests/{request_id}", headers=auth(token))
    assert res.status_code == 200, res.text
    return res.json()["version"]


def resident_detail(client: TestClient, request_id: str) -> dict:
    res = client.get(f"/api/requests/{request_id}", headers=auth(RESIDENT_TOKEN))
    assert res.status_code == 200, res.text
    return res.json()


# ---- 狀態推進 ----


def test_vendor_walks_the_full_four_step_progression(client):
    request_id = submit(client)
    token = vendor_token(client)
    version = version_of_case(client, token, request_id)

    steps = [
        ("accept", {}, "CONFIRMED", "已確認"),
        ("contacted", {}, "CONTACTED", "已聯繫"),
        ("quote", {"amount": 3200}, "QUOTED", "已報價"),
        ("start", {}, "IN_PROGRESS", "服務進行中"),
        ("complete", {}, "COMPLETED", "已完成"),
    ]
    for action, body, expected_status, expected_label in steps:
        res = act(client, token, request_id, action, version, **body)
        assert res.status_code == 200, res.text
        assert res.json()["status"] == expected_status
        assert res.json()["status_label"] == expected_label
        version = res.json()["version"]

    assert res.json()["available_actions"] == []  # 冷氣清洗完工即結案


def test_quote_can_skip_the_contacted_step(client):
    """師傅第一通電話就在電話裡報好價：不該逼他先按一次「已聯繫」。"""
    request_id = submit(client)
    token = vendor_token(client)
    version = version_of_case(client, token, request_id)

    accepted = act(client, token, request_id, "accept", version)
    quoted = act(client, token, request_id, "quote", accepted.json()["version"], amount=1800)

    assert quoted.status_code == 200, quoted.text
    assert quoted.json()["status"] == "QUOTED"


def test_start_does_not_require_contacting_or_quoting(client):
    request_id = submit(client)
    token = vendor_token(client)
    version = version_of_case(client, token, request_id)

    accepted = act(client, token, request_id, "accept", version)
    started = act(client, token, request_id, "start", accepted.json()["version"])

    assert started.status_code == 200, started.text
    assert started.json()["status"] == "IN_PROGRESS"


def test_contacted_cannot_be_pressed_before_accepting(client):
    request_id = submit(client)
    token = vendor_token(client)
    version = version_of_case(client, token, request_id)

    res = act(client, token, request_id, "contacted", version)
    assert res.status_code == 409
    assert res.json()["detail"]["error"]["code"] == "REQUEST_STATUS_CONFLICT"
    assert STORE.get_request("user-vincent", request_id)["status"] == "SUBMITTED"


def test_a_case_in_the_middle_steps_stays_in_the_vendor_orders_tab(client):
    """已聯繫／已報價要留在「已接訂單」——漏掉的話廠商一按下去案件就從清單消失。"""
    request_id = submit(client)
    token = vendor_token(client)
    version = version_of_case(client, token, request_id)

    for action, body in (("accept", {}), ("contacted", {}), ("quote", {"amount": 2500})):
        res = act(client, token, request_id, action, version, **body)
        assert res.status_code == 200, res.text
        version = res.json()["version"]

        orders = client.get("/api/vendor/requests?scope=orders", headers=auth(token)).json()
        assert request_id in [i["request_id"] for i in orders["items"]]


# ---- 報價金額 ----


def test_quote_without_an_amount_is_rejected(client):
    """沒有金額的「已報價」對住戶毫無意義：狀態往前走了，畫面上卻沒有數字。"""
    request_id = submit(client)
    token = vendor_token(client)
    version = version_of_case(client, token, request_id)

    accepted = act(client, token, request_id, "accept", version)
    res = act(client, token, request_id, "quote", accepted.json()["version"])

    assert res.status_code == 400
    assert res.json()["detail"]["error"]["code"] == "QUOTE_AMOUNT_REQUIRED"
    # 金額檢查沒過就不該動到狀態
    assert STORE.get_request("user-vincent", request_id)["status"] == "CONFIRMED"


def test_absurd_quote_amount_is_rejected(client):
    request_id = submit(client)
    token = vendor_token(client)
    accepted = act(client, token, request_id, "accept", version_of_case(client, token, request_id))

    for amount in (0, -100, 99_999_999):
        res = act(client, token, request_id, "quote", accepted.json()["version"], amount=amount)
        assert res.status_code == 422, f"{amount} 應該被擋下"


def test_quote_amount_reaches_the_resident(client):
    request_id = submit(client)
    token = vendor_token(client)
    accepted = act(client, token, request_id, "accept", version_of_case(client, token, request_id))
    quoted = act(client, token, request_id, "quote", accepted.json()["version"], amount=3200)
    assert quoted.status_code == 200, quoted.text
    assert quoted.json()["quote_amount"] == 3200

    detail = resident_detail(client, request_id)
    assert detail["status"] == "QUOTED"
    assert detail["quote_amount"] == 3200

    listed = client.get("/api/requests", headers=auth(RESIDENT_TOKEN)).json()["items"]
    assert next(i for i in listed if i["request_id"] == request_id)["quote_amount"] == 3200


def test_quote_amount_survives_later_steps(client):
    """開工、完工之後住戶還是要看得到當初報的價。"""
    request_id = submit(client)
    token = vendor_token(client)
    version = version_of_case(client, token, request_id)

    for action, body in (
        ("accept", {}),
        ("quote", {"amount": 4500}),
        ("start", {}),
        ("complete", {}),
    ):
        res = act(client, token, request_id, action, version, **body)
        assert res.status_code == 200, res.text
        version = res.json()["version"]

    assert resident_detail(client, request_id)["quote_amount"] == 4500


def test_replayed_quote_with_a_stale_version_does_not_overwrite_the_amount(client):
    """連點兩下報價：第二次帶著舊版本，不該把金額改掉。"""
    request_id = submit(client)
    token = vendor_token(client)
    accepted = act(client, token, request_id, "accept", version_of_case(client, token, request_id))
    stale = accepted.json()["version"]

    assert act(client, token, request_id, "quote", stale, amount=3200).status_code == 200
    replay = act(client, token, request_id, "quote", stale, amount=9999)

    assert replay.status_code == 409
    assert STORE.get_request("user-vincent", request_id)["quote_amount"] == 3200


# ---- 住戶端進度條 ----


def test_progress_marks_each_step_as_the_vendor_advances(client):
    request_id = submit(client)
    token = vendor_token(client)
    version = version_of_case(client, token, request_id)

    fresh = resident_detail(client, request_id)["progress"]
    assert [s["status"] for s in fresh] == [
        "SUBMITTED",
        "CONFIRMED",
        "CONTACTED",
        "QUOTED",
        "IN_PROGRESS",
        "COMPLETED",
    ]
    assert [s["label"] for s in fresh] == [
        "已送出需求",
        "廠商已接單",
        "已聯繫",
        "已報價",
        "施工中",
        "已完成",
    ]
    # 剛送出：只有第一格走過，而且帶著送出時間
    assert [s["done"] for s in fresh] == [True, False, False, False, False, False]
    assert fresh[0]["at"]

    for action, body in (("accept", {}), ("contacted", {}), ("quote", {"amount": 2000})):
        res = act(client, token, request_id, action, version, **body)
        version = res.json()["version"]

    progress = resident_detail(client, request_id)["progress"]
    assert [s["done"] for s in progress] == [True, True, True, True, False, False]
    # 廠商按過的每一步都留下時間戳，還沒走到的沒有
    assert all(step["at"] for step in progress[:4])
    assert not any(step["at"] for step in progress[4:])


def test_progress_hides_the_quote_steps_for_services_without_quoting(client):
    """餐廳訂位當下就成交，硬畫「已報價」只會讓進度條卡在永遠不會亮的格子上。"""
    assert progress_chain("restaurant_reservation") == (
        "SUBMITTED",
        "CONFIRMED",
        "IN_PROGRESS",
        "COMPLETED",
    )
    assert "CONTACTED" in progress_chain("air_conditioner_cleaning")

    # 動作也一起收掉，廠商後台不會冒出按了必定 409 的按鈕
    assert _available_actions("CONFIRMED", "restaurant_reservation") == ["start"]


def test_progress_of_an_old_case_without_history_is_inferred_from_its_status():
    """這次才加的 progress_history，之前的案件沒有——進度條仍要畫對，只是沒有時間。"""
    steps = build_progress(
        {
            "service_id": "air_conditioner_cleaning",
            "status": "IN_PROGRESS",
            "created_at": "2026-07-30T09:00:00+08:00",
        }
    )
    assert [s["done"] for s in steps] == [True, True, True, True, True, False]
    assert steps[0]["at"] == "2026-07-30T09:00:00+08:00"
    assert steps[1]["at"] == ""


def test_progress_of_a_cancelled_case_stops_where_it_got_to(client):
    request_id = submit(client)
    token = vendor_token(client)
    accepted = act(client, token, request_id, "accept", version_of_case(client, token, request_id))
    assert accepted.status_code == 200, accepted.text

    assert client.post(
        f"/api/requests/{request_id}/cancel", headers=auth(RESIDENT_TOKEN)
    ).status_code == 200

    progress = resident_detail(client, request_id)["progress"]
    assert [s["status"] for s in progress][-1] == "CANCELLED"
    assert progress[-1]["label"] == "已取消"
    # 走到「廠商已接單」就中止了，後面的關卡不能算完成
    assert [s["done"] for s in progress] == [True, True, False, False, False, False, True]


def test_progress_of_a_draft_does_not_claim_it_was_submitted():
    steps = build_progress(
        {
            "service_id": "home_cleaning",
            "status": "DRAFT",
            "created_at": "2026-07-30T09:00:00+08:00",
        }
    )
    assert not any(step["done"] for step in steps)


def test_progress_history_does_not_pollute_the_reservation_status_history(client):
    """status_history 存的是餐廳／外送／商城的兩位數代碼，兩種字彙不能混在同一個陣列。"""
    request_id = submit(client)
    token = vendor_token(client)
    version = version_of_case(client, token, request_id)
    act(client, token, request_id, "accept", version)

    stored = STORE.get_request("user-vincent", request_id)
    assert [e["status"] for e in stored["progress_history"]] == ["CONFIRMED"]
    assert "status_history" not in stored


def test_unknown_progress_action_is_still_rejected(client):
    request_id = submit(client)
    token = vendor_token(client)
    # "contact" 是解密聯絡資訊的端點，不是狀態動作——別名寫錯不該默默推進案件。
    res = client.post(
        f"/api/vendor/requests/{request_id}/contact",
        json={"version": 1},
        headers=auth(token),
    )
    assert res.status_code in (200, 404)  # 走到 /contact 那條路由，不是狀態機
    assert STORE.get_request("user-vincent", request_id)["status"] == "SUBMITTED"


def test_case_saved_with_now_iso_timestamps_are_ordered(client):
    """進度歷程的時間戳必須遞增，前端才能照順序畫。"""
    request_id = submit(client)
    token = vendor_token(client)
    version = version_of_case(client, token, request_id)
    for action, body in (("accept", {}), ("contacted", {}), ("quote", {"amount": 1500})):
        res = act(client, token, request_id, action, version, **body)
        version = res.json()["version"]

    history = STORE.get_request("user-vincent", request_id)["progress_history"]
    assert [e["status"] for e in history] == ["CONFIRMED", "CONTACTED", "QUOTED"]
    assert [e["at"] for e in history] == sorted(e["at"] for e in history)
    assert history[0]["at"] <= now_iso()
