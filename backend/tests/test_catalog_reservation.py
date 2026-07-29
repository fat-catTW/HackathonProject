from backend.app.services import catalog


def test_restaurant_reservation_registered_in_service_list():
    services = catalog.list_services()
    ids = [s["id"] for s in services]
    assert "restaurant_reservation" in ids


def test_restaurant_reservation_schema_has_required_fields():
    schema = catalog.get_service_schema("restaurant_reservation")
    field_ids = [f["id"] for f in schema["fields"]]
    assert field_ids == [
        "restaurant_id",
        "reserved_date",
        "time_slot",
        "people",
        "contact_name",
        "phone",
        "is_premium",
    ]


def test_restaurant_reservation_restaurant_field_lists_all_six_ids_as_options():
    schema = catalog.get_service_schema("restaurant_reservation")
    restaurant_field = next(f for f in schema["fields"] if f["id"] == "restaurant_id")
    assert set(restaurant_field["options"]) == {"r001", "r002", "r003", "r004", "r005", "r006"}


def test_restaurant_reservation_keywords_trigger_detection():
    service_id, _ = __import__("backend.app.agent.nlu", fromlist=["detect_service"]).detect_service("我想訂餐廳吃飯")
    assert service_id == "restaurant_reservation"
