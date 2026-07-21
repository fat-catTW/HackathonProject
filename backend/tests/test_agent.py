"""§20.1/20.3：Agent 流程、缺欄位計算、Tool 錯誤、多使用者隔離。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agent import tools  # noqa: E402
from app.agent.agent import handle_message, new_state  # noqa: E402
from app.services.store import STORE  # noqa: E402


def chat(actor, sid, state, msg):
    r = handle_message(actor, sid, state, msg)
    return r["reply"], r["state"]


def test_missing_field_flow_and_no_repeat():
    state = new_state()
    reply, state = chat("t-user1", "s1", state, "我要洗冷氣")
    assert "幾台" in reply
    reply, state = chat("t-user1", "s1", state, "兩台")
    assert "幾台" not in reply  # 不重複詢問
    assert state["collected_fields"]["quantity"] == 2


def test_confirmation_required_before_submit():
    state = new_state()
    _, state = chat("t-user2", "s2", state,
                    "明天下午洗一台冷氣 台北市中山區民生東路1號 0911222333")
    assert state["awaiting_confirmation"] is True
    assert state["request_id"] is None  # 未確認前不得建立案件
    reply, state = chat("t-user2", "s2", state, "確認")
    assert state["request_id"] is not None


def test_tool_error_no_fake_request_id(monkeypatch):
    state = new_state()
    _, state = chat("t-user3", "s3", state,
                    "明天下午洗一台冷氣 台北市中山區民生東路1號 0911222333")
    orig = tools.call

    def failing(name, params):
        if name == "submit_service_request":
            return {"success": False,
                    "error": {"code": "TOOL_INVOCATION_FAILED", "message": "模擬失敗"}}
        return orig(name, params)

    monkeypatch.setattr("app.agent.agent.tools.call", failing)
    reply, state = chat("t-user3", "s3", state, "確認")
    assert state["request_id"] is None
    assert "無法送出" in reply


def test_multi_user_isolation():
    sa = new_state()
    _, sa = chat("t-userA", "sA", sa,
                 "明天下午洗一台冷氣 台北市中山區民生東路1號 0911222333")
    _, sa = chat("t-userA", "sA", sa, "確認")
    assert STORE.list_requests("t-userB") == []  # B 看不到 A 的案件
    assert STORE.get_preferences("t-userB") == {}


def test_submit_validation_missing_fields():
    r = tools.call("submit_service_request", {
        "service_id": "air_conditioner_cleaning",
        "session_id": "x", "actor_id": "t-user4",
        "payload": {"quantity": 1}})
    assert r["success"] is False
    assert "address" in r["error"]["missing_fields"]
