from unittest.mock import patch

from backend.app.agent import agent
from backend.app.services import catalog


def test_clinic_appointment_registered_in_service_list():
    services = catalog.list_services()
    ids = [s["id"] for s in services]
    assert "clinic_appointment" in ids


def test_agent_redirects_to_clinic_appointment_flow_page():
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
        result = agent.handle_message("user-1", "sess-1", state, "我想掛號看醫生")

    assert result["redirect_path"] == "/services/clinic_appointment"
    state = result["state"]
    assert state["service_id"] is None
    assert state["request_id"] is None
