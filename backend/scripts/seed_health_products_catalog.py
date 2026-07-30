"""Seed the health product recommendation catalog into DynamoDB.

health_catalog.list_products()/get_product() read from DynamoDB first
(PK=PRODUCT#<id>, SK=METADATA, entity_type=PRODUCT) and only fall back to
the hardcoded PRODUCTS list when DynamoDB has none yet — same convention as
seed_restaurant_reservation_catalog.py / seed_food_delivery_catalog.py for
the SERVICE#<id> catalog. Also seeds the health_product_recommendation
SERVICE# entry itself so it shows up for the real AWS/MCP tool mode.

Usage (from the project root, with a working .env):
    backend\\.venv\\Scripts\\python.exe backend\\scripts\\seed_health_products_catalog.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.app.config import get_settings
from backend.app.services.aws import get_aws_resource
from backend.app.services.health_catalog import PRODUCTS

SERVICE_SCHEMA = {
    "fields": [
        {
            "id": "query",
            "label": "健康或飲食需求",
            "type": "textarea",
            "required": True,
            "question": "請問想解決什麼健康或飲食需求呢？例如：我在減脂但想吃點甜食。",
        },
    ],
}


def main() -> None:
    settings = get_settings()
    table = get_aws_resource("dynamodb").Table(settings.dynamodb_table_name)

    for product in PRODUCTS:
        item = {
            "PK": f"PRODUCT#{product['id']}",
            "SK": "METADATA",
            "entity_type": "PRODUCT",
            **product,
        }
        table.put_item(Item=item)
    print(f"Seeded {len(PRODUCTS)} PRODUCT# items into table '{settings.dynamodb_table_name}'.")

    service_item = {
        "PK": "SERVICE#health_product_recommendation",
        "SK": "METADATA",
        "entity_type": "SERVICE",
        "enabled": True,
        "name": "健康商品推薦",
        "description": "說出健康或飲食需求，推薦適合的 7-11 商品",
        "schema": SERVICE_SCHEMA,
    }
    table.put_item(Item=service_item)
    print(f"Seeded SERVICE#health_product_recommendation into table '{settings.dynamodb_table_name}'.")

    check = table.get_item(Key={"PK": "PRODUCT#P001", "SK": "METADATA"}).get("Item")
    if check:
        print("Verified: PRODUCT#P001 is readable back from DynamoDB.")
        print(f"  name = {check['name']}")
    else:
        print("WARNING: put_item succeeded but PRODUCT#P001 could not be read back.")


if __name__ == "__main__":
    main()
