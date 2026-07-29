"""Shared service catalog and DynamoDB helpers for Lambda tool handlers."""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Attr, Key

TABLE_NAME = os.environ.get("DYNAMODB_TABLE_NAME", "ServiceAssistant")
CATALOG_FALLBACK = os.environ.get("SERVICE_CATALOG_FALLBACK", "true").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
TZ = timezone(timedelta(hours=8))

# --- 餐廳訂位：餐廳目錄（複製自 backend/app/services/restaurant_catalog.py，
#     lambda_tools 跟 backend 是分開打包部署，兩邊各自維護一份，見
#     docs/mcp-gateway-lambda-setup.md） ---
RESTAURANTS: list[dict] = [
    {
        "id": "r001",
        "name": "22世紀風味館 信義旗艦店",
        "brand": "22世紀風味館",
        "address": "台北市信義區松高路12號3樓",
        "phone": "02-2723-0022",
        "cuisine": "複合式料理",
        "supports_booking_api": True,
        "verification_enabled": True,
        "image_url": "/images/restaurants/r001.jpg",
    },
    {
        "id": "r002",
        "name": "22世紀風味館 板橋文化店",
        "brand": "22世紀風味館",
        "address": "新北市板橋區文化路一段280號2樓",
        "phone": "02-2258-0022",
        "cuisine": "複合式料理",
        "supports_booking_api": True,
        "verification_enabled": True,
        "image_url": "/images/restaurants/r002.jpg",
    },
    {
        "id": "r003",
        "name": "22世紀風味館 台中公益店",
        "brand": "22世紀風味館",
        "address": "台中市南屯區公益路二段51號",
        "phone": "04-2326-0022",
        "cuisine": "複合式料理",
        "supports_booking_api": True,
        "verification_enabled": False,
        "image_url": "/images/restaurants/r003.jpg",
    },
    {
        "id": "r004",
        "name": "22世紀風味館 高雄夢時代店",
        "brand": "22世紀風味館",
        "address": "高雄市前鎮區中華五路789號B1",
        "phone": "07-812-0022",
        "cuisine": "複合式料理",
        "supports_booking_api": True,
        "verification_enabled": True,
        "image_url": "/images/restaurants/r004.jpg",
    },
    {
        "id": "r005",
        "name": "22世紀風味館 桃園中正店",
        "brand": "22世紀風味館",
        "address": "桃園市桃園區中正路1055號",
        "phone": "03-356-0022",
        "cuisine": "複合式料理",
        "supports_booking_api": False,
        "verification_enabled": False,
        "image_url": "/images/restaurants/r005.jpg",
    },
    {
        "id": "r006",
        "name": "22世紀風味館 新竹巨城店",
        "brand": "22世紀風味館",
        "address": "新竹市東區中央路229號4樓",
        "phone": "03-623-0022",
        "cuisine": "複合式料理",
        "supports_booking_api": True,
        "verification_enabled": True,
        "image_url": "/images/restaurants/r006.jpg",
    },
]

# --- 美食外送：店家目錄（複製自 backend/app/services/delivery_catalog.py，
#     同樣的分開部署理由） ---
DELIVERY_STORES: list[dict] = [
    {
        "id": "store-001",
        "name": "好味道便當",
        "address": "台北市大安區忠孝東路四段100號",
        "cuisine": "便當",
        "url": "",
        "menu": [
            {"id": "item-001", "title": "招牌雞腿便當", "price": 110},
            {"id": "item-002", "title": "排骨便當", "price": 100},
            {"id": "item-003", "title": "素食便當", "price": 90},
        ],
    },
    {
        "id": "store-002",
        "name": "鮮茶道",
        "address": "台北市信義區松仁路28號",
        "cuisine": "飲料",
        "url": "",
        "menu": [
            {"id": "item-010", "title": "珍珠奶茶（大）", "price": 65},
            {"id": "item-011", "title": "四季春茶（大）", "price": 40},
            {"id": "item-012", "title": "冬瓜檸檬", "price": 55},
        ],
    },
    {
        "id": "store-003",
        "name": "義式小館",
        "address": "台北市中山區南京東路二段50號",
        "cuisine": "義式料理",
        "url": "",
        "menu": [
            {"id": "item-020", "title": "奶油培根義大利麵", "price": 180},
            {"id": "item-021", "title": "瑪格麗特披薩", "price": 220},
            {"id": "item-022", "title": "凱薩沙拉", "price": 120},
        ],
    },
]


