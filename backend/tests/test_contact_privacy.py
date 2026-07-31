"""聯絡資訊的加密儲存、遮罩顯示與解密存取紀錄（Milestone 15）。"""
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services import contact_privacy
from backend.app.services.store import STORE, now_iso

RESIDENT_TOKEN = "demo-token-vincent"
RESIDENT_SUB = "user-vincent"
VENDOR_CLEANING = ("vendor1@demo.local", "vendor1234")  # service_vendor_id = 1
VENDOR_PLUMBING = ("vendor11@demo.local", "vendor1234")  # service_vendor_id = 11

PHONE = "0912345678"
ADDRESS = "台北市信義區市府路1號"

AC_CLEANING_FORM = {
    "quantity": 2,
    "air_conditioner_type": "WALL_MOUNTED",
    "antibacterial_film_addon": "NO",
    "preferred_date": "2026-08-01",
    "preferred_time_slot": "MORNING",
    "address": ADDRESS,
    "phone": PHONE,
}


@pytest.fixture
def client():
    return TestClient(app)


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def vendor_token(client: TestClient, account: tuple[str, str] = VENDOR_CLEANING) -> str:
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


def reveal(client: TestClient, token: str, request_id: str):
    return client.post(f"/api/vendor/requests/{request_id}/contact", headers=auth(token))


# ---- 遮罩規則 ----


def test_masking_keeps_enough_to_be_useful_but_not_enough_to_reach_someone():
    assert contact_privacy.mask_value("phone", "0912345678") == "0912***678"
    assert contact_privacy.mask_value("address", ADDRESS) == "台北市信義區…"
    assert contact_privacy.mask_value("contact_name", "王小明") == "王○明"
    assert contact_privacy.mask_value("contact_name", "王明") == "王○"


def test_masking_hides_phone_numbers_too_short_to_partially_mask():
    assert contact_privacy.mask_value("phone", "1234") == "***"


def test_密文無法遮罩時整串蓋掉():
    encrypted = contact_privacy.encrypt_value(PHONE)
    assert contact_privacy.mask_value("phone", encrypted) == "***"


# ---- 加解密 ----


def test_encrypt_decrypt_round_trip():
    token = contact_privacy.encrypt_value(ADDRESS)
    assert token != ADDRESS
    assert contact_privacy.is_encrypted(token)
    assert contact_privacy.decrypt_value(token) == ADDRESS


def test_encrypting_twice_does_not_double_wrap():
    once = contact_privacy.encrypt_value(PHONE)
    assert contact_privacy.encrypt_value(once) == once


def test_plaintext_from_before_milestone_15_passes_through():
    # 舊資料沒有 enc: 前綴，解密要原樣放行而不是炸掉。
    assert contact_privacy.decrypt_value(PHONE) == PHONE


def test_undecryptable_value_keeps_the_ciphertext_instead_of_destroying_it():
    """解不開時保留密文——換成佔位字串會在下次寫回時把原始資料蓋掉。"""
    broken = "enc:v1:bm90LXJlYWxseS1jaXBoZXJ0ZXh0"
    plain = contact_privacy.decrypt_form_data({"phone": broken})
    assert plain["phone"] == broken


# ---- 儲存層 ----


def test_contact_fields_are_encrypted_at_rest(client):
    request_id = submit_request(client)

    stored = STORE.get_item(f"USER#{RESIDENT_SUB}", f"REQUEST#{request_id}")
    assert contact_privacy.is_encrypted(stored["form_data"]["phone"])
    assert contact_privacy.is_encrypted(stored["form_data"]["address"])
    # 非聯絡欄位維持原樣，廠商不解密也要看得到服務內容。
    assert stored["form_data"]["preferred_date"] == "2026-08-01"
    assert stored["form_data_masked"]["phone"] == "0912***678"


def test_vendor_index_mirror_is_encrypted_too(client):
    request_id = submit_request(client)
    index = STORE.get_item("VENDOR#1", f"REQUEST#{request_id}")
    assert contact_privacy.is_encrypted(index["form_data"]["phone"])
    assert index["form_data_masked"]["address"] == "台北市信義區…"


