"""Seed the `food_delivery` service catalog entry into DynamoDB.

The deployed MCP Gateway Lambdas (`list_services` / `get_service_schema`)
read the service catalog from DynamoDB first (`SERVICE#<id>` items) and
only fall back to their own hardcoded list when DynamoDB has none. Run
this once so the delivery feature shows up for the real AWS/MCP tool
mode without needing a Lambda redeploy for future catalog edits.

Usage (from the project root, with a working .env):
    backend\\.venv\\Scripts\\python.exe backend\\scripts\\seed_food_delivery_catalog.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.app.config import get_settings
from backend.app.services.aws import get_aws_resource
from backend.app.services.delivery_catalog import list_stores

SCHEMA = {
    "fields": [
        {"id": "address", "label": "外送地址", "type": "address", "required": True},
        {
            "id": "store_id",
            "label": "選擇店家",
            "type": "select",
            "required": True,
            "options": [store["id"] for store in list_stores()],
        },
        {"id": "goods", "label": "餐點品項", "type": "cart", "required": True},
        {"id": "contact_name", "label": "收件人姓名", "type": "text", "required": True},
        {"id": "note", "label": "備註需求", "type": "text", "required": False},
    ],
}


def main() -> None:
    settings = get_settings()
    table = get_aws_resource("dynamodb").Table(settings.dynamodb_table_name)

    item = {
        "PK": "SERVICE#food_delivery",
        "SK": "METADATA",
        "entity_type": "SERVICE",
        "enabled": True,
        "name": "美食外送",
        "description": "附近店家美食外送到府服務",
        "schema": SCHEMA,
    }

    table.put_item(Item=item)
    print(f"Seeded SERVICE#food_delivery into table '{settings.dynamodb_table_name}'.")

    # Read back to confirm.
    check = table.get_item(Key={"PK": "SERVICE#food_delivery", "SK": "METADATA"}).get("Item")
    if check:
        print("Verified: item is readable back from DynamoDB.")
        print(f"  name = {check['name']}")
        print(f"  fields = {[f['id'] for f in check['schema']['fields']]}")
    else:
        print("WARNING: put_item succeeded but the item could not be read back.")


if __name__ == "__main__":
    main()
