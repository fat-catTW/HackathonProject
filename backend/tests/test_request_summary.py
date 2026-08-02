"""AI 需求摘要：內容組成、隱私邊界，以及建單當下就寫進案件這件事。

測試環境的 conftest 會清掉 AWS 憑證，llm 一律不可用，因此不特別 mock 的案例走的都是
機械版兜底摘要——這正是 demo 機器沒有 Bedrock 權限時使用者會看到的東西。
"""
import pytest
from fastapi.testclient import TestClient

from backend.app.agent import llm
from backend.app.main import app
from backend.app.services import request_summary
from backend.app.services.store import STORE, now_iso

RESIDENT_TOKEN = "demo-token-vincent"
VENDOR_CLEANING = ("vendor1@demo.local", "vendor1234")

PLUMBING_FORM = {
    "repair_item": "水管",
    "issue_description": "廚房水槽下方的水管接頭一直滴水，地板都濕了",
    "preferred_date": "2026-08-05",
    "preferred_time_slot": "MORNING",
    "address": "台北市信義區市府路1號",
    "phone": "0912345678",
    "notes": "電鈴壞了，麻煩打電話",
}

AC_CLEANING_FORM = {
    "quantity": 2,
    "air_conditioner_type": "壁掛式",
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


# ---- 摘要內容本身 ----


def test_summary_never_contains_contact_information():
    """摘要以明文存在案件上、廠商一開頁就看得到，不能挾帶姓名／電話／地址。"""
    fields = request_summary._fields_for_summary("plumbing_repair", PLUMBING_FORM)
    labels = [field["label"] for field in fields]

    assert "服務地址" not in labels
    assert "聯絡電話" not in labels
    summary = request_summary.build("plumbing_repair", PLUMBING_FORM)
    assert "0912345678" not in summary
    assert "市府路1號" not in summary


def test_summary_prompt_fields_follow_schema_order_and_use_labels():
    """欄位順序取自 schema，選項代碼換成中文，模型才不會讀到 MORNING 這種東西。"""
    fields = request_summary._fields_for_summary("plumbing_repair", PLUMBING_FORM)

    assert [f["label"] for f in fields] == ["叫修工項", "問題描述", "服務日期", "服務時間", "備註"]
    assert {"label": "服務時間", "value": "上午"} in fields


def test_summary_falls_back_to_a_mechanical_line_without_bedrock():
    """沒有 Bedrock 也要有東西可看，而且不能超過單行預算、不能切在字中間。"""
    summary = request_summary.build("plumbing_repair", PLUMBING_FORM)

    assert summary.startswith("水電修繕")
    assert len(summary) <= request_summary.MAX_CHARS
    assert not summary.endswith("…")
    assert "廚房水槽" in summary, "塞得下的問題描述就該完整寫進去"


def test_fallback_skips_an_oversized_field_instead_of_stopping_there():
    """問題描述常常又長又排在前面；一碰到塞不下的欄位就收工，日期時段會全部落空。"""
    verbose = dict(PLUMBING_FORM, issue_description="廚房水槽下方的水管接頭這兩天一直在滴水，下面的櫃子跟地板都濕掉了，怕會發霉")

    summary = request_summary.build("plumbing_repair", verbose)

    assert len(summary) <= request_summary.MAX_CHARS
    assert "廚房水槽" not in summary
    assert "2026-08-05" in summary
    assert "上午" in summary


def test_summary_clips_an_overlong_model_answer(monkeypatch):
    monkeypatch.setattr(llm, "summarize_service_request", lambda *_: "廚" * 80)

    summary = request_summary.build("plumbing_repair", PLUMBING_FORM)

    assert len(summary) == request_summary.MAX_CHARS
    assert summary.endswith("…")


def test_summary_keeps_the_model_answer_on_one_line(monkeypatch):
    monkeypatch.setattr(llm, "summarize_service_request", lambda *_: " 廚房水管漏水\n8/5 上午 ")

    assert request_summary.build("plumbing_repair", PLUMBING_FORM) == "廚房水管漏水 8/5 上午"


def test_summary_survives_a_model_blowup(monkeypatch):
    """摘要是錦上添花；模型端爆炸也不能讓住戶送不出單。"""
    def boom(*_):
        raise RuntimeError("bedrock is having a day")

    monkeypatch.setattr(llm, "summarize_service_request", boom)

    assert request_summary.build("plumbing_repair", PLUMBING_FORM) == "水電修繕"


def test_no_summary_for_services_no_vendor_ever_sees():
    """健康商品推薦沒有廠商後台，不必為它花一次 Bedrock。"""
    assert request_summary.build("health_product_recommendation", {"query": "血壓"}) == ""


# ---- 建單當下就寫進 DB，廠商明細頁直接讀 ----


def test_form_submission_stores_the_summary_and_vendor_detail_serves_it(client):
    res = client.post(
        "/api/services/air_conditioner_cleaning/requests",
        json={"payload": AC_CLEANING_FORM},
        headers=auth(RESIDENT_TOKEN),
    )
    assert res.status_code == 200, res.text
    request_id = res.json()["request_id"]

    stored = STORE.get_stored_request("user-vincent", request_id)
    assert stored and stored["ai_summary"], "摘要應該在建單當下就寫進案件，而不是開頁才算"

    detail = client.get(
        f"/api/vendor/requests/{request_id}",
        headers=auth(vendor_token(client, VENDOR_CLEANING)),
    )
    assert detail.status_code == 200, detail.text
    assert detail.json()["ai_summary"] == stored["ai_summary"]


def test_vendor_detail_returns_empty_summary_for_older_requests(client):
    """Milestone 前建立的案件沒有這個欄位，明細頁要能照常打開。"""
    request_id = client.post(
        "/api/services/air_conditioner_cleaning/requests",
        json={"payload": AC_CLEANING_FORM},
        headers=auth(RESIDENT_TOKEN),
    ).json()["request_id"]
    stored = STORE.get_stored_request("user-vincent", request_id)
    stored.pop("ai_summary")
    STORE.put_item(stored)

    detail = client.get(
        f"/api/vendor/requests/{request_id}",
        headers=auth(vendor_token(client, VENDOR_CLEANING)),
    )
    assert detail.status_code == 200, detail.text
    assert detail.json()["ai_summary"] == ""


def test_attaching_the_summary_does_not_bump_the_optimistic_lock_version():
    """管家送單走補寫路徑；補一句摘要不該讓廠商手上已開著的頁面版本失效。"""
    request_id = STORE.next_request_id()
    STORE.save_request(
        "user-vincent",
        {
            "request_id": request_id,
            "service_id": "plumbing_repair",
            "service_name": "水電修繕",
            "service_vendor_id": 11,
            "status": "SUBMITTED",
            "form_data": dict(PLUMBING_FORM),
            # save_request 不會補這個欄位，漏掉的話案件會一路留在共用的 mock store
            # 裡，之後每次打住戶端案件清單都被它絆倒。
            "created_at": now_iso(),
        },
    )
    before = STORE.get_stored_request("user-vincent", request_id)

    summary = request_summary.attach("user-vincent", request_id, "plumbing_repair", PLUMBING_FORM)

    after = STORE.get_stored_request("user-vincent", request_id)
    assert after["ai_summary"] == summary
    assert after["version"] == before["version"]
    assert after["updated_at"] == before["updated_at"]
    # 補寫時原樣寫回，聯絡欄位不能因此變回明文。
    assert after["form_data"]["phone"] == before["form_data"]["phone"]
    assert after["form_data"]["phone"] != PLUMBING_FORM["phone"]
