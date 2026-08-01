from unittest.mock import patch

from backend.app.services import external_search


def test_google_text_search_returns_none_without_api_key(monkeypatch):
    monkeypatch.setattr(external_search, "get_settings", lambda: type(
        "S", (), {"google_search_api_key": "", "google_search_engine_id": ""}
    )())
    assert external_search.google_text_search("foo") is None


def test_google_text_search_returns_parsed_items(monkeypatch):
    monkeypatch.setattr(external_search, "get_settings", lambda: type(
        "S", (), {"google_search_api_key": "k", "google_search_engine_id": "cx"}
    )())

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"items": [{"title": "T", "snippet": "S", "link": "L"}]}

    with patch("backend.app.services.external_search.httpx.get", return_value=FakeResponse()):
        result = external_search.google_text_search("foo")
    assert result == [{"title": "T", "snippet": "S", "link": "L"}]


def test_google_text_search_returns_none_on_http_error(monkeypatch):
    monkeypatch.setattr(external_search, "get_settings", lambda: type(
        "S", (), {"google_search_api_key": "k", "google_search_engine_id": "cx"}
    )())
    with patch("backend.app.services.external_search.httpx.get", side_effect=Exception("boom")):
        assert external_search.google_text_search("foo") is None


def test_google_places_search_returns_none_without_api_key(monkeypatch):
    monkeypatch.setattr(external_search, "get_settings", lambda: type(
        "S", (), {"google_maps_api_key": ""}
    )())
    assert external_search.google_places_search("foo") is None


def test_google_places_search_returns_parsed_results(monkeypatch):
    monkeypatch.setattr(external_search, "get_settings", lambda: type(
        "S", (), {"google_maps_api_key": "k"}
    )())

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "status": "OK",
                "results": [
                    {"place_id": "p1", "name": "N", "formatted_address": "A", "rating": 4.2}
                ],
            }

    with patch("backend.app.services.external_search.httpx.get", return_value=FakeResponse()):
        result = external_search.google_places_search("foo")
    assert result == [{"place_id": "p1", "name": "N", "address": "A", "rating": 4.2}]
