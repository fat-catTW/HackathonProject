import tempfile
from pathlib import Path

from backend.app.services.store import MemoryStore, ResilientStore


def test_scan_by_entity_type_returns_items_across_all_actors():
    with tempfile.TemporaryDirectory() as tmp:
        store = MemoryStore(storage_path=Path(tmp) / "store.json")
        store.save_request("user-a", {"request_id": "REQ-1", "service_id": "x", "status": "SUBMITTED"})
        store.save_request("user-b", {"request_id": "REQ-2", "service_id": "x", "status": "SUBMITTED"})
        store.save_preferences("user-a", {"last_address": "台北市"})

        items = store.scan_by_entity_type("SERVICE_REQUEST")

        ids = sorted(item["request_id"] for item in items)
        assert ids == ["REQ-1", "REQ-2"]


def test_scan_by_entity_type_ignores_other_entity_types():
    with tempfile.TemporaryDirectory() as tmp:
        store = MemoryStore(storage_path=Path(tmp) / "store.json")
        store.save_preferences("user-a", {"last_address": "台北市"})

        items = store.scan_by_entity_type("SERVICE_REQUEST")

        assert items == []


def test_resilient_store_scan_falls_through_to_primary_on_empty_fallback():
    """Test that scan_by_entity_type falls through to primary when fallback is empty."""
    with tempfile.TemporaryDirectory() as tmp:
        fallback = MemoryStore(storage_path=Path(tmp) / "fallback.json")
        primary = MemoryStore(storage_path=Path(tmp) / "primary.json")
        resilient = ResilientStore(primary=primary, fallback=fallback)

        # Save a request only to the primary store
        primary.save_request("user-a", {"request_id": "REQ-1", "service_id": "x", "status": "SUBMITTED"})

        # scan_by_entity_type should still find it even though fallback is empty
        items = resilient.scan_by_entity_type("SERVICE_REQUEST")

        assert len(items) == 1
        assert items[0]["request_id"] == "REQ-1"
