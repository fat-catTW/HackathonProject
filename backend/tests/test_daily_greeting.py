"""每日問候卡：卡片內容必須是真的從使用者案件算出來的，不是罐頭問候。"""
import tempfile
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services import daily_greeting
from backend.app.services import store as store_module

ACTOR = "user-demo"


@pytest.fixture(autouse=True)
def isolated_store(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        test_store = store_module.MemoryStore(storage_path=Path(tmp) / "store.json")
        monkeypatch.setattr(store_module, "STORE", test_store)
        monkeypatch.setattr(daily_greeting, "STORE", test_store)
        yield test_store


def _morning(day: str = "2026-08-01") -> datetime:
    return datetime.fromisoformat(f"{day}T07:00:00+08:00")


def _save(store, updated_at: str | None = None, **overrides) -> dict:
    request = {
        "request_id": overrides.pop("request_id", "REQ-1"),
        "service_id": "air_conditioner_cleaning",
        "service_name": "冷氣清洗",
        "status": "SUBMITTED",
        "form_data": {},
        "created_at": "2026-07-30T10:00:00+08:00",
    } | overrides
    store.save_request(ACTOR, request)
    if updated_at:
        # save_request 一律把 updated_at 蓋成「現在」（所有狀態變更都走這條），
        # 要模擬「幾天前就完工的案件」只能事後改寫，否則測試結果會跟跑測試的
        # 當天日期綁在一起。
        stored = store.get_stored_request(ACTOR, request["request_id"])
        store.put_item(stored | {"updated_at": updated_at})
    return request


def test_greeting_uses_time_of_day_and_name():
    card = daily_greeting.build_daily_greeting(ACTOR, "王小明", now=_morning())

    assert card["period"] == "morning"
    assert card["greeting"] == "早安，王小明"
    assert card["push_time"] == "07:00"
    assert card["date"] == "2026-08-01"
    assert card["weekday"] == "星期六"


def test_afternoon_and_evening_switch_the_greeting():
    afternoon = daily_greeting.build_daily_greeting(
        ACTOR, "王小明", now=datetime.fromisoformat("2026-08-01T14:00:00+08:00")
    )
    evening = daily_greeting.build_daily_greeting(
        ACTOR, "王小明", now=datetime.fromisoformat("2026-08-01T20:00:00+08:00")
    )

    assert (afternoon["period"], afternoon["greeting"]) == ("afternoon", "午安，王小明")
    assert (evening["period"], evening["greeting"]) == ("evening", "晚安，王小明")


def test_no_requests_yields_an_empty_but_actionable_card(isolated_store):
    card = daily_greeting.build_daily_greeting(ACTOR, "王小明", now=_morning())

    assert card["items"] == []
    assert card["headline"] == "今天沒有待辦，輕鬆一點"
    # 沒有待辦時卡片不能是死的：至少要給幾個可以直接丟給管家的開場白。
    assert len(card["suggestions"]) == daily_greeting.MAX_SUGGESTIONS
    assert all(s["prompt"] for s in card["suggestions"])


def test_reservation_scheduled_today_is_the_top_item(isolated_store):
    _save(
        isolated_store,
        request_id="REQ-RESV",
        service_id="restaurant_reservation",
        service_name="餐廳訂位",
        status="CONFIRMED",
        service_time="2026-08-01T18:00:00+08:00",
        order_items={"restaurant_name": "22世紀風味館"},
    )

    card = daily_greeting.build_daily_greeting(ACTOR, "王小明", now=_morning())

    assert card["headline"] == "今天有 1 件事要提醒你"
    item = card["items"][0]
    assert item["kind"] == "today"
    assert item["title"] == "今天 18:00 餐廳訂位"
    assert item["detail"] == "22世紀風味館 · 已確認"
    assert item["action_path"] == "/requests/REQ-RESV"


def test_upcoming_days_are_labelled_relative_to_today(isolated_store):
    _save(
        isolated_store,
        request_id="REQ-TOMORROW",
        service_name="居家清潔",
        service_id="home_cleaning",
        status="CONFIRMED",
        form_data={"preferred_date": "2026-08-02", "preferred_time_slot": "09:30"},
    )

    card = daily_greeting.build_daily_greeting(ACTOR, "王小明", now=_morning())

    assert card["items"][0]["kind"] == "upcoming"
    assert card["items"][0]["title"] == "明天 09:30 居家清潔"


def test_same_day_items_put_the_ones_with_a_time_first(isolated_store):
    _save(
        isolated_store,
        request_id="REQ-NO-TIME",
        status="CONFIRMED",
        form_data={"preferred_date": "2026-08-01"},
    )
    _save(
        isolated_store,
        request_id="REQ-AT-NINE",
        service_id="home_cleaning",
        service_name="居家清潔",
        status="CONFIRMED",
        form_data={"preferred_date": "2026-08-01", "preferred_time_slot": "09:00"},
    )

    card = daily_greeting.build_daily_greeting(ACTOR, "王小明", now=_morning())

    # 「今天 09:00 的清潔」比「今天的冷氣清洗」明確，先讓使用者看到。
    assert [item["id"] for item in card["items"]] == ["REQ-AT-NINE", "REQ-NO-TIME"]


def test_far_future_bookings_are_not_mentioned_today(isolated_store):
    _save(
        isolated_store,
        request_id="REQ-FAR",
        status="CONFIRMED",
        form_data={"preferred_date": "2026-09-20"},
    )

    card = daily_greeting.build_daily_greeting(ACTOR, "王小明", now=_morning())

    # 一個半月後的預約今天提醒沒有意義，但案件仍在跑，所以退回「進行中」那一則。
    assert card["items"][0]["kind"] == "in_progress"
    assert card["items"][0]["detail"] == "已確認"


def test_time_slot_codes_are_not_printed_as_a_clock_time(isolated_store):
    _save(
        isolated_store,
        request_id="REQ-SLOT",
        service_id="restaurant_reservation",
        service_name="餐廳訂位",
        status="CONFIRMED",
        form_data={"reserved_date": "2026-08-01", "time_slot": "DINNER"},
    )

    card = daily_greeting.build_daily_greeting(ACTOR, "王小明", now=_morning())

    assert card["items"][0]["title"] == "今天的餐廳訂位"


def test_draft_outranks_an_in_progress_case(isolated_store):
    _save(isolated_store, request_id="REQ-RUNNING", status="IN_PROGRESS")
    _save(
        isolated_store,
        request_id="REQ-DRAFT",
        service_id="home_cleaning",
        service_name="居家清潔",
        status="DRAFT",
    )

    card = daily_greeting.build_daily_greeting(ACTOR, "王小明", now=_morning())

    kinds = [item["kind"] for item in card["items"]]
    assert kinds == ["action_needed", "in_progress"]
    assert card["items"][0]["title"] == "還沒送出的居家清潔"
    assert card["message"] == daily_greeting._KIND_MESSAGES["action_needed"]


def test_cancelled_cases_never_show_up(isolated_store):
    _save(isolated_store, request_id="REQ-GONE", status="CANCELLED")

    card = daily_greeting.build_daily_greeting(ACTOR, "王小明", now=_morning())

    assert card["items"] == []


def test_recently_completed_case_asks_for_feedback_then_stops(isolated_store):
    _save(
        isolated_store,
        request_id="REQ-DONE",
        status="COMPLETED",
        updated_at="2026-08-01T09:00:00+08:00",
    )

    fresh = daily_greeting.build_daily_greeting(ACTOR, "王小明", now=_morning())
    assert fresh["items"][0]["kind"] == "followup"

    # 一週後同一筆已完成的案件不該再天天出現。
    stale = daily_greeting.build_daily_greeting(ACTOR, "王小明", now=_morning("2026-08-09"))
    assert stale["items"] == []


def test_card_is_capped_so_it_stays_readable(isolated_store):
    for index in range(6):
        _save(isolated_store, request_id=f"REQ-{index}", status="SUBMITTED")

    card = daily_greeting.build_daily_greeting(ACTOR, "王小明", now=_morning())

    assert len(card["items"]) == daily_greeting.MAX_ITEMS


def test_suggestions_lead_with_a_service_the_user_has_used(isolated_store):
    _save(
        isolated_store,
        request_id="REQ-OLD",
        service_id="washing_machine_cleaning",
        service_name="洗衣機清洗",
        status="COMPLETED",
        updated_at="2026-06-01T09:00:00+08:00",
    )

    card = daily_greeting.build_daily_greeting(ACTOR, "王小明", now=_morning())

    assert card["suggestions"][0]["label"] == "再約一次洗衣機清洗"
    assert card["suggestions"][0]["prompt"] == "我想再預約一次洗衣機清洗"


def test_repeat_copy_uses_the_verb_that_fits_each_service(isolated_store):
    """「再約一次商城購物」中文不通——每個服務的動詞要各自挑過，不能共用樣板。"""
    _save(
        isolated_store,
        request_id="REQ-SHOP",
        service_id="shop_purchase",
        service_name="商城購物",
        status="COMPLETED",
        updated_at="2026-06-01T09:00:00+08:00",
    )

    card = daily_greeting.build_daily_greeting(ACTOR, "王小明", now=_morning())

    assert card["suggestions"][0] == {
        "service_id": "shop_purchase",
        "label": "再逛一次商城",
        "prompt": "我想再去商城買東西",
    }


def test_every_pooled_service_has_both_a_first_time_and_a_repeat_line():
    for entry in daily_greeting._SUGGESTION_POOL:
        for key in ("label", "prompt", "repeat_label", "repeat_prompt"):
            assert entry[key], f"{entry['service_id']} 缺少 {key}"


def test_suggestions_skip_services_already_reminded_about(isolated_store):
    _save(isolated_store, request_id="REQ-AC", status="IN_PROGRESS")

    card = daily_greeting.build_daily_greeting(ACTOR, "王小明", now=_morning())

    assert card["items"][0]["service_id"] == "air_conditioner_cleaning"
    assert "air_conditioner_cleaning" not in {s["service_id"] for s in card["suggestions"]}


def test_suggestions_rotate_between_days(isolated_store):
    monday = daily_greeting.build_daily_greeting(ACTOR, "王小明", now=_morning("2026-08-03"))
    tuesday = daily_greeting.build_daily_greeting(ACTOR, "王小明", now=_morning("2026-08-04"))

    assert [s["service_id"] for s in monday["suggestions"]] != [
        s["service_id"] for s in tuesday["suggestions"]
    ]


def _auth_headers(client: TestClient) -> dict:
    accounts = client.get("/api/auth/demo-accounts").json()["accounts"]
    return {"Authorization": f"Bearer {accounts[0]['token']}"}


def test_api_returns_a_card_for_the_logged_in_user():
    client = TestClient(app)

    response = client.get("/api/daily-greeting", headers=_auth_headers(client))

    assert response.status_code == 200
    card = response.json()
    assert card["push_time"] == "07:00"
    assert card["greeting"].startswith(("早安", "午安", "晚安", "夜深了"))
    assert isinstance(card["items"], list)
    assert card["suggestions"]


def test_api_requires_authentication():
    client = TestClient(app)

    assert client.get("/api/daily-greeting").status_code == 401


def test_api_uses_the_client_local_date():
    client = TestClient(app)

    card = client.get(
        "/api/daily-greeting",
        params={"client_date": "2026-12-25"},
        headers=_auth_headers(client),
    ).json()

    assert card["date"] == "2026-12-25"
    assert card["date_label"] == "12 月 25 日 星期五"
