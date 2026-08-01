"""相對日期（「這禮拜三」「明天」）必須以使用者當下的日期換算。

之前有兩個問題會填出對不上的日期：
1. 只要模型回了一個格式正確又不是過去的 YYYY-MM-DD，就直接採信——但「某個日期是星期幾」
   是模型很容易算錯的推理。
2. 「今天」用的是伺服器所在時區（部署在 UTC），台灣時間 16:00 之後會整整差一天。
"""
from datetime import date
from unittest.mock import patch

import pytest

from backend.app.agent import agent, nlu
from backend.app.services import clock

MONDAY = date(2026, 8, 3)
SATURDAY = date(2026, 8, 1)
DATE_FIELD = {"id": "preferred_date", "type": "date", "required": True}


@pytest.mark.parametrize(
    ("today", "text", "expected"),
    [
        # 使用者在星期一說「這禮拜三」→ 就是這一週的星期三
        (MONDAY, "這禮拜三下午兩點半", "2026-08-05"),
        (MONDAY, "禮拜三", "2026-08-05"),
        (MONDAY, "這禮拜一", "2026-08-03"),
        # 沒說「這」而且今天就是那一天 → 指下一個
        (MONDAY, "禮拜一", "2026-08-10"),
        # 「下禮拜三」是下一個日曆週的星期三
        (MONDAY, "下禮拜三", "2026-08-12"),
        (MONDAY, "下下禮拜三", "2026-08-19"),
        (SATURDAY, "下禮拜三", "2026-08-05"),
        # 這一週的那天已經過了 → 取最近的下一次，不給過去的日期
        (SATURDAY, "這禮拜三", "2026-08-05"),
        (MONDAY, "明天", "2026-08-04"),
        (MONDAY, "後天", "2026-08-05"),
    ],
)
def test_weekday_is_resolved_against_the_users_today(today, text, expected):
    assert nlu.parse_date(text, today=today) == expected


def test_relative_date_beats_a_wrong_model_answer():
    """模型把「這禮拜三」算成別的日期時，以規則換算為準。"""
    with patch.object(clock, "today", return_value=MONDAY):
        normalized = agent._normalize_field_value(
            DATE_FIELD,
            "2026-08-19",  # 模型猜錯的日期
            "幫我填，這禮拜三下午兩點半",
        )

    assert normalized == "2026-08-05"


def test_absolute_date_from_the_model_is_still_trusted():
    """使用者講的是明確日期時，維持原本行為。"""
    with patch.object(clock, "today", return_value=MONDAY):
        normalized = agent._normalize_field_value(DATE_FIELD, "2026-08-20", "8月20號可以嗎")

    assert normalized == "2026-08-20"


def test_client_date_wins_over_the_server_clock():
    """使用者裝置說今天是星期一時，「這禮拜三」就要從那一天算起。"""
    token = clock.use_client_date("2026-08-03")
    try:
        assert clock.today() == MONDAY
        assert nlu.parse_date("這禮拜三") == "2026-08-05"
    finally:
        clock.reset_client_date(token)

    # 請求結束後不能殘留，否則會污染下一位使用者
    assert clock.today() == clock.now().date()


def test_a_broken_client_date_falls_back_to_taiwan_time():
    token = clock.use_client_date("not-a-date")
    try:
        assert clock.today() == clock.now().date()
    finally:
        clock.reset_client_date(token)


def test_chat_api_resolves_weekdays_against_the_client_date():
    from fastapi.testclient import TestClient

    from backend.app.main import app

    client = TestClient(app)
    accounts = client.get("/api/auth/demo-accounts").json()["accounts"]
    headers = {"Authorization": f"Bearer {accounts[0]['token']}"}
    session_id = client.post("/api/sessions", headers=headers).json()["session_id"]

    with patch.object(
        agent,
        "_extract_fields",
        side_effect=lambda actor_id, state, text, events: {
            "preferred_date": nlu.parse_date(text) or "",
        },
    ):
        response = client.post(
            "/api/chat",
            headers=headers,
            json={
                "session_id": session_id,
                "message": "幫我填，這禮拜三下午兩點半",
                "current_page_id": "service_form_air_conditioner_cleaning",
                "form_context": {"service_id": "air_conditioner_cleaning", "values": {}},
                "client_date": "2026-08-03",
            },
        )

    assert response.status_code == 200
    dates = [
        action["value"]
        for action in response.json()["form_actions"]
        if action["field_id"] == "preferred_date"
    ]
    assert dates == ["2026-08-05"]


def test_today_follows_taiwan_time_not_the_server_timezone():
    """伺服器跑在 UTC 時，台灣時間傍晚之後不能還停在前一天。"""
    assert clock.TZ.utcoffset(None).total_seconds() == 8 * 3600
    assert clock.today() == clock.now().date()
    assert clock.weekday_zh(MONDAY) == "星期一"
    assert clock.weekday_zh(SATURDAY) == "星期六"
