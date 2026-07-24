"""Core agent regression tests."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agent import tools  # noqa: E402
from app.agent.agent import handle_message, new_state  # noqa: E402
from app.services.store import STORE  # noqa: E402


def chat(actor: str, sid: str, state: dict, msg: str):
    result = handle_message(actor, sid, state, msg)
    return result["reply"], result["state"]


def test_missing_field_flow_and_no_repeat():
    state = new_state()
    reply, state = chat("t-user1", "s1", state, "我要預約洗兩台冷氣")
    assert "日期" in reply or "時段" in reply or "地址" in reply

    reply, state = chat("t-user1", "s1", state, "兩台")
    assert state["collected_fields"]["quantity"] == 2
    assert "兩台" not in reply


def test_confirmation_required_before_submit():
    state = new_state()
    _, state = chat(
        "t-user2",
        "s2",
        state,
        "我要預約明天下午洗一台冷氣，地址是台北市信義區測試路1號，電話0911222333",
    )
    assert state["awaiting_confirmation"] is True
    assert state["request_id"] is None

    _, state = chat("t-user2", "s2", state, "確認")
    assert state["request_id"] is not None


def test_tool_error_no_fake_request_id(monkeypatch):
    state = new_state()
    _, state = chat(
        "t-user3",
        "s3",
        state,
        "我要預約明天下午洗一台冷氣，地址是台北市信義區測試路1號，電話0911222333",
    )
    original = tools.call

    def failing(name, params, auth_token=None):
        if name == "submit_service_request":
            return {
                "success": False,
                "error": {"code": "TOOL_INVOCATION_FAILED", "message": "資料庫異常"},
            }
        return original(name, params, auth_token=auth_token)

    monkeypatch.setattr("app.agent.agent.tools.call", failing)
    reply, state = chat("t-user3", "s3", state, "確認")
    assert state["request_id"] is None
    assert "失敗" in reply or "稍後" in reply


def test_multi_user_isolation():
    state_a = new_state()
    _, state_a = chat(
        "t-userA",
        "sA",
        state_a,
        "我要預約明天下午洗一台冷氣，地址是台北市信義區測試路1號，電話0911222333",
    )
    _, state_a = chat("t-userA", "sA", state_a, "確認")

    assert STORE.list_requests("t-userB") == []
    assert STORE.get_preferences("t-userB") == {}


def test_submit_validation_missing_fields():
    result = tools.call(
        "submit_service_request",
        {
            "service_id": "air_conditioner_cleaning",
            "session_id": "x",
            "actor_id": "t-user4",
            "payload": {"quantity": 1},
        },
    )
    assert result["success"] is False
    assert "address" in result["error"]["missing_fields"]


def test_can_explain_current_page_function():
    state = new_state()
    result = handle_message(
        "t-user5",
        "s5",
        state,
        "這個頁面的功能是什麼？",
        current_page_id="home",
    )
    assert "服務首頁" in result["reply"]
    assert "目前所有服務" in result["reply"] or "AI 管家" in result["reply"]
    assert result["state"]["service_id"] is None


def test_can_explain_other_page_function():
    state = new_state()
    result = handle_message(
        "t-user6",
        "s6",
        state,
        "我的服務頁面是做什麼的？",
        current_page_id="home",
    )
    assert "我的服務" in result["reply"]
    assert "案件" in result["reply"]
    assert result["state"]["service_id"] is None


def test_can_guide_user_to_my_services_page():
    state = new_state()
    result = handle_message(
        "t-user7",
        "s7",
        state,
        "我要去哪裡看我的案件？",
        current_page_id="home",
    )
    assert "我的服務" in result["reply"]
    assert "案件" in result["reply"]
    assert result["state"]["service_id"] is None


def test_can_guide_user_to_assistant_page():
    state = new_state()
    result = handle_message(
        "t-user8",
        "s8",
        state,
        "如果我要新增服務需求，要去哪裡？",
        current_page_id="home",
    )
    assert "AI 管家" in result["reply"]
    assert "啟動 AI 管家" in result["reply"] or "服務首頁" in result["reply"]
    assert result["state"]["service_id"] is None
