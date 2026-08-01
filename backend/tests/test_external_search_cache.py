import time
from unittest.mock import patch

from backend.app.services import external_search_cache


def test_store_and_get_result_round_trips():
    external_search_cache.store_results(
        "user-1", "ns", [{"id": "a", "name": "A"}, {"id": "b", "name": "B"}], id_key="id"
    )
    assert external_search_cache.get_result("user-1", "ns", "a") == {"id": "a", "name": "A"}


def test_get_result_returns_none_for_unknown_id():
    external_search_cache.store_results("user-1", "ns", [{"id": "a"}], id_key="id")
    assert external_search_cache.get_result("user-1", "ns", "missing") is None


def test_get_result_returns_none_when_never_searched():
    assert external_search_cache.get_result("user-2", "ns", "a") is None


def test_get_result_expires_after_ttl():
    external_search_cache.store_results("user-3", "ns", [{"id": "a"}], id_key="id")
    with patch("backend.app.services.external_search_cache.time.time", return_value=time.time() + 3600):
        assert external_search_cache.get_result("user-3", "ns", "a") is None
