"""資料儲存層。

Mock 模式：以記憶體字典模擬 DynamoDB 單表設計（PK/SK），介面刻意
與 boto3 Table 操作對齊，Milestone 5 換成 DynamoDBStore 時 API 不變。

Key 設計（設計書 §11）：
  Service Request : PK=USER#<actor_id>   SK=REQUEST#<request_id>
  Session         : PK=USER#<actor_id>   SK=SESSION#<session_id>
  Preferences     : PK=USER#<actor_id>   SK=PREFERENCES   （長期記憶 mock）
"""
from __future__ import annotations

import threading
from datetime import datetime, timezone, timedelta

TZ = timezone(timedelta(hours=8))


def now_iso() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


class MemoryStore:
    """單表 KV 儲存（thread-safe），模擬 DynamoDB。"""

    def __init__(self) -> None:
        self._items: dict[tuple[str, str], dict] = {}
        self._lock = threading.Lock()
        self._req_seq = 0

    # ---- 低階操作（對齊 DynamoDB put/get/query） ----
    def put_item(self, item: dict) -> None:
        with self._lock:
            self._items[(item["PK"], item["SK"])] = item

    def get_item(self, pk: str, sk: str) -> dict | None:
        return self._items.get((pk, sk))

    def query_prefix(self, pk: str, sk_prefix: str) -> list[dict]:
        return [
            v for (p, s), v in self._items.items()
            if p == pk and s.startswith(sk_prefix)
        ]

    # ---- Service Request ----
    def next_request_id(self) -> str:
        with self._lock:
            self._req_seq += 1
            return f"REQ-{datetime.now(TZ):%Y%m%d}-{self._req_seq:03d}"

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

    # ---- Session（短期記憶：對話事件，模擬 AgentCore Memory events） ----
    def save_session(self, actor_id: str, session: dict) -> None:
        session["PK"] = f"USER#{actor_id}"
        session["SK"] = f"SESSION#{session['session_id']}"
        self.put_item(session)

    def get_session(self, actor_id: str, session_id: str) -> dict | None:
        return self.get_item(f"USER#{actor_id}", f"SESSION#{session_id}")

    # ---- 長期記憶（偏好，模擬 /preferences/{actorId} namespace） ----
    def get_preferences(self, actor_id: str) -> dict:
        item = self.get_item(f"USER#{actor_id}", "PREFERENCES")
        return item.get("data", {}) if item else {}

    def save_preferences(self, actor_id: str, prefs: dict) -> None:
        merged = self.get_preferences(actor_id) | prefs
        self.put_item({
            "PK": f"USER#{actor_id}", "SK": "PREFERENCES",
            "entity_type": "PREFERENCES", "data": merged,
            "updated_at": now_iso(),
        })


STORE = MemoryStore()
