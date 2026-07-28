"""Session, preference, and request storage backends."""
from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from time import monotonic

from ..config import get_settings
from .aws import get_aws_resource

TZ = timezone(timedelta(hours=8))


def now_iso() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


class BaseStore:
    backend_name = "base"

    def put_item(self, item: dict) -> None:
        raise NotImplementedError

    def put_item_if_absent(self, item: dict) -> bool:
        """Write only when (PK, SK) is absent; returns whether the write happened."""
        raise NotImplementedError

    def get_item(self, pk: str, sk: str) -> dict | None:
        raise NotImplementedError

    def delete_item(self, pk: str, sk: str) -> None:
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

    # ---- Auth: credentials, profiles, and issued tokens ----
    def save_credential_if_absent(self, email: str, credential: dict) -> bool:
        """Claim an email address; False means it was already registered."""
        credential["PK"] = f"AUTH#EMAIL#{email}"
        credential["SK"] = "CREDENTIAL"
        credential["entity_type"] = "USER_CREDENTIAL"
        return self.put_item_if_absent(credential)

    def get_credential(self, email: str) -> dict | None:
        return self.get_item(f"AUTH#EMAIL#{email}", "CREDENTIAL")

    def delete_credential(self, email: str) -> None:
        self.delete_item(f"AUTH#EMAIL#{email}", "CREDENTIAL")

    def save_user_profile(self, actor_id: str, profile: dict) -> None:
        profile["PK"] = f"USER#{actor_id}"
        profile["SK"] = "PROFILE"
        profile["entity_type"] = "USER_PROFILE"
        self.put_item(profile)

    def get_user_profile(self, actor_id: str) -> dict | None:
        return self.get_item(f"USER#{actor_id}", "PROFILE")

    def save_auth_token(self, token: str, session: dict) -> None:
        session["PK"] = f"AUTH#TOKEN#{token}"
        session["SK"] = "SESSION"
        session["entity_type"] = "AUTH_TOKEN"
        self.put_item(session)

    def get_auth_token(self, token: str) -> dict | None:
        return self.get_item(f"AUTH#TOKEN#{token}", "SESSION")

    def delete_auth_token(self, token: str) -> None:
        self.delete_item(f"AUTH#TOKEN#{token}", "SESSION")

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

    backend_name = "memory+file"

    def __init__(self, storage_path: Path | None = None) -> None:
        self._items: dict[tuple[str, str], dict] = {}
        self._lock = threading.Lock()
        self._req_seq = 0
        self._storage_path = storage_path
        self._load()

    def put_item(self, item: dict) -> None:
        with self._lock:
            self._items[(item["PK"], item["SK"])] = item
            self._flush()

    def put_item_if_absent(self, item: dict) -> bool:
        key = (item["PK"], item["SK"])
        with self._lock:
            if key in self._items:
                return False
            self._items[key] = item
            self._flush()
            return True

    def get_item(self, pk: str, sk: str) -> dict | None:
        with self._lock:
            item = self._items.get((pk, sk))
            return dict(item) if item else None

    def delete_item(self, pk: str, sk: str) -> None:
        with self._lock:
            if self._items.pop((pk, sk), None) is not None:
                self._flush()

    def query_prefix(self, pk: str, sk_prefix: str) -> list[dict]:
        with self._lock:
            return [dict(v) for (p, s), v in self._items.items() if p == pk and s.startswith(sk_prefix)]

    def next_request_id(self) -> str:
        with self._lock:
            self._req_seq += 1
            self._flush()
            return f"REQ-{datetime.now(TZ):%Y%m%d}-{self._req_seq:03d}"

    def _load(self) -> None:
        if not self._storage_path or not self._storage_path.exists():
            return
        try:
            payload = json.loads(self._storage_path.read_text(encoding="utf-8"))
        except Exception:
            return

        items = payload.get("items") or []
        self._req_seq = int(payload.get("req_seq") or 0)
        for item in items:
            pk = item.get("PK")
            sk = item.get("SK")
            if pk and sk:
                self._items[(pk, sk)] = item

    def _flush(self) -> None:
        if not self._storage_path:
            return
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "req_seq": self._req_seq,
            "items": list(self._items.values()),
        }
        self._storage_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


class DynamoDBStore(BaseStore):
    backend_name = "dynamodb"

    def __init__(self, table_name: str) -> None:
        self._table = get_aws_resource("dynamodb").Table(table_name)

    def put_item(self, item: dict) -> None:
        self._table.put_item(Item=item)

    def put_item_if_absent(self, item: dict) -> bool:
        from botocore.exceptions import ClientError

        try:
            self._table.put_item(
                Item=item,
                ConditionExpression="attribute_not_exists(PK) AND attribute_not_exists(SK)",
            )
            return True
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
                return False
            raise

    def get_item(self, pk: str, sk: str) -> dict | None:
        return self._table.get_item(Key={"PK": pk, "SK": sk}).get("Item")

    def delete_item(self, pk: str, sk: str) -> None:
        self._table.delete_item(Key={"PK": pk, "SK": sk})

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


class ResilientStore(BaseStore):
    """Keep local demo flows working when DynamoDB is temporarily unavailable."""

    backend_name = "local-file+best-effort-dynamodb"

    def __init__(self, primary: BaseStore, fallback: BaseStore) -> None:
        self._primary = primary
        self._fallback = fallback
        self._primary_disabled_until = 0.0
        self._lock = threading.Lock()

    def _primary_available(self) -> bool:
        with self._lock:
            return monotonic() >= self._primary_disabled_until

    def _mark_primary_unavailable(self, cooldown_seconds: int = 300) -> None:
        with self._lock:
            self._primary_disabled_until = monotonic() + cooldown_seconds

    def put_item(self, item: dict) -> None:
        fallback_item = dict(item)
        self._fallback.put_item(fallback_item)
        if not self._primary_available():
            return
        try:
            self._primary.put_item(item)
        except Exception:
            self._mark_primary_unavailable()
            return

    def put_item_if_absent(self, item: dict) -> bool:
        # Uniqueness must be decided by the primary whenever it is reachable —
        # the local fallback only sees this process's own writes.
        if self._primary_available():
            try:
                if not self._primary.put_item_if_absent(item):
                    return False
                self._fallback.put_item(dict(item))
                return True
            except Exception:
                self._mark_primary_unavailable()
        return self._fallback.put_item_if_absent(dict(item))

    def delete_item(self, pk: str, sk: str) -> None:
        self._fallback.delete_item(pk, sk)
        if not self._primary_available():
            return
        try:
            self._primary.delete_item(pk, sk)
        except Exception:
            self._mark_primary_unavailable()

    def get_item(self, pk: str, sk: str) -> dict | None:
        item = self._fallback.get_item(pk, sk)
        if item is not None:
            return item
        if not self._primary_available():
            return None
        try:
            return self._primary.get_item(pk, sk)
        except Exception:
            self._mark_primary_unavailable()
            return None

    def query_prefix(self, pk: str, sk_prefix: str) -> list[dict]:
        fallback_items = self._fallback.query_prefix(pk, sk_prefix)
        if fallback_items:
            return fallback_items
        if not self._primary_available():
            return []
        try:
            return self._primary.query_prefix(pk, sk_prefix)
        except Exception:
            self._mark_primary_unavailable()
            return []


def build_store() -> BaseStore:
    settings = get_settings()
    if settings.use_mock:
        return MemoryStore()
    return DynamoDBStore(settings.dynamodb_table_name)


STORE = build_store()
