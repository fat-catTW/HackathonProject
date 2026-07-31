"""Session, preference, and request storage backends."""
from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from time import monotonic

from ..config import get_settings
from . import catalog, contact_privacy
from .aws import get_aws_resource

TZ = timezone(timedelta(hours=8))


def now_iso() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def convert_floats_to_decimal(value):
    """Recursively convert Python float values to Decimal.

    DynamoDB (via boto3) rejects native float values outright ("Float
    types are not supported. Use Decimal types instead."), so any item
    written through DynamoDBStore needs this applied first — callers
    shouldn't have to know about this constraint themselves.
    """
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, dict):
        return {key: convert_floats_to_decimal(item) for key, item in value.items()}
    if isinstance(value, list):
        return [convert_floats_to_decimal(item) for item in value]
    return value


def vendor_id_of(request: dict) -> int | None:
    """案件所屬廠商；舊資料沒有帶 service_vendor_id 時回頭查服務目錄。"""
    vendor_id = request.get("service_vendor_id")
    if vendor_id is not None:
        return int(vendor_id)
    return catalog.vendor_id_for_service(request.get("service_id", ""))


def version_of(item: dict | None) -> int:
    """案件的樂觀鎖版本；Milestone 3 之前寫入的案件沒有這個欄位，視為 0。

    DynamoDB 讀回來的數字是 Decimal，一律轉成 int 再比對。
    """
    if not item:
        return 0
    try:
        return int(item.get("version") or 0)
    except (TypeError, ValueError):
        return 0


