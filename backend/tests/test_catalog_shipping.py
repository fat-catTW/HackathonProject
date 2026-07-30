from backend.app.services import catalog


def test_package_shipping_schema_field_order_and_branching():
    schema = catalog.get_service_schema("package_shipping")
    field_ids = [f["id"] for f in schema["fields"]]
    assert field_ids == [
        "pickup_method",
        "sender_address",
        "receiver_address",
        "sender_store",
        "receiver_store",
        "weight_kg",
        "length_cm",
        "width_cm",
        "height_cm",
        "item_description",
        "declared_value",
        "pickup_time_slot",
        "contact_name",
        "phone",
    ]

    fields_by_id = {f["id"]: f for f in schema["fields"]}
    assert fields_by_id["sender_address"]["visibleWhen"] == {
        "fieldId": "pickup_method",
        "value": "HOME_PICKUP",
    }
    assert fields_by_id["sender_store"]["visibleWhen"] == {
        "fieldId": "pickup_method",
        "value": "STORE_TO_STORE",
    }
    assert fields_by_id["sender_address"]["type"] == "address"
    assert fields_by_id["pickup_method"]["options"] == ["HOME_PICKUP", "STORE_TO_STORE"]


def test_package_shipping_vendor_is_two():
    assert catalog.vendor_id_for_service("package_shipping") == 2
