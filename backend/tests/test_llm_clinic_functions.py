from unittest.mock import patch

from backend.app.agent import llm
from backend.app.services import health_catalog


def test_triage_symptom_falls_back_to_keyword_rules_without_bedrock():
    with patch("backend.app.agent.llm._converse_json", return_value=None):
        result = llm.triage_symptom("我一直咳嗽，喉嚨很癢")
    assert result["specialty"] == "耳鼻喉科"
    assert result["advisory"]


def test_triage_symptom_defaults_to_family_medicine_for_unmatched_symptoms():
    with patch("backend.app.agent.llm._converse_json", return_value=None):
        result = llm.triage_symptom("完全不相關的描述xyz")
    assert result["specialty"] == "家醫科"


def test_triage_symptom_uses_bedrock_result_when_valid():
    with patch(
        "backend.app.agent.llm._converse_json",
        return_value={"specialty": "耳鼻喉科", "advisory": "多喝溫水喔"},
    ):
        result = llm.triage_symptom("喉嚨癢癢的")
    assert result == {"specialty": "耳鼻喉科", "advisory": "多喝溫水喔"}


def test_triage_symptom_ignores_bedrock_result_with_invalid_specialty():
    with patch(
        "backend.app.agent.llm._converse_json",
        return_value={"specialty": "不存在的科別", "advisory": "..."},
    ):
        result = llm.triage_symptom("喉嚨癢癢的")
    assert result["specialty"] in llm._VALID_SPECIALTIES


def test_recommend_clinic_returns_none_for_empty_candidates():
    assert llm.recommend_clinic("咳嗽", []) is None


def test_recommend_clinic_falls_back_to_first_open_candidate_without_bedrock():
    candidates = [
        {"id": "c1", "name": "A診所", "is_open_now": False},
        {"id": "c2", "name": "B診所", "is_open_now": True},
    ]
    with patch("backend.app.agent.llm._converse_json", return_value=None):
        result = llm.recommend_clinic("咳嗽", candidates)
    assert result["id"] == "c2"


def test_recommend_clinic_uses_bedrock_choice_when_id_is_valid():
    candidates = [{"id": "c1", "name": "A診所", "is_open_now": True}]
    with patch(
        "backend.app.agent.llm._converse_json",
        return_value={"id": "c1", "reason": "距離最近"},
    ):
        result = llm.recommend_clinic("咳嗽", candidates)
    assert result == {"id": "c1", "reason": "距離最近"}


def test_recommend_clinic_ignores_bedrock_choice_with_unknown_id():
    candidates = [{"id": "c1", "name": "A診所", "is_open_now": True}]
    with patch(
        "backend.app.agent.llm._converse_json",
        return_value={"id": "does-not-exist", "reason": "..."},
    ):
        result = llm.recommend_clinic("咳嗽", candidates)
    assert result["id"] == "c1"


def test_recommend_health_products_falls_back_to_keyword_matching_without_bedrock():
    products = health_catalog.list_products()
    with patch("backend.app.agent.llm._converse_json", return_value=None):
        result = llm.recommend_health_products_for_symptom("喉嚨癢癢的，一直咳嗽", products)
    assert result["fallback_used"] is True
    assert len(result["recommendations"]) > 0


def test_recommend_health_products_uses_bedrock_choice_when_valid():
    products = health_catalog.list_products()
    valid_id = products[0]["id"]
    with patch(
        "backend.app.agent.llm._converse_json",
        return_value={"recommendations": [{"product_id": valid_id, "reason": "適合喉嚨不適"}]},
    ):
        result = llm.recommend_health_products_for_symptom("喉嚨癢", products)
    assert result["fallback_used"] is False
    assert result["recommendations"] == [{"product_id": valid_id, "reason": "適合喉嚨不適"}]