class BaseStore:
    backend_name = "base"

    def put_item(self, item: dict) -> None:
        raise NotImplementedError

    def put_item_if_absent(self, item: dict) -> bool:
        """Write only when (PK, SK) is absent; returns whether the write happened."""
        raise NotImplementedError

    def put_item_if_version(self, item: dict, expected_version: int) -> bool:
        """Write only when the stored item is still at expected_version (optimistic lock)."""
        raise NotImplementedError

    def get_item(self, pk: str, sk: str) -> dict | None:
        raise NotImplementedError

    def delete_item(self, pk: str, sk: str) -> None:
        raise NotImplementedError

    def query_prefix(self, pk: str, sk_prefix: str) -> list[dict]:
        raise NotImplementedError

    def scan_by_entity_type(self, entity_type: str) -> list[dict]:
        raise NotImplementedError

    def decrement_sku_stock(self, sku_id: str, quantity: int) -> bool:
        """Atomically decrement stock; return False (no write) if insufficient."""
        raise NotImplementedError

    def next_request_id(self) -> str:
        return f"REQ-{datetime.now(TZ):%Y%m%d}-{uuid.uuid4().hex[:6].upper()}"

    def _stamp_request(self, actor_id: str, request: dict) -> None:
        """補齊 key 欄位並把版本推進一號。

        每次寫入都換版本，讀到舊版本的人（例如廠商後台開著的另一個分頁）帶著
        過期版本回來時就會被 save_request_if_version 擋下。
        """
        request["PK"] = f"USER#{actor_id}"
        request["SK"] = f"REQUEST#{request['request_id']}"
        request["entity_type"] = "SERVICE_REQUEST"
        request["updated_at"] = now_iso()
        request["version"] = version_of(request) + 1

    def _for_storage(self, request: dict) -> dict:
        """把聯絡欄位換成密文，並附上遮罩對照表（Milestone 15）。

        加密只在這個出口做，所有 save_request 的呼叫端（送單、外送、訂位、商城…）
        就都不必記得這件事，也不會有人漏掉。回傳副本而非就地修改：呼叫端手上的
        dict 還要拿來組回應、扣庫存，換成密文只會讓它們讀到亂碼。
        """
        form_data = request.get("form_data")
        if not isinstance(form_data, dict) or not form_data:
            return request
        if contact_privacy.is_fully_encrypted(form_data) and "form_data_masked" in request:
            # 已經是儲存後的樣子（例如廠商後台只改狀態就原樣寫回），不必重跑一次
            # 加密——密文每次都不同，重算只是徒增寫入量與 KMS 呼叫。
            return request
        plain = contact_privacy.decrypt_form_data(form_data)
        return dict(request) | {
            "form_data": contact_privacy.encrypt_form_data(plain),
            "form_data_masked": contact_privacy.masked_form_data(plain),
        }

    @staticmethod
    def _decrypted(request: dict | None) -> dict | None:
        """住戶讀自己的案件：聯絡資訊是他本人填的，直接還原成明文。"""
        if not request or not isinstance(request.get("form_data"), dict):
            return request
        return dict(request) | {
            "form_data": contact_privacy.decrypt_form_data(request["form_data"])
        }

    def save_request(self, actor_id: str, request: dict) -> None:
        self._stamp_request(actor_id, request)
        stored = self._for_storage(request)
        self.put_item(stored)
        self._save_vendor_index(actor_id, stored)

    def save_request_if_version(self, actor_id: str, request: dict, expected_version: int) -> bool:
        """樂觀鎖版本的 save_request；案件已被其他人改過時回 False，不覆寫。"""
        self._stamp_request(actor_id, request)
        stored = self._for_storage(request)
        if not self.put_item_if_version(stored, expected_version):
            return False
        self._save_vendor_index(actor_id, stored)
        return True

    def get_request(self, actor_id: str, request_id: str) -> dict | None:
        return self._decrypted(self.get_stored_request(actor_id, request_id))

    def get_stored_request(self, actor_id: str, request_id: str) -> dict | None:
        """原封不動的案件（聯絡欄位仍是密文）。

        廠商後台走這條：它要的是狀態與版本，聯絡資訊只給遮罩值，真的要看得另外走
        會留下存取紀錄的解密端點。
        """
        return self.get_item(f"USER#{actor_id}", f"REQUEST#{request_id}")

    def list_requests(self, actor_id: str) -> list[dict]:
        items = self.query_prefix(f"USER#{actor_id}", "REQUEST#")
        ordered = sorted(items, key=lambda x: x.get("created_at", ""), reverse=True)
        return [self._decrypted(item) for item in ordered]

    # ---- Vendor view: requests mirrored under a vendor partition key ----
    def _save_vendor_index(self, actor_id: str, request: dict) -> None:
        """把案件鏡射一份到 VENDOR# 分區，讓廠商後台能一次查出自家案件。

        單表沒有 GSI，廠商清單只能靠這份副本查詢。save_request 是所有狀態變更的
        必經之路，因此兩份項目一定同步；索引寫入失敗不影響住戶端的案件本體。
        """
        vendor_id = vendor_id_of(request)
        if vendor_id is None:
            return
        try:
            self.put_item(
                {
                    "PK": f"VENDOR#{vendor_id}",
                    "SK": f"REQUEST#{request['request_id']}",
                    "entity_type": "VENDOR_REQUEST_INDEX",
                    "vendor_id": vendor_id,
                    "owner_id": actor_id,
                    "request_id": request["request_id"],
                    "service_id": request.get("service_id", ""),
                    "service_name": request.get("service_name", ""),
                    "status": request.get("status", ""),
                    # 廠商後台改狀態時要帶回這個版本，因此索引也要跟著鏡射。
                    "version": version_of(request),
                    # 密文與遮罩一起鏡射；廠商清單只讀 form_data_masked。
                    "form_data": request.get("form_data", {}),
                    "form_data_masked": request.get("form_data_masked", {}),
                    "estimated_fee_min": request.get("estimated_fee_min"),
                    "estimated_fee_max": request.get("estimated_fee_max"),
                    "created_at": request.get("created_at", ""),
                    "updated_at": request["updated_at"],
                }
            )
        except Exception:  # noqa: BLE001 - 住戶送單不該因為廠商索引寫入失敗而失敗
            pass

    def list_vendor_requests(self, vendor_id: int) -> list[dict]:
        items = self.query_prefix(f"VENDOR#{vendor_id}", "REQUEST#")
        return sorted(items, key=lambda x: x.get("created_at", ""), reverse=True)

    def get_vendor_request(self, vendor_id: int, request_id: str) -> dict | None:
        return self.get_item(f"VENDOR#{vendor_id}", f"REQUEST#{request_id}")

    # ---- 聯絡資訊存取軌跡（Milestone 15）----
    def log_contact_access(self, request_id: str, entry: dict) -> dict:
        """記一筆「誰在什麼時候解密了哪些欄位」。

        寫在案件自己的 `REQUEST#{id}` 分區而不是廠商分區：紀錄是為了讓住戶與稽核
        能追一張單被誰看過，跟著案件走才查得到完整的一串。SK 用時間戳排序，尾巴
        補亂數避免同一秒的兩次存取互相覆蓋。
        """
        record = dict(entry) | {
            "PK": f"REQUEST#{request_id}",
            "SK": f"ACCESS#{now_iso()}#{uuid.uuid4().hex[:6]}",
            "entity_type": "CONTACT_ACCESS_LOG",
            "request_id": request_id,
            "at": entry.get("at") or now_iso(),
        }
        self.put_item(record)
        return record

    def list_contact_access(self, request_id: str, vendor_id: int | None = None) -> list[dict]:
        """存取紀錄，新的在前；帶 vendor_id 就只回那家廠商自己的紀錄。"""
        items = self.query_prefix(f"REQUEST#{request_id}", "ACCESS#")
        if vendor_id is not None:
            items = [i for i in items if int(i.get("vendor_id") or 0) == vendor_id]
        return sorted(items, key=lambda x: x.get("at", ""), reverse=True)

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

    def get_sku_stock(self, sku_id: str) -> int:
        item = self.get_item(f"SHOP_SKU#{sku_id}", "STOCK")
        return int(item["quantity"]) if item else 0

    def restock_sku(self, sku_id: str, quantity: int) -> None:
        # Non-atomic read-modify-write, same shape as get_preferences/save_preferences.
        # Acceptable here per the shop-purchase design doc's known limitations: restock
        # only happens on order cancellation, a low-frequency path, not the hot add-to-cart path.
        current = self.get_sku_stock(sku_id)
        self.put_item(
            {
                "PK": f"SHOP_SKU#{sku_id}",
                "SK": "STOCK",
                "entity_type": "SHOP_SKU_STOCK",
                "quantity": current + quantity,
                "updated_at": now_iso(),
            }
        )

    def get_user_points(self, actor_id: str) -> int:
        item = self.get_item(f"USER#{actor_id}", "POINTS")
        return int(item["balance"]) if item else 0

    def deduct_user_points(self, actor_id: str, amount: int) -> bool:
        if amount <= 0:
            return False
        balance = self.get_user_points(actor_id)
        if balance < amount:
            return False
        self.put_item(
            {
                "PK": f"USER#{actor_id}",
                "SK": "POINTS",
                "entity_type": "POINTS",
                "balance": balance - amount,
                "updated_at": now_iso(),
            }
        )
        return True

    def refund_user_points(self, actor_id: str, amount: int) -> None:
        balance = self.get_user_points(actor_id)
        self.put_item(
            {
                "PK": f"USER#{actor_id}",
                "SK": "POINTS",
                "entity_type": "POINTS",
                "balance": balance + amount,
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

    # ---- Onboarding: first-run guide completion flag (M13) ----
    def get_onboarding_status(self, actor_id: str) -> dict:
        item = self.get_item(f"USER#{actor_id}", "ONBOARDING")
        if not item:
            return {"completed": False, "version": 0}
        return {
            "completed": bool(item.get("completed", False)),
            "version": int(item.get("version") or 0),
        }

    def save_onboarding_status(self, actor_id: str, completed: bool, version: int) -> None:
        self.put_item(
            {
                "PK": f"USER#{actor_id}",
                "SK": "ONBOARDING",
                "entity_type": "ONBOARDING_STATUS",
                "completed": completed,
                "version": version,
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

    def put_item_if_version(self, item: dict, expected_version: int) -> bool:
        key = (item["PK"], item["SK"])
        with self._lock:
            current = self._items.get(key)
            if current is None or version_of(current) != expected_version:
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

    def decrement_sku_stock(self, sku_id: str, quantity: int) -> bool:
        key = (f"SHOP_SKU#{sku_id}", "STOCK")
        with self._lock:
            item = self._items.get(key)
            current = int(item["quantity"]) if item else 0
            if current < quantity:
                return False
            self._items[key] = {
                "PK": f"SHOP_SKU#{sku_id}",
                "SK": "STOCK",
                "entity_type": "SHOP_SKU_STOCK",
                "quantity": current - quantity,
                "updated_at": now_iso(),
            }
            self._flush()
            return True

    def query_prefix(self, pk: str, sk_prefix: str) -> list[dict]:
        with self._lock:
            return [dict(v) for (p, s), v in self._items.items() if p == pk and s.startswith(sk_prefix)]

    def scan_by_entity_type(self, entity_type: str) -> list[dict]:
        with self._lock:
            return [dict(v) for v in self._items.values() if v.get("entity_type") == entity_type]

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
        self._table.put_item(Item=convert_floats_to_decimal(item))

    def put_item_if_absent(self, item: dict) -> bool:
        from botocore.exceptions import ClientError

        try:
            self._table.put_item(
                Item=convert_floats_to_decimal(item),
                ConditionExpression="attribute_not_exists(PK) AND attribute_not_exists(SK)",
            )
            return True
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
                return False
            raise

    def put_item_if_version(self, item: dict, expected_version: int) -> bool:
        from botocore.exceptions import ClientError

        # version 0 代表「還沒有版本欄位的舊案件」，也要視為符合預期。
        condition = (
            "attribute_exists(PK) AND (attribute_not_exists(version) OR version = :expected)"
            if expected_version == 0
            else "version = :expected"
        )
        try:
            self._table.put_item(
                Item=convert_floats_to_decimal(item),
                ConditionExpression=condition,
                ExpressionAttributeValues={":expected": expected_version},
            )
            return True
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
                return False
            raise

    def decrement_sku_stock(self, sku_id: str, quantity: int) -> bool:
        from botocore.exceptions import ClientError

        try:
            self._table.update_item(
                Key={"PK": f"SHOP_SKU#{sku_id}", "SK": "STOCK"},
                UpdateExpression="SET quantity = quantity - :qty, updated_at = :now",
                ConditionExpression="quantity >= :qty",
                ExpressionAttributeValues={":qty": quantity, ":now": now_iso()},
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

    def scan_by_entity_type(self, entity_type: str) -> list[dict]:
        from boto3.dynamodb.conditions import Attr

        items: list[dict] = []
        start_key = None
        while True:
            kwargs = {"FilterExpression": Attr("entity_type").eq(entity_type)}
            if start_key:
                kwargs["ExclusiveStartKey"] = start_key
            response = self._table.scan(**kwargs)
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

    def put_item_if_version(self, item: dict, expected_version: int) -> bool:
        # 版本比對同樣以 primary 為準；primary 掛掉時只能退回本地副本，這時的
        # 樂觀鎖只擋得住本行程看得到的併發，屬於降級行為。
        if self._primary_available():
            try:
                if not self._primary.put_item_if_version(item, expected_version):
                    return False
                self._fallback.put_item(dict(item))
                return True
            except Exception:
                self._mark_primary_unavailable()
        local = self._fallback.get_item(item["PK"], item["SK"])
        if local is None:
            # 本地副本沒有這筆（案件是從 DynamoDB 讀出來的），沒有版本可比對。
            self._fallback.put_item(dict(item))
            return True
        return self._fallback.put_item_if_version(dict(item), expected_version)

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

    def scan_by_entity_type(self, entity_type: str) -> list[dict]:
        fallback_items = self._fallback.scan_by_entity_type(entity_type)
        if fallback_items:
            return fallback_items
        if not self._primary_available():
            return []
        try:
            return self._primary.scan_by_entity_type(entity_type)
        except Exception:
            self._mark_primary_unavailable()
            return []


def build_store() -> BaseStore:
    settings = get_settings()
    if settings.use_mock:
        return MemoryStore(storage_path=settings.mock_store_path)
    return DynamoDBStore(settings.dynamodb_table_name)


STORE = build_store()