def get_restaurant(restaurant_id: str) -> dict | None:
    return next((r for r in RESTAURANTS if r["id"] == restaurant_id), None)


def get_delivery_store(store_id: str) -> dict | None:
    return next((s for s in DELIVERY_STORES if s["id"] == store_id), None)


def convert_floats_to_decimal(value):
    """Recursively convert Python float values to Decimal.

    DynamoDB (via boto3) rejects native float values outright ("Float
    types are not supported. Use Decimal types instead."). Mirrors
    backend/app/services/store.py's helper of the same name — duplicated
    here because lambda_tools is packaged and deployed separately from
    backend (see docs/mcp-gateway-lambda-setup.md).
    """
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, dict):
        return {key: convert_floats_to_decimal(item) for key, item in value.items()}
    if isinstance(value, list):
        return [convert_floats_to_decimal(item) for item in value]
    return value


def query_requests_by_actor(actor_id: str) -> list[dict]:
    """所有屬於這個使用者的 SERVICE_REQUEST item（PK=USER#<actor_id>, SK 前綴 REQUEST#）。"""
    table = dynamodb_table()
    items: list[dict] = []
    start_key = None
    while True:
        kwargs = {
            "KeyConditionExpression": Key("PK").eq(f"USER#{actor_id}") & Key("SK").begins_with("REQUEST#"),
        }
        if start_key:
            kwargs["ExclusiveStartKey"] = start_key
        response = table.query(**kwargs)
        items.extend(response.get("Items", []))
        start_key = response.get("LastEvaluatedKey")
        if not start_key:
            return items


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
    {
        "id": "restaurant_reservation",
        "name": "餐廳訂位",
        "description": "22世紀風味館 精選餐廳訂位服務。",
        "schema": {
            "fields": [
                {
                    "id": "restaurant_id",
                    "label": "餐廳選擇",
                    "type": "select",
                    "required": True,
                    "options": ["r001", "r002", "r003", "r004", "r005", "r006"],
                },
                {"id": "reserved_date", "label": "用餐日期", "type": "date", "required": True},
                {
                    "id": "time_slot",
                    "label": "用餐時段",
                    "type": "select",
                    "required": True,
                    "options": ["LUNCH", "DINNER"],
                },
                {"id": "people", "label": "用餐人數", "type": "number", "required": True},
                {"id": "contact_name", "label": "聯絡人姓名", "type": "text", "required": True},
                {"id": "phone", "label": "聯絡電話", "type": "text", "required": True},
                {
                    "id": "is_premium",
                    "label": "訂位類型",
                    "type": "select",
                    "required": True,
                    "options": ["STANDARD", "PREMIUM"],
                },
            ]
        },
    },
    {
        "id": "food_delivery",
        "name": "美食外送",
        "description": "附近店家美食外送到府服務。",
        "schema": {
            "fields": [
                {"id": "address", "label": "外送地址", "type": "address", "required": True},
                {
                    "id": "store_id",
                    "label": "選擇店家",
                    "type": "select",
                    "required": True,
                    "options": [s["id"] for s in DELIVERY_STORES],
                },
                {"id": "goods", "label": "餐點品項", "type": "cart", "required": True},
                {"id": "contact_name", "label": "收件人姓名", "type": "text", "required": True},
                {"id": "note", "label": "備註需求", "type": "text", "required": False},
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
