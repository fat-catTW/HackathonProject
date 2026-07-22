"""Conversation memory backends: local store or AgentCore Memory."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from functools import lru_cache

from botocore.exceptions import ClientError

from ..config import get_settings
from .aws import get_aws_client
from .store import STORE, now_iso


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class BaseConversationMemory:
    backend_name = "base"

    def create_session(self, actor_id: str, session_id: str, state: dict) -> dict:
        raise NotImplementedError

    def get_session(self, actor_id: str, session_id: str) -> dict | None:
        raise NotImplementedError

    def save_turn(self, actor_id: str, session_id: str, user_message: str, assistant_message: str, state: dict) -> None:
        raise NotImplementedError

    def save_state(self, actor_id: str, session_id: str, state: dict) -> None:
        raise NotImplementedError

    def get_preferences(self, actor_id: str) -> dict:
        return {}

    def save_preferences(self, actor_id: str, prefs: dict) -> None:
        return None

    def save_long_term_summary(self, actor_id: str, memory: dict) -> None:
        return None

    def get_long_term_context(self, actor_id: str, query: str) -> str:
        return "None"

    def get_memory_snapshot(self, actor_id: str) -> dict:
        return {"preferences": {}, "long_term_memory": {}}


class LocalConversationMemory(BaseConversationMemory):
    backend_name = "local-store"

    def create_session(self, actor_id: str, session_id: str, state: dict) -> dict:
        session = {
            "session_id": session_id,
            "entity_type": "SESSION",
            "state": state,
            "events": [],
            "created_at": now_iso(),
        }
        STORE.save_session(actor_id, session)
        return session

    def get_session(self, actor_id: str, session_id: str) -> dict | None:
        return STORE.get_session(actor_id, session_id)

    def save_turn(self, actor_id: str, session_id: str, user_message: str, assistant_message: str, state: dict) -> None:
        session = STORE.get_session(actor_id, session_id)
        if not session:
            return
        session["events"].append({"role": "USER", "content": user_message})
        session["events"].append({"role": "ASSISTANT", "content": assistant_message})
        session["state"] = state
        STORE.save_session(actor_id, session)

    def save_state(self, actor_id: str, session_id: str, state: dict) -> None:
        session = STORE.get_session(actor_id, session_id)
        if not session:
            return
        session["state"] = state
        STORE.save_session(actor_id, session)

    def get_preferences(self, actor_id: str) -> dict:
        return STORE.get_preferences(actor_id)

    def save_preferences(self, actor_id: str, prefs: dict) -> None:
        STORE.save_preferences(actor_id, prefs)

    def save_long_term_summary(self, actor_id: str, memory: dict) -> None:
        STORE.save_long_term_memory(actor_id, memory)

    def get_long_term_context(self, actor_id: str, query: str) -> str:
        prefs = STORE.get_preferences(actor_id)
        memory = STORE.get_long_term_memory(actor_id)
        lines: list[str] = []
        if prefs.get("last_address"):
            lines.append(f"常用地址: {prefs['last_address']}")
        if prefs.get("last_phone"):
            lines.append(f"常用電話: {prefs['last_phone']}")
        if prefs.get("preferred_time_slot"):
            lines.append(f"偏好時段: {prefs['preferred_time_slot']}")
        if memory.get("last_service_name"):
            lines.append(f"最近服務: {memory['last_service_name']}")
        if memory.get("last_request_summary"):
            lines.append(f"上次摘要: {memory['last_request_summary']}")
        if memory.get("service_counts"):
            lines.append(f"歷史次數: {memory['service_counts']}")
        return "\n".join(lines) if lines else "None"

    def get_memory_snapshot(self, actor_id: str) -> dict:
        return {
            "preferences": STORE.get_preferences(actor_id),
            "long_term_memory": STORE.get_long_term_memory(actor_id),
        }


class AgentCoreConversationMemory(BaseConversationMemory):
    backend_name = "agentcore"
    PROFILE_SESSION_ID = "agent-profile"

    def __init__(self, memory_id: str) -> None:
        self.memory_id = memory_id
        self.data_client = get_aws_client("bedrock-agentcore")
        self.control_client = get_aws_client("bedrock-agentcore-control")

    def create_session(self, actor_id: str, session_id: str, state: dict) -> dict:
        created_at = now_iso()
        self._write_state_snapshot(actor_id, session_id, state, created_at)
        return {
            "session_id": session_id,
            "state": state,
            "events": [],
            "created_at": created_at,
        }

    def get_session(self, actor_id: str, session_id: str) -> dict | None:
        try:
            paginator = self.data_client.get_paginator("list_events")
            pages = paginator.paginate(
                memoryId=self.memory_id,
                actorId=actor_id,
                sessionId=session_id,
                includePayloads=True,
                PaginationConfig={"PageSize": 50},
            )
        except ClientError:
            return None

        collected_events: list[dict] = []
        state = None
        created_at = None
        for page in pages:
            for event in sorted(page.get("events", []), key=lambda item: item.get("eventTimestamp") or _utcnow()):
                if created_at is None and event.get("eventTimestamp"):
                    created_at = event["eventTimestamp"].astimezone(timezone.utc).isoformat()
                for payload in event.get("payload", []):
                    if "conversational" in payload:
                        message = payload["conversational"]
                        text = (((message.get("content") or {}).get("text")) or "").strip()
                        role = message.get("role", "OTHER")
                        if text:
                            collected_events.append({"role": role, "content": text})
                    elif "blob" in payload:
                        blob = payload["blob"]
                        if isinstance(blob, str):
                            try:
                                blob = json.loads(blob)
                            except json.JSONDecodeError:
                                continue
                        if isinstance(blob, dict) and blob.get("kind") == "state_snapshot":
                            state = blob.get("state", state)
                            created_at = blob.get("created_at", created_at)

        if state is None:
            return None
        return {
            "session_id": session_id,
            "state": state,
            "events": collected_events,
            "created_at": created_at or now_iso(),
        }

    def save_turn(self, actor_id: str, session_id: str, user_message: str, assistant_message: str, state: dict) -> None:
        self._create_conversational_event(actor_id, session_id, "USER", user_message)
        self._create_conversational_event(actor_id, session_id, "ASSISTANT", assistant_message)
        self._write_state_snapshot(actor_id, session_id, state)

    def save_state(self, actor_id: str, session_id: str, state: dict) -> None:
        self._write_state_snapshot(actor_id, session_id, state)

    def get_preferences(self, actor_id: str) -> dict:
        return self._load_profile_snapshot(actor_id).get("preferences", {})

    def save_preferences(self, actor_id: str, prefs: dict) -> None:
        profile = self._load_profile_snapshot(actor_id)
        merged = (profile.get("preferences") or {}) | prefs
        self._save_profile_snapshot(
            actor_id,
            preferences=merged,
            long_term_memory=profile.get("long_term_memory") or {},
        )

    def save_long_term_summary(self, actor_id: str, memory: dict) -> None:
        profile = self._load_profile_snapshot(actor_id)
        merged = (profile.get("long_term_memory") or {}) | memory
        self._save_profile_snapshot(
            actor_id,
            preferences=profile.get("preferences") or {},
            long_term_memory=merged,
        )

    def get_memory_snapshot(self, actor_id: str) -> dict:
        profile = self._load_profile_snapshot(actor_id)
        return {
            "preferences": profile.get("preferences") or {},
            "long_term_memory": profile.get("long_term_memory") or {},
        }

    def get_long_term_context(self, actor_id: str, query: str) -> str:
        lines: list[str] = []
        profile = self._load_profile_snapshot(actor_id)
        prefs = profile.get("preferences") or {}
        memory = profile.get("long_term_memory") or {}
        if prefs.get("last_address"):
            lines.append(f"最近地址: {prefs['last_address']}")
        if prefs.get("last_phone"):
            lines.append(f"最近電話: {prefs['last_phone']}")
        if prefs.get("preferred_time_slot"):
            lines.append(f"偏好時段: {prefs['preferred_time_slot']}")
        if memory.get("last_service_name"):
            lines.append(f"最近服務: {memory['last_service_name']}")
        if memory.get("last_request_summary"):
            lines.append(f"上次摘要: {memory['last_request_summary']}")

        for namespace_path in self._namespace_paths(actor_id):
            try:
                response = self.data_client.retrieve_memory_records(
                    memoryId=self.memory_id,
                    namespacePath=namespace_path,
                    searchCriteria={"searchQuery": query, "topK": 3},
                    maxResults=3,
                )
            except ClientError:
                continue
            for summary in response.get("memoryRecordSummaries", []):
                content = summary.get("content")
                if isinstance(content, dict):
                    text = (content.get("text") or "").strip()
                    if text:
                        lines.append(text)
                        continue
                record_id = summary.get("memoryRecordId")
                if record_id:
                    try:
                        record = self.data_client.get_memory_record(memoryId=self.memory_id, memoryRecordId=record_id).get("memoryRecord", {})
                        text = (((record.get("content") or {}).get("text")) or "").strip()
                        if text:
                            lines.append(text)
                    except ClientError:
                        continue
        if not lines:
            return "None"
        # Keep the prompt compact and deterministic.
        unique_lines = []
        for line in lines:
            if line not in unique_lines:
                unique_lines.append(line)
        return "\n".join(unique_lines[:6])

    def _load_profile_snapshot(self, actor_id: str) -> dict:
        try:
            paginator = self.data_client.get_paginator("list_events")
            pages = paginator.paginate(
                memoryId=self.memory_id,
                actorId=actor_id,
                sessionId=self.PROFILE_SESSION_ID,
                includePayloads=True,
                PaginationConfig={"PageSize": 50},
            )
        except ClientError:
            return {"preferences": {}, "long_term_memory": {}}

        snapshot = {"preferences": {}, "long_term_memory": {}}
        for page in pages:
            events = sorted(page.get("events", []), key=lambda item: item.get("eventTimestamp") or _utcnow())
            for event in events:
                for payload in event.get("payload", []):
                    blob = payload.get("blob")
                    if not blob:
                        continue
                    if isinstance(blob, str):
                        try:
                            blob = json.loads(blob)
                        except json.JSONDecodeError:
                            continue
                    if isinstance(blob, dict) and blob.get("kind") == "profile_snapshot":
                        snapshot = {
                            "preferences": blob.get("preferences") or {},
                            "long_term_memory": blob.get("long_term_memory") or {},
                        }
        return snapshot

    def _save_profile_snapshot(self, actor_id: str, *, preferences: dict, long_term_memory: dict) -> None:
        self.data_client.create_event(
            memoryId=self.memory_id,
            actorId=actor_id,
            sessionId=self.PROFILE_SESSION_ID,
            eventTimestamp=_utcnow(),
            extractionMode="SKIP",
            metadata={"event_type": {"stringValue": "PROFILE_SNAPSHOT"}},
            payload=[
                {
                    "blob": json.dumps(
                        {
                            "kind": "profile_snapshot",
                            "created_at": now_iso(),
                            "preferences": preferences,
                            "long_term_memory": long_term_memory,
                        },
                        ensure_ascii=False,
                    )
                }
            ],
        )

    def _create_conversational_event(self, actor_id: str, session_id: str, role: str, text: str) -> None:
        self.data_client.create_event(
            memoryId=self.memory_id,
            actorId=actor_id,
            sessionId=session_id,
            eventTimestamp=_utcnow(),
            payload=[
                {
                    "conversational": {
                        "content": {"text": text},
                        "role": role,
                    }
                }
            ],
        )

    def _write_state_snapshot(self, actor_id: str, session_id: str, state: dict, created_at: str | None = None) -> None:
        self.data_client.create_event(
            memoryId=self.memory_id,
            actorId=actor_id,
            sessionId=session_id,
            eventTimestamp=_utcnow(),
            extractionMode="SKIP",
            metadata={"event_type": {"stringValue": "STATE_SNAPSHOT"}},
            payload=[
                {
                    "blob": json.dumps(
                        {
                            "kind": "state_snapshot",
                            "created_at": created_at or now_iso(),
                            "state": state,
                        },
                        ensure_ascii=False,
                    )
                }
            ],
        )

    @lru_cache
    def _strategy_ids(self) -> tuple[str, ...]:
        try:
            memory = self.control_client.get_memory(memoryId=self.memory_id, view="without_decryption").get("memory", {})
        except Exception:
            return ()
        ids: list[str] = []
        for strategy in memory.get("memoryStrategies", []):
            strategy_id = strategy.get("strategyId")
            if strategy_id:
                ids.append(strategy_id)
        return tuple(ids)

    def _namespace_paths(self, actor_id: str) -> list[str]:
        return [f"/strategy/{strategy_id}/actors/{actor_id}/" for strategy_id in self._strategy_ids()]


def build_conversation_memory() -> BaseConversationMemory:
    settings = get_settings()
    if settings.use_agentcore_memory:
        return AgentCoreConversationMemory(settings.agentcore_memory_id)
    return LocalConversationMemory()


MEMORY = build_conversation_memory()
