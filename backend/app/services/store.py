"""Session, preference, and request storage backends."""
from __future__ import annotations

import threading
import uuid
from datetime import datetime, timedelta, timezone

from ..config import get_settings
from .aws import get_aws_resource

TZ = timezone(timedelta(hours=8))


def now_iso() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


class BaseStore:
    backend_name = "base"

    def put_item(self, item: dict) -> None:
        raise NotImplementedError

    def get_item(self, pk: str, sk: str) -> dict | None:
        raise NotImplementedError

    def query_prefix(self, pk: str, sk_prefix: str) -> list[dict]:
        raise NotImplementedError

    def next_request_id(self) -> str:
        return f"REQ-{datetime.now(TZ):%Y%m%d}-{uuid.uuid4().hex[:6].upper()}"

    def save_request(self, actor_id: str, request: dict) -> None:
        request["PK"] = f"USER#{actor_id}"
        request["SK"] = f"REQUEST#{request['request_id']}"
        request["entity_type"] = "SERVICE_REQUEST"
        request["updated_at"] = now_iso()
        self.put_item(request)

    def get_request(self, actor_id: str, request_id: str) -> dict | None:
        return self.get_item(f"USER#{actor_id}", f"REQUEST#{request_id}")

    def list_requests(self, actor_id: str) -> list[dict]:
        items = self.query_prefix(f"USER#{actor_id}", "REQUEST#")
        return sorted(items, key=lambda x: x.get("created_at", ""), reverse=True)

    def save_session(self, actor_id: str, session: dict) -> None:
        session["PK"] = f"USER#{actor_id}"
        session["SK"] = f"SESSION#{session['session_id']}"
        self.put_item(session)

    def get_session(self, actor_id: str, session_id: str) -> dict | None:
        return self.get_item(f"USER#{actor_id}", f"SESSION#{session_id}")

    def get_preferences(self, actor_id: str) -> dict:
        item = self.get_item(f"USER#{actor_id}", "PREFERENCES")
        return item.get("data", {}) if item else {}

    def save_preferences(self, actor_id: str, prefs: dict) -> None:
        merged = self.get_preferences(actor_id) | prefs
        self.put_item(
            {
                "PK": f"USER#{actor_id}",
                "SK": "PREFERENCES",
                "entity_type": "PREFERENCES",
                "data": merged,
                "updated_at": now_iso(),
            }
        )

    def get_long_term_memory(self, actor_id: str) -> dict:
        item = self.get_item(f"USER#{actor_id}", "LONG_TERM_MEMORY")
        return item.get("data", {}) if item else {}

    def save_long_term_memory(self, actor_id: str, memory: dict) -> None:
        merged = self.get_long_term_memory(actor_id) | memory
        self.put_item(
            {
                "PK": f"USER#{actor_id}",
                "SK": "LONG_TERM_MEMORY",
                "entity_type": "LONG_TERM_MEMORY",
                "data": merged,
                "updated_at": now_iso(),
            }
        )


class MemoryStore(BaseStore):
    """Thread-safe in-memory store used for mock mode and tests."""

    backend_name = "memory"

    def __init__(self) -> None:
        self._items: dict[tuple[str, str], dict] = {}
        self._lock = threading.Lock()
        self._req_seq = 0

    def put_item(self, item: dict) -> None:
        with self._lock:
            self._items[(item["PK"], item["SK"])] = item

    def get_item(self, pk: str, sk: str) -> dict | None:
        return self._items.get((pk, sk))

    def query_prefix(self, pk: str, sk_prefix: str) -> list[dict]:
        return [v for (p, s), v in self._items.items() if p == pk and s.startswith(sk_prefix)]

    def next_request_id(self) -> str:
        with self._lock:
            self._req_seq += 1
            return f"REQ-{datetime.now(TZ):%Y%m%d}-{self._req_seq:03d}"


class DynamoDBStore(BaseStore):
    backend_name = "dynamodb"

    def __init__(self, table_name: str) -> None:
        self._table = get_aws_resource("dynamodb").Table(table_name)

    def put_item(self, item: dict) -> None:
        self._table.put_item(Item=item)

    def get_item(self, pk: str, sk: str) -> dict | None:
        return self._table.get_item(Key={"PK": pk, "SK": sk}).get("Item")

    def query_prefix(self, pk: str, sk_prefix: str) -> list[dict]:
        from boto3.dynamodb.conditions import Key

        items: list[dict] = []
        start_key = None
        while True:
            kwargs = {
                "KeyConditionExpression": Key("PK").eq(pk) & Key("SK").begins_with(sk_prefix),
            }
            if start_key:
                kwargs["ExclusiveStartKey"] = start_key
            response = self._table.query(**kwargs)
            items.extend(response.get("Items", []))
            start_key = response.get("LastEvaluatedKey")
            if not start_key:
                return items


def build_store() -> BaseStore:
    settings = get_settings()
    if settings.use_mock:
        return MemoryStore()
    return DynamoDBStore(settings.dynamodb_table_name)


STORE = build_store()
