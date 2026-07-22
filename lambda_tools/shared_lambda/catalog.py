"""Shared service catalog and DynamoDB helpers for Lambda tool handlers."""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone

import boto3
from boto3.dynamodb.conditions import Attr

TABLE_NAME = os.environ.get("DYNAMODB_TABLE_NAME", "ServiceAssistant")
CATALOG_FALLBACK = os.environ.get("SERVICE_CATALOG_FALLBACK", "true").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
TZ = timezone(timedelta(hours=8))

FALLBACK_SERVICES: list[dict] = [
    {
        "id": "plumbing_repair",
        "name": "水電修繕",
        "description": "處理漏水、堵塞、馬桶、水管、插座與燈具等居家修繕問題。",
        "schema": {
            "fields": [
                {"id": "issue_description", "label": "問題描述", "type": "text", "required": True},
                {"id": "preferred_date", "label": "希望日期", "type": "date", "required": True},
                {
                    "id": "preferred_time_slot",
                    "label": "希望時段",
                    "type": "select",
                    "required": True,
                    "options": ["MORNING", "AFTERNOON", "EVENING"],
                },
                {"id": "address", "label": "服務地址", "type": "text", "required": True},
                {"id": "phone", "label": "聯絡電話", "type": "text", "required": True},
            ]
        },
    },
    {
        "id": "washing_machine_cleaning",
        "name": "洗衣機清洗",
        "description": "提供洗衣機拆洗與深度清潔服務。",
        "schema": {
            "fields": [
                {"id": "quantity", "label": "數量", "type": "number", "required": True},
                {
                    "id": "machine_type",
                    "label": "洗衣機類型",
                    "type": "select",
                    "required": True,
                    "options": ["TOP_LOAD", "FRONT_LOAD"],
                },
                {"id": "preferred_date", "label": "希望日期", "type": "date", "required": True},
                {
                    "id": "preferred_time_slot",
                    "label": "希望時段",
                    "type": "select",
                    "required": True,
                    "options": ["MORNING", "AFTERNOON", "EVENING"],
                },
                {"id": "address", "label": "服務地址", "type": "text", "required": True},
                {"id": "phone", "label": "聯絡電話", "type": "text", "required": True},
            ]
        },
    },
    {
        "id": "air_conditioner_cleaning",
        "name": "冷氣清洗",
        "description": "提供分離式與窗型冷氣清潔保養服務。",
        "schema": {
            "fields": [
                {"id": "quantity", "label": "數量", "type": "number", "required": True},
                {"id": "preferred_date", "label": "希望日期", "type": "date", "required": True},
                {
                    "id": "preferred_time_slot",
                    "label": "希望時段",
                    "type": "select",
                    "required": True,
                    "options": ["MORNING", "AFTERNOON", "EVENING"],
                },
                {"id": "address", "label": "服務地址", "type": "text", "required": True},
                {"id": "phone", "label": "聯絡電話", "type": "text", "required": True},
            ]
        },
    },
    {
        "id": "home_cleaning",
        "name": "居家清潔",
        "description": "提供居家打掃與鐘點清潔服務。",
        "schema": {
            "fields": [
                {"id": "hours", "label": "服務時數", "type": "number", "required": True},
                {"id": "preferred_date", "label": "希望日期", "type": "date", "required": True},
                {
                    "id": "preferred_time_slot",
                    "label": "希望時段",
                    "type": "select",
                    "required": True,
                    "options": ["MORNING", "AFTERNOON", "EVENING"],
                },
                {"id": "address", "label": "服務地址", "type": "text", "required": True},
                {"id": "phone", "label": "聯絡電話", "type": "text", "required": True},
            ]
        },
    },
]


def dynamodb_table():
    return boto3.resource("dynamodb").Table(TABLE_NAME)


def now_iso() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def next_request_id() -> str:
    return f"REQ-{datetime.now(TZ):%Y%m%d}-{uuid.uuid4().hex[:6].upper()}"


def fallback_services() -> list[dict]:
    return [dict(service) for service in FALLBACK_SERVICES]


def fallback_service(service_id: str) -> dict | None:
    return next((service for service in FALLBACK_SERVICES if service["id"] == service_id), None)


def scan_catalog_from_dynamodb() -> list[dict]:
    table = dynamodb_table()
    items: list[dict] = []
    start_key = None
    while True:
        kwargs = {
            "FilterExpression": Attr("entity_type").eq("SERVICE") & Attr("enabled").eq(True),
        }
        if start_key:
            kwargs["ExclusiveStartKey"] = start_key
        response = table.scan(**kwargs)
        items.extend(response.get("Items", []))
        start_key = response.get("LastEvaluatedKey")
        if not start_key:
            return items


def load_services() -> list[dict]:
    try:
        items = scan_catalog_from_dynamodb()
        if items:
            return [
                {
                    "id": item["PK"].split("#", 1)[1],
                    "name": item["name"],
                    "description": item.get("description", ""),
                    "schema": item["schema"],
                }
                for item in items
            ]
    except Exception:
        if not CATALOG_FALLBACK:
            raise
    if CATALOG_FALLBACK:
        return fallback_services()
    return []


def load_service(service_id: str) -> dict | None:
    try:
        table = dynamodb_table()
        item = table.get_item(Key={"PK": f"SERVICE#{service_id}", "SK": "METADATA"}).get("Item")
        if item and item.get("enabled"):
            return {
                "id": service_id,
                "name": item["name"],
                "description": item.get("description", ""),
                "schema": item["schema"],
            }
    except Exception:
        if not CATALOG_FALLBACK:
            raise
    return fallback_service(service_id) if CATALOG_FALLBACK else None


def validate_required_fields(fields: list[dict], payload: dict) -> list[str]:
    required = [field["id"] for field in fields if field.get("required")]
    return [field_id for field_id in required if payload.get(field_id) in (None, "")]
