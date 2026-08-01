"""Read-only calendar view: groups the actor's own service requests by date."""
from fastapi import APIRouter, Depends

from ..auth.cognito import CurrentUser, get_current_user
from ..services import statuses
from ..services.store import STORE

router = APIRouter()

_DATE_FIELDS = ("preferred_date", "reserved_date", "pickup_time_slot", "sender_date")


def _request_date(form_data: dict) -> str | None:
    for field_id in _DATE_FIELDS:
        value = form_data.get(field_id)
        if isinstance(value, str) and len(value) == 10 and value[4] == "-" and value[7] == "-":
            return value
    return None


@router.get("/api/calendar")
def get_calendar(user: CurrentUser = Depends(get_current_user)):
    requests = STORE.list_requests(user.sub)
    by_date: dict[str, list[dict]] = {}
    for request in requests:
        form_data = request.get("form_data") or {}
        request_date = _request_date(form_data)
        if not request_date:
            continue
        status = request.get("status", "")
        by_date.setdefault(request_date, []).append(
            {
                "request_id": request["request_id"],
                "service_name": request.get("service_name", ""),
                "status": status,
                "status_label": statuses.status_label(status),
                "created_at": request.get("created_at", ""),
            }
        )

    days = [
        {
            "date": request_date,
            "items": [
                {k: v for k, v in item.items() if k != "created_at"}
                for item in sorted(items, key=lambda x: x["created_at"])
            ],
        }
        for request_date, items in sorted(by_date.items())
    ]
    return {"days": days}
