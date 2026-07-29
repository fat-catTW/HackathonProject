from backend.app.services import restaurant_catalog


def test_list_restaurants_returns_at_most_six():
    result = restaurant_catalog.list_restaurants()
    assert 1 <= len(result) <= 6


def test_get_restaurant_found():
    restaurant = restaurant_catalog.get_restaurant("r001")
    assert restaurant is not None
    assert restaurant["name"] == "22世紀風味館 信義旗艦店"
    assert restaurant["phone"] == "02-2723-0022"


def test_get_restaurant_not_found():
    assert restaurant_catalog.get_restaurant("does-not-exist") is None


def test_supports_third_party_booking_true_for_r001():
    assert restaurant_catalog.supports_third_party_booking("r001") is True


def test_supports_third_party_booking_false_for_r005():
    assert restaurant_catalog.supports_third_party_booking("r005") is False


def test_supports_third_party_booking_false_for_unknown_restaurant():
    assert restaurant_catalog.supports_third_party_booking("nope") is False
