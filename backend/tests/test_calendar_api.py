import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.api import calendar
from backend.app.services import store as store_module


@pytest.fixture(autouse=True)
def isolated_store(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        test_store = store_module.MemoryStore(storage_path=Path(tmp) / "store.json")
        monkeypatch.setattr(store_module, "STORE", test_store)
        monkeypatch.setattr(calendar, "STORE", test_store)
        yield test_store


def _auth_headers(client: TestClient) -> dict:
    accounts = client.get("/api/auth/demo-accounts").json()["accounts"]
    token = accounts[0]["token"]
    return {"Authorization": f"Bearer {token}"}


def test_calendar_groups_requests_by_date(isolated_store):
    client = TestClient(app)
    headers = _auth_headers(client)
    # Directly seed two requests with different date-bearing fields, mimicking
    # what home_cleaning (preferred_date) and restaurant_reservation (reserved_date) store.
    isolated_store.save_request(
        "user-vincent",
        {
            "request_id": "REQ-1",
            "service_id": "home_cleaning",
            "service_name": "居家清潔",
            "status": "SUBMITTED",
            "form_data": {"preferred_date": "2026-08-02", "preferred_time_slot": "14:00"},
            "created_at": "2026-08-01T10:00:00+08:00",
        },
    )
    isolated_store.save_request(
        "user-vincent",
        {
            "request_id": "REQ-2",
            "service_id": "restaurant_reservation",
            "service_name": "餐廳訂位",
            "status": "CONFIRMED",
            "form_data": {"reserved_date": "2026-08-02", "time_slot": "LUNCH"},
            "created_at": "2026-08-01T10:05:00+08:00",
        },
    )

    response = client.get("/api/calendar", headers=headers)
    body = response.json()

    assert response.status_code == 200
    assert body["days"] == [
        {
            "date": "2026-08-02",
            "items": [
                {
                    "request_id": "REQ-1",
                    "service_name": "居家清潔",
                    "status": "SUBMITTED",
                    "status_label": "等待廠商確認",
                },
                {
                    "request_id": "REQ-2",
                    "service_name": "餐廳訂位",
                    "status": "CONFIRMED",
                    "status_label": "已確認",
                },
            ],
        }
    ]
