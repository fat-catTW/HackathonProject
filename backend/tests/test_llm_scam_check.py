from unittest.mock import patch

from backend.app.agent import llm


def test_check_scam_message_returns_validated_category():
    fake_payload = {"category": "投資詐騙", "explanation": "這類訊息常以保證獲利吸引匯款，請勿點擊連結或提供帳戶資料。"}
    with patch("backend.app.agent.llm._converse_json", return_value=fake_payload):
        result = llm.check_scam_message("老師說穩賺不賠，加LINE了解")

    assert result == fake_payload


def test_check_scam_message_returns_none_when_category_invalid():
    with patch("backend.app.agent.llm._converse_json", return_value={"category": "不明分類", "explanation": "x"}):
        assert llm.check_scam_message("隨便的訊息") is None


def test_check_scam_message_returns_none_when_client_unavailable():
    with patch("backend.app.agent.llm._converse_json", return_value=None):
        assert llm.check_scam_message("隨便的訊息") is None
