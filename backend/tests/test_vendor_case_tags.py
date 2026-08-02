"""廠商案件標籤（P1 V5 案件分類與標籤）：正規化、資料隔離，以及不干擾案件本體。"""
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.case_tags import MAX_TAGS, TagError, normalize_tags

RESIDENT_TOKEN = "demo-token-vincent"
VENDOR_CLEANING = ("vendor1@demo.local", "vendor1234")  # service_vendor_id = 1
VENDOR_PLUMBING = ("vendor11@demo.local", "vendor1234")  # service_vendor_id = 11

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


def vendor_token(client: TestClient, account: tuple[str, str]) -> str:
    email, password = account
    res = client.post("/api/vendor/login", json={"email": email, "password": password})
    assert res.status_code == 200, res.text
    return res.json()["token"]


def submit_request(client: TestClient) -> str:
    res = client.post(
        "/api/services/air_conditioner_cleaning/requests",
        json={"payload": AC_CLEANING_FORM},
        headers=auth(RESIDENT_TOKEN),
    )
    assert res.status_code == 200, res.text
    return res.json()["request_id"]


def put_tags(client: TestClient, token: str, request_id: str, tags: list[str]):
    return client.put(
        f"/api/vendor/case-tags/{request_id}", json={"tags": tags}, headers=auth(token)
    )


def error_code(res) -> str:
    return res.json()["detail"]["error"]["code"]


# ---- normalize_tags 單元 ----


def test_normalize_trims_drops_blanks_and_dedupes_preserving_order():
    assert normalize_tags(["  急件 ", "", "   ", "待報價", "急件"]) == ["急件", "待報價"]


def test_normalize_rejects_overlong_tag():
    with pytest.raises(TagError) as e:
        normalize_tags(["這個標籤實在是有夠長根本放不進清單"])
    assert e.value.code == "TAG_TOO_LONG"


def test_normalize_rejects_too_many_tags():
    with pytest.raises(TagError) as e:
        normalize_tags([f"標籤{i}" for i in range(MAX_TAGS + 1)])
    assert e.value.code == "TOO_MANY_TAGS"


# ---- API ----


def test_put_then_read_back_tags(client):
    request_id = submit_request(client)
    token = vendor_token(client, VENDOR_CLEANING)

    res = put_tags(client, token, request_id, ["急件", "大型案件"])
    assert res.status_code == 200, res.text
    assert res.json() == {"success": True, "request_id": request_id, "tags": ["急件", "大型案件"]}

    single = client.get(f"/api/vendor/case-tags/{request_id}", headers=auth(token))
    assert single.status_code == 200
    assert single.json()["tags"] == ["急件", "大型案件"]

    listed = client.get("/api/vendor/case-tags", headers=auth(token))
    assert listed.status_code == 200
    assert listed.json()["tags"][request_id] == ["急件", "大型案件"]


def test_put_normalizes_before_storing(client):
    request_id = submit_request(client)
    token = vendor_token(client, VENDOR_CLEANING)

    res = put_tags(client, token, request_id, [" 待報價 ", "待報價", ""])
    assert res.status_code == 200, res.text
    assert res.json()["tags"] == ["待報價"]


def test_empty_list_clears_the_tags(client):
    request_id = submit_request(client)
    token = vendor_token(client, VENDOR_CLEANING)
    put_tags(client, token, request_id, ["急件"])

    res = put_tags(client, token, request_id, [])
    assert res.status_code == 200, res.text
    assert res.json()["tags"] == []
    # 清空後就從清單字典裡消失，不留一筆空標籤的殼。
    assert request_id not in client.get("/api/vendor/case-tags", headers=auth(token)).json()["tags"]


def test_untagged_case_reads_as_empty(client):
    request_id = submit_request(client)
    token = vendor_token(client, VENDOR_CLEANING)
    res = client.get(f"/api/vendor/case-tags/{request_id}", headers=auth(token))
    assert res.status_code == 200
    assert res.json()["tags"] == []


def test_overlong_and_overcount_tags_are_rejected_with_a_readable_message(client):
    request_id = submit_request(client)
    token = vendor_token(client, VENDOR_CLEANING)

    too_long = put_tags(client, token, request_id, ["這個標籤實在是有夠長根本放不進清單"])
    assert too_long.status_code == 400
    assert error_code(too_long) == "TAG_TOO_LONG"

    too_many = put_tags(client, token, request_id, [f"標籤{i}" for i in range(MAX_TAGS + 1)])
    assert too_many.status_code == 400
    assert error_code(too_many) == "TOO_MANY_TAGS"


def test_tags_are_private_to_the_vendor_that_wrote_them(client):
    request_id = submit_request(client)
    cleaning = vendor_token(client, VENDOR_CLEANING)
    plumbing = vendor_token(client, VENDOR_PLUMBING)
    put_tags(client, cleaning, request_id, ["急件"])

    # 別家廠商連這張單都看不到，遑論它的標籤。
    assert client.get(f"/api/vendor/case-tags/{request_id}", headers=auth(plumbing)).status_code == 404
    assert put_tags(client, plumbing, request_id, ["亂貼"]).status_code == 404
    assert client.get("/api/vendor/case-tags", headers=auth(plumbing)).json()["tags"] == {}


def test_tags_require_a_vendor_token(client):
    request_id = submit_request(client)
    assert client.get("/api/vendor/case-tags").status_code == 401
    # 住戶登入是有效身分但不是廠商，所以是 403（拒絕）而不是 401（沒登入）。
    assert (
        client.put(
            f"/api/vendor/case-tags/{request_id}",
            json={"tags": ["急件"]},
            headers=auth(RESIDENT_TOKEN),
        ).status_code
        == 403
    )


def test_tagging_does_not_touch_the_case_itself(client):
    """標籤是廠商的內部註記：不推進案件版本、不出現在住戶端。"""
    request_id = submit_request(client)
    token = vendor_token(client, VENDOR_CLEANING)
    before = client.get(f"/api/vendor/requests/{request_id}", headers=auth(token)).json()

    put_tags(client, token, request_id, ["急件"])

    after = client.get(f"/api/vendor/requests/{request_id}", headers=auth(token)).json()
    assert after["version"] == before["version"]
    assert after["updated_at"] == before["updated_at"]
    # 貼完標籤後樂觀鎖仍以原本的版本為準，接單不會被自己的標籤擋下。
    accepted = client.post(
        f"/api/vendor/requests/{request_id}/accept",
        json={"version": before["version"]},
        headers=auth(token),
    )
    assert accepted.status_code == 200, accepted.text

    resident = client.get(f"/api/requests/{request_id}", headers=auth(RESIDENT_TOKEN))
    assert resident.status_code == 200
    assert "急件" not in resident.text
