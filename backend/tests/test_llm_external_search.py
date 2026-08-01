from unittest.mock import patch

from backend.app.agent import llm


def test_plan_external_query_returns_query_string():
    with patch("backend.app.agent.llm._converse_json", return_value={"query": "台中 餐廳"}):
        assert llm.plan_external_query("我想在台中吃飯", purpose="restaurant") == "台中 餐廳"


def test_plan_external_query_returns_none_when_bedrock_unavailable():
    with patch("backend.app.agent.llm._converse_json", return_value=None):
        assert llm.plan_external_query("foo", purpose="x") is None


def test_rank_external_results_filters_to_valid_ids_and_caps_length():
    candidates = [{"pid": "a", "name": "A"}, {"pid": "b", "name": "B"}, {"pid": "c", "name": "C"}]
    fake_payload = {
        "picks": [
            {"id": "b", "reason": "matches"},
            {"id": "does-not-exist", "reason": "ignored"},
            {"id": "a", "reason": "also matches"},
            {"id": "c", "reason": "third"},
        ]
    }
    with patch("backend.app.agent.llm._converse_json", return_value=fake_payload):
        result = llm.rank_external_results("query", candidates, id_key="pid", max_results=2)
    assert [r["pid"] for r in result] == ["b", "a"]
    assert result[0]["reason"] == "matches"
    assert result[0]["name"] == "B"


def test_rank_external_results_returns_none_when_bedrock_unavailable():
    with patch("backend.app.agent.llm._converse_json", return_value=None):
        assert llm.rank_external_results("q", [{"pid": "a"}], id_key="pid", max_results=3) is None


def test_rank_external_results_returns_none_when_no_valid_picks():
    candidates = [{"pid": "a"}]
    with patch("backend.app.agent.llm._converse_json", return_value={"picks": [{"id": "z"}]}):
        assert llm.rank_external_results("q", candidates, id_key="pid", max_results=3) is None
