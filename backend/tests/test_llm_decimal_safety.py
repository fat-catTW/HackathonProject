"""Regression tests for Decimal values (as returned by real DynamoDB reads,
see store.py's convert_floats_to_decimal for the write-side counterpart)
breaking json.dumps in llm.py's prompt-building. USE_MOCK=false + real
DynamoDB was never exercised by the existing mock-store-only test suite,
so this crashed in production the first time a session with a numeric
collected_fields value (e.g. people count) went through llm.compose_reply."""
from decimal import Decimal
from unittest.mock import patch

from backend.app.agent import llm


def test_json_safe_converts_whole_number_decimal_to_int():
    assert llm._json_safe(Decimal("5")) == 5
    assert isinstance(llm._json_safe(Decimal("5")), int)


def test_json_safe_converts_fractional_decimal_to_float():
    assert llm._json_safe(Decimal("1.5")) == 1.5
    assert isinstance(llm._json_safe(Decimal("1.5")), float)


def test_json_safe_recurses_into_nested_dicts_and_lists():
    value = {"people": Decimal("4"), "items": [{"price": Decimal("99.5")}]}
    assert llm._json_safe(value) == {"people": 4, "items": [{"price": 99.5}]}


def test_dumps_does_not_raise_on_decimal_values():
    llm._dumps({"people": Decimal("4")})


def test_compose_reply_does_not_raise_when_collected_fields_has_decimal():
    with patch("backend.app.agent.llm._converse_json", return_value={"reply": "好的"}) as mock_converse:
        reply = llm.compose_reply(
            phase="collect_field",
            collected_fields={"people": Decimal("5")},
            missing_field_question="請問哪一天？",
        )
    assert reply == "好的"
    mock_converse.assert_called_once()
