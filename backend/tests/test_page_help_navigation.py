"""Regression tests for page explanation and app navigation guidance."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agent.agent import handle_message, new_state  # noqa: E402


def test_current_page_understands_colloquial_function_question():
    state = new_state()
    result = handle_message(
        "t-user9",
        "s9",
        state,
        "這頁可以做什麼",
        current_page_id="home",
    )
    assert "服務首頁" in result["reply"]
    assert result["state"]["service_id"] is None


def test_navigation_understands_my_cases_lookup():
    state = new_state()
    result = handle_message(
        "t-user10",
        "s10",
        state,
        "我要去哪裡看我的案件",
        current_page_id="home",
    )
    assert "我的服務" in result["reply"]
    assert result["state"]["service_id"] is None


def test_navigation_understands_return_home():
    state = new_state()
    result = handle_message(
        "t-user11",
        "s11",
        state,
        "怎麼回首頁",
        current_page_id="my_services",
    )
    assert "服務首頁" in result["reply"]
    assert result["state"]["service_id"] is None


def test_current_page_understands_here_can_do_what():
    state = new_state()
    result = handle_message(
        "t-user12",
        "s12",
        state,
        "這裡能做什麼",
        current_page_id="service_form",
    )
    assert "服務表單頁" in result["reply"]
    assert result["state"]["service_id"] is None


def test_assistant_can_explain_its_role():
    state = new_state()
    result = handle_message(
        "t-user13",
        "s13",
        state,
        "你知道你的任務是什麼嗎",
        current_page_id="home",
    )
    assert "AI 管家" in result["reply"] or "我是這個 app 的 AI 管家" in result["reply"]
    assert "介紹頁面" in result["reply"]
    assert result["state"]["service_id"] is None


def test_current_page_understands_colloquial_whats_this_page_for():
    state = new_state()
    result = handle_message(
        "t-user14",
        "s14",
        state,
        "這頁面在幹嘛",
        current_page_id="home",
    )
    assert "服務首頁" in result["reply"]
    assert "這一頁你可以" in result["reply"]
    assert result["state"]["service_id"] is None


def test_assistant_understands_other_capabilities_question():
    state = new_state()
    result = handle_message(
        "t-user15",
        "s15",
        state,
        "還有什麼其他功能",
        current_page_id="home",
    )
    assert "介紹頁面" in result["reply"]
    assert "帶你找功能" in result["reply"]
    assert result["state"]["service_id"] is None
