"""AWS-first behavior regression tests."""
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agent import tools  # noqa: E402
from app.agent.agent import _available_services, _model_reply, new_state  # noqa: E402
from app.services import conversation_memory as memory_module  # noqa: E402
from app.services import store as store_module  # noqa: E402


def test_model_reply_prefers_llm_when_available(monkeypatch):
    monkeypatch.setattr("app.agent.agent.llm.is_available", lambda: True)
    monkeypatch.setattr("app.agent.agent.llm.compose_reply", lambda **kwargs: "llm reply")
    monkeypatch.setattr("app.agent.agent._long_term_memory_context", lambda actor_id, query: "None")
    state = new_state()
    assert _model_reply("actor-1", state, "confirm", summary="summary") == "llm reply"


def test_available_services_skips_local_catalog_fallback_when_not_mock(monkeypatch):
    monkeypatch.setattr(
        "app.agent.agent.tools.call",
        lambda name, params, auth_token=None: {
            "success": False,
            "error": {"code": "SERVICE_CATALOG_UNAVAILABLE", "message": "boom"},
        },
    )
    monkeypatch.setattr("app.agent.agent.get_settings", lambda: SimpleNamespace(use_mock=False))
    assert _available_services() is None


def test_mcp_tool_failure_does_not_fallback(monkeypatch):
    monkeypatch.setattr(
        "app.agent.tools.get_settings",
        lambda: SimpleNamespace(
            use_mock=False,
            agent_tool_mode="mcp",
            lambda_tooling_enabled=False,
        ),
    )
    monkeypatch.setattr(
        "app.agent.tools._invoke_mcp_gateway",
        lambda tool_name, params, auth_token=None: {
            "success": False,
            "error": {"code": "TOOL_INVOCATION_FAILED", "message": "gateway down"},
        },
    )

    def unexpected_fallback(tool_name, params):
        raise AssertionError("fallback tool path should not run")

    monkeypatch.setattr("app.agent.tools._fallback_tool_call", unexpected_fallback)
    result = tools.call("submit_service_request", {"service_id": "svc"})
    assert result["success"] is False
    assert result["error"]["code"] == "TOOL_INVOCATION_FAILED"


def test_build_store_uses_direct_dynamodb_in_non_mock_mode(monkeypatch):
    sentinel = object()
    monkeypatch.setattr(
        "app.services.store.get_settings",
        lambda: SimpleNamespace(use_mock=False, dynamodb_table_name="ServiceAssistant"),
    )
    monkeypatch.setattr("app.services.store.DynamoDBStore", lambda table_name: sentinel)
    assert store_module.build_store() is sentinel


def test_build_conversation_memory_uses_agentcore_directly(monkeypatch):
    sentinel = object()
    monkeypatch.setattr(
        "app.services.conversation_memory.get_settings",
        lambda: SimpleNamespace(use_agentcore_memory=True, agentcore_memory_id="memory-123"),
    )
    monkeypatch.setattr(
        "app.services.conversation_memory.AgentCoreConversationMemory",
        lambda memory_id: sentinel,
    )
    assert memory_module.build_conversation_memory() is sentinel
