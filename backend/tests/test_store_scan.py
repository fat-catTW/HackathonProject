import tempfile
from pathlib import Path

from backend.app.services.store import MemoryStore


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
