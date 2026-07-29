"""Seed the `restaurant_reservation` service catalog entry into DynamoDB.

The deployed MCP Gateway Lambdas (`list_services` / `get_service_schema`)
read the service catalog from DynamoDB first (`SERVICE#<id>` items) and
only fall back to their own hardcoded list when DynamoDB has none. Run
this once so the reservation feature shows up for the real AWS/MCP tool
mode without needing a Lambda redeploy for future catalog edits.

Usage (from the project root, with a working .env):
    backend\\.venv\\Scripts\\python.exe backend\\scripts\\seed_restaurant_reservation_catalog.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.app.config import get_settings
from backend.app.services.aws import get_aws_resource

SCHEMA = {
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
    ],
}


def main() -> None:
    settings = get_settings()
    table = get_aws_resource("dynamodb").Table(settings.dynamodb_table_name)

    item = {
        "PK": "SERVICE#restaurant_reservation",
        "SK": "METADATA",
        "entity_type": "SERVICE",
        "enabled": True,
        "name": "餐廳訂位",
        "description": "22世紀風味館 精選餐廳訂位服務",
        "schema": SCHEMA,
    }

    table.put_item(Item=item)
    print(f"Seeded SERVICE#restaurant_reservation into table '{settings.dynamodb_table_name}'.")

    # Read back to confirm.
    check = table.get_item(Key={"PK": "SERVICE#restaurant_reservation", "SK": "METADATA"}).get("Item")
    if check:
        print("Verified: item is readable back from DynamoDB.")
        print(f"  name = {check['name']}")
        print(f"  fields = {[f['id'] for f in check['schema']['fields']]}")
    else:
        print("WARNING: put_item succeeded but the item could not be read back.")


if __name__ == "__main__":
    main()
