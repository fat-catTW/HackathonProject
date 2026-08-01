from backend.app.services import weather


def test_get_weather_uses_live_data_when_available(monkeypatch):
    monkeypatch.setattr(weather, "_CACHE", {})
    monkeypatch.setattr(
        weather,
        "_fetch_live_weather",
        lambda city: {
            "city": city,
            "temperature": 28.0,
            "high": 31.0,
            "low": 24.0,
            "condition": "多雲",
            "is_large_temp_swing": False,
            "fallback_used": False,
        },
    )
    result = weather.get_weather("台中市")
    assert result["fallback_used"] is False
    assert result["city"] == "台中市"
    assert result["temperature"] == 28.0


def test_get_weather_falls_back_when_live_fetch_fails(monkeypatch):
    monkeypatch.setattr(weather, "_CACHE", {})
    monkeypatch.setattr(weather, "_fetch_live_weather", lambda city: None)
    result = weather.get_weather("台中市")
    assert result["fallback_used"] is True
    assert result["city"] == "台中市"
    assert isinstance(result["temperature"], float)


def test_get_weather_defaults_to_default_city_when_blank(monkeypatch):
    monkeypatch.setattr(weather, "_CACHE", {})
    monkeypatch.setattr(weather, "_fetch_live_weather", lambda city: None)
    result = weather.get_weather("")
    assert result["city"] == weather.DEFAULT_CITY


def test_get_weather_caches_within_ttl(monkeypatch):
    monkeypatch.setattr(weather, "_CACHE", {})
    calls = {"count": 0}

    def fake_fetch(city):
        calls["count"] += 1
        return {
            "city": city,
            "temperature": 28.0,
            "high": 31.0,
            "low": 24.0,
            "condition": "多雲",
            "is_large_temp_swing": False,
            "fallback_used": False,
        }

    monkeypatch.setattr(weather, "_fetch_live_weather", fake_fetch)
    weather.get_weather("台中市")
    weather.get_weather("台中市")
    assert calls["count"] == 1


def test_fallback_weather_flags_large_temp_swing_for_known_city():
    result = weather._fallback_weather("台中市")
    assert result["high"] - result["low"] >= 7
    assert result["is_large_temp_swing"] is True


def test_fallback_weather_uses_generic_default_for_unknown_city():
    result = weather._fallback_weather("某個沒有資料的城市")
    assert result["city"] == "某個沒有資料的城市"
    assert result["fallback_used"] is True
