from backend.app.agent import nlu


def test_parse_restaurant_matches_full_name():
    assert nlu.parse_restaurant("我想訂22世紀風味館 信義旗艦店") == "r001"


def test_parse_restaurant_matches_partial_branch_name():
    assert nlu.parse_restaurant("板橋文化店有位子嗎") == "r002"


def test_parse_restaurant_returns_none_when_no_match():
    assert nlu.parse_restaurant("我想吃拉麵") is None


def test_parse_meal_slot_lunch():
    assert nlu.parse_meal_slot("中午想訂位") == "LUNCH"
    assert nlu.parse_meal_slot("我要訂午餐") == "LUNCH"


def test_parse_meal_slot_dinner():
    assert nlu.parse_meal_slot("晚餐時段") == "DINNER"
    assert nlu.parse_meal_slot("想約晚上吃飯") == "DINNER"


def test_parse_meal_slot_returns_none_when_ambiguous():
    assert nlu.parse_meal_slot("隨便都可以") is None