def test_resident_still_sees_their_own_contact_details(client):
    request_id = submit_request(client)
    res = client.get(f"/api/requests/{request_id}", headers=auth(RESIDENT_TOKEN))
    assert res.status_code == 200
    assert res.json()["form_data"]["phone"] == PHONE
    assert res.json()["form_data"]["address"] == ADDRESS


def test_status_changes_do_not_corrupt_the_encrypted_payload(client):
    """住戶改狀態會整包讀出再寫回；聯絡資訊不能在來回之間走鐘。"""
    request_id = submit_request(client)

    client.post(f"/api/requests/{request_id}/simulate/CONFIRMED", headers=auth(RESIDENT_TOKEN))
    client.post(f"/api/requests/{request_id}/simulate/IN_PROGRESS", headers=auth(RESIDENT_TOKEN))

    res = client.get(f"/api/requests/{request_id}", headers=auth(RESIDENT_TOKEN))
    assert res.json()["form_data"]["phone"] == PHONE
    stored = STORE.get_item(f"USER#{RESIDENT_SUB}", f"REQUEST#{request_id}")
    assert contact_privacy.is_encrypted(stored["form_data"]["phone"])


def test_vendor_accept_does_not_re_encrypt_or_lose_contact_details(client):
    request_id = submit_request(client)
    token = vendor_token(client)
    detail = client.get(f"/api/vendor/requests/{request_id}", headers=auth(token)).json()

    accepted = client.post(
        f"/api/vendor/requests/{request_id}/accept",
        json={"version": detail["version"]},
        headers=auth(token),
    )
    assert accepted.status_code == 200, accepted.text

    revealed = reveal(client, token, request_id)
    assert revealed.status_code == 200
    assert {c["id"]: c["value"] for c in revealed.json()["contact"]}["phone"] == PHONE


# ---- 廠商後台：遮罩與解密 ----


def test_vendor_detail_marks_contact_fields_and_masks_them(client):
    request_id = submit_request(client)
    detail = client.get(
        f"/api/vendor/requests/{request_id}", headers=auth(vendor_token(client))
    ).json()

    by_id = {f["id"]: f for f in detail["fields"]}
    assert by_id["phone"]["value"] == "0912***678"
    assert by_id["phone"]["masked"] is True
    assert by_id["address"]["masked"] is True
    assert by_id["preferred_date"]["masked"] is False
    assert detail["has_contact"] is True
    assert detail["contact_access_log"] == []


def test_reveal_returns_plaintext_with_field_labels(client):
    request_id = submit_request(client)
    res = reveal(client, vendor_token(client), request_id)

    assert res.status_code == 200, res.text
    contact = {c["id"]: c for c in res.json()["contact"]}
    assert contact["phone"]["value"] == PHONE
    assert contact["phone"]["label"] == "聯絡電話"
    assert contact["address"]["value"] == ADDRESS


def test_reveal_writes_an_access_record(client):
    request_id = submit_request(client)
    token = vendor_token(client)

    res = reveal(client, token, request_id)
    log = res.json()["contact_access_log"]
    assert len(log) == 1
    assert log[0]["viewer_name"] == "潔家家事服務"
    assert set(log[0]["fields"]) == {"服務地址", "聯絡電話"}
    assert log[0]["at"]

    stored = STORE.list_contact_access(request_id)
    assert stored[0]["vendor_id"] == 1
    assert stored[0]["owner_id"] == RESIDENT_SUB
    assert stored[0]["entity_type"] == "CONTACT_ACCESS_LOG"


def test_access_records_accumulate_and_show_up_on_the_detail_page(client):
    request_id = submit_request(client)
    token = vendor_token(client)

    reveal(client, token, request_id)
    reveal(client, token, request_id)

    detail = client.get(f"/api/vendor/requests/{request_id}", headers=auth(token)).json()
    assert len(detail["contact_access_log"]) == 2


def test_vendor_only_sees_its_own_access_records(client):
    """同一張單被別家廠商看過的紀錄不外流——那是另一家的營運資訊。"""
    request_id = submit_request(client)
    reveal(client, vendor_token(client), request_id)
    STORE.log_contact_access(
        request_id,
        {"vendor_id": 11, "vendor_name": "安心水電工程行", "owner_id": RESIDENT_SUB, "fields": ["phone"]},
    )

    detail = client.get(
        f"/api/vendor/requests/{request_id}", headers=auth(vendor_token(client))
    ).json()
    assert [e["viewer_name"] for e in detail["contact_access_log"]] == ["潔家家事服務"]
    assert len(STORE.list_contact_access(request_id)) == 2


