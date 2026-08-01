from unittest.mock import patch

from backend.app.agent import agent
from backend.app.services import catalog, clinic_catalog


def test_clinic_appointment_registered_in_service_list():
    services = catalog.list_services()
    ids = [s["id"] for s in services]
    assert "clinic_appointment" in ids


def test_agent_answers_clinic_recommendation_with_cards(monkeypatch):
    """clinic_appointment is a one-shot query-and-answer service (like
    health_product_recommendation): the agent must run the same Bedrock
    symptom triage + clinic recommendation the manual flow page uses and
    return clinic cards for the chat panel to render, instead of just
    telling the user to go fill a form."""
    clinic_catalog._cache.clear()
    monkeypatch.setattr(clinic_catalog, "_fetch_all_clinics", lambda: None)
    monkeypatch.setattr(
        agent.llm,
        "triage_symptom",
        lambda symptom_text: {"specialty": "家醫科", "advisory": "多休息、多喝溫水。"},
    )

    state = agent.new_state()
    with patch(
        "backend.app.agent.agent._available_services",
        return_value=[
            {
                "id": "clinic_appointment",
                "name": "診所掛號",
                "description": "描述症狀，AI 幫您找附近診所並掛號",
                "keywords": ["掛號", "看醫生", "診所", "看診"],
            }
        ],
    ):
        result = agent.handle_message("user-1", "sess-1", state, "我的腰很痛，想掛號看診所")

    assert result["redirect_path"] is None
    recommendation = result["clinic_recommendation"]
    assert recommendation is not None
    assert recommendation["clinics"]
    assert recommendation["symptom_note"] == "我的腰很痛，想掛號看診所"
    state = result["state"]
    assert state["service_id"] is None
    assert state["request_id"] is None


def test_agent_clinic_recommendation_detects_district_from_message(monkeypatch):
    """使用者提到「豐原」時應該查豐原區的診所，而不是永遠用預設的西屯區。"""
    clinic_catalog._cache.clear()
    monkeypatch.setattr(clinic_catalog, "_fetch_all_clinics", lambda: None)
    monkeypatch.setattr(
        clinic_catalog,
        "_FALLBACK_CLINICS",
        [
            {
                "id": "clinic-fengyuan-001",
                "name": "豐原內科診所",
                "specialties": ["內科"],
                "address": "台中市豐原區中正路1號",
                "phone": "04-1111-2222",
                "holiday_duty_cname": "",
            }
        ],
    )
    monkeypatch.setattr(
        agent.llm,
        "triage_symptom",
        lambda symptom_text: {"specialty": "內科", "advisory": "多休息、多喝溫水。"},
    )

    state = agent.new_state()
    with patch(
        "backend.app.agent.agent._available_services",
        return_value=[
            {
                "id": "clinic_appointment",
                "name": "診所掛號",
                "description": "描述症狀，AI 幫您找附近診所並掛號",
                "keywords": ["掛號", "看醫生", "診所", "看診"],
            }
        ],
    ):
        result = agent.handle_message("user-1", "sess-1", state, "我住豐原，我的腰很痛，想掛號看診所")

    recommendation = result["clinic_recommendation"]
    assert recommendation is not None
    assert recommendation["district"] == "豐原區"
    assert any(c["name"] == "豐原內科診所" for c in recommendation["clinics"])
