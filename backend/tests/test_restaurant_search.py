from unittest.mock import patch

from backend.app.services import external_search_cache, restaurant_search


def test_search_falls_back_to_internal_list_without_bedrock():
    with patch("backend.app.services.restaurant_search.llm.is_available", return_value=False):
        result = restaurant_search.search_restaurants("user-1", "台中市")
    assert len(result["restaurants"]) == 5
    assert all(r["source"] == "internal" for r in result["restaurants"])


def test_search_merges_and_caches_google_places_results():
    fake_places = [{"place_id": "p1", "name": "測試餐廳", "address": "台中市西區", "rating": 4.5}]
    fake_picks = [
        {"id": "p1", "name": "測試餐廳", "address": "台中市西區", "phone": "",
         "source": "google_places", "reason": "離你最近"}
    ]
    with patch("backend.app.services.restaurant_search.llm.is_available", return_value=True), \
         patch("backend.app.services.restaurant_search.llm.plan_external_query", return_value="台中市 餐廳"), \
         patch("backend.app.services.restaurant_search.external_search.google_places_search", return_value=fake_places), \
         patch("backend.app.services.restaurant_search.llm.rank_external_results", return_value=fake_picks):
        result = restaurant_search.search_restaurants("user-9", "台中市")

    assert result["restaurants"] == fake_picks
    cached = external_search_cache.get_result("user-9", "restaurant_search", "p1")
    assert cached == fake_picks[0]


def test_search_caps_at_five_results_when_ranking_unavailable():
    with patch("backend.app.services.restaurant_search.llm.is_available", return_value=True), \
         patch("backend.app.services.restaurant_search.llm.plan_external_query", return_value=None), \
         patch("backend.app.services.restaurant_search.llm.rank_external_results", return_value=None):
        result = restaurant_search.search_restaurants("user-2", "台北市")
    assert len(result["restaurants"]) == 5