def test_another_vendor_cannot_reveal_contact(client):
    request_id = submit_request(client)
    res = reveal(client, vendor_token(client, VENDOR_PLUMBING), request_id)
    assert res.status_code == 404
    assert STORE.list_contact_access(request_id) == []


def test_resident_token_cannot_reveal_contact(client):
    request_id = submit_request(client)
    res = client.post(
        f"/api/vendor/requests/{request_id}/contact", headers=auth(RESIDENT_TOKEN)
    )
    assert res.status_code == 403
    assert STORE.list_contact_access(request_id) == []


def test_reveal_without_a_token_is_rejected(client):
    request_id = submit_request(client)
    res = client.post(f"/api/vendor/requests/{request_id}/contact")
    assert res.status_code == 401
    assert STORE.list_contact_access(request_id) == []


def test_reveal_on_an_order_without_contact_fields_is_404(client):
    request_id = "REQ-NO-CONTACT-TEST"
    STORE.save_request(
        RESIDENT_SUB,
        {
            "request_id": request_id,
            "service_id": "air_conditioner_cleaning",
            "service_name": "冷氣清洗",
            "service_vendor_id": 1,
            "status": "SUBMITTED",
            "form_data": {"quantity": 1},
            "created_at": now_iso(),
        },
    )
    res = reveal(client, vendor_token(client), request_id)
    assert res.status_code == 404
    assert res.json()["detail"]["error"]["code"] == "CONTACT_NOT_FOUND"


def test_log_failure_blocks_the_reveal(client, monkeypatch):
    """存取軌跡寫不進去就不給資料，否則會出現查不到的存取。"""
    request_id = submit_request(client)

    def boom(*_args, **_kwargs):
        raise RuntimeError("dynamodb unavailable")

    monkeypatch.setattr(STORE, "log_contact_access", boom)
    res = reveal(client, vendor_token(client), request_id)
    assert res.status_code == 503
    assert res.json()["detail"]["error"]["code"] == "CONTACT_LOG_UNAVAILABLE"


# ---- Milestone 15 之前存進去的明文案件 ----


def test_legacy_plaintext_request_is_masked_and_revealable(client):
    """回填腳本跑之前，資料庫裡還是明文；廠商後台一樣不能直接看到完整內容。"""
    request_id = "REQ-LEGACY-PLAINTEXT"
    STORE.put_item(
        {
            "PK": f"USER#{RESIDENT_SUB}",
            "SK": f"REQUEST#{request_id}",
            "entity_type": "SERVICE_REQUEST",
            "request_id": request_id,
            "service_id": "air_conditioner_cleaning",
            "service_name": "冷氣清洗",
            "service_vendor_id": 1,
            "status": "SUBMITTED",
            "form_data": dict(AC_CLEANING_FORM),  # 明文，也沒有 form_data_masked
            "version": 1,
            "created_at": now_iso(),
            "updated_at": now_iso(),
        }
    )
    STORE.put_item(
        {
            "PK": "VENDOR#1",
            "SK": f"REQUEST#{request_id}",
            "entity_type": "VENDOR_REQUEST_INDEX",
            "vendor_id": 1,
            "owner_id": RESIDENT_SUB,
            "request_id": request_id,
            "service_id": "air_conditioner_cleaning",
            "service_name": "冷氣清洗",
            "status": "SUBMITTED",
            "version": 1,
            "form_data": dict(AC_CLEANING_FORM),
            "created_at": now_iso(),
            "updated_at": now_iso(),
        }
    )
    token = vendor_token(client)

    detail = client.get(f"/api/vendor/requests/{request_id}", headers=auth(token)).json()
    assert {f["id"]: f["value"] for f in detail["fields"]}["phone"] == "0912***678"

    revealed = reveal(client, token, request_id)
    assert {c["id"]: c["value"] for c in revealed.json()["contact"]}["phone"] == PHONE
