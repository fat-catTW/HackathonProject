from backend.app.services import catalog


def test_food_delivery_schema_includes_note_field():
    schema = catalog.get_service_schema("food_delivery")
    field_ids = [f["id"] for f in schema["fields"]]
    assert field_ids == ["address", "store_id", "goods", "contact_name", "note"]


def test_food_delivery_store_question_lists_store_names():
    schema = catalog.get_service_schema("food_delivery")
    store_field = next(f for f in schema["fields"] if f["id"] == "store_id")
    assert "好味道便當" in store_field["question"]
    assert "鮮茶道" in store_field["question"]
    assert "義式小館" in store_field["question"]
