"""Upsert service catalog items into DynamoDB from a local JSON payload."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from app.config import get_settings
from app.services.aws import get_aws_resource

DEFAULT_PAYLOAD = Path(__file__).with_name("dynamodb_service_catalog_payload.json")
REQUIRED_ITEM_KEYS = {"PK", "SK", "entity_type", "enabled", "id", "name", "description", "schema"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--payload",
        type=Path,
        default=DEFAULT_PAYLOAD,
        help=f"Path to the catalog payload JSON. Default: {DEFAULT_PAYLOAD.name}",
    )
    parser.add_argument(
        "--table-name",
        default="",
        help="Override DynamoDB table name. Defaults to DYNAMODB_TABLE_NAME / config value.",
    )
    parser.add_argument(
        "--service-id",
        action="append",
        default=[],
        help="Only update the given service_id. Repeat this flag to update multiple services.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and print the target items without writing to DynamoDB.",
    )
    return parser.parse_args()


def load_payload(path: Path) -> list[dict]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"Payload file was not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Payload file is not valid JSON: {path} ({exc})") from exc

    if not isinstance(data, list):
        raise SystemExit("Payload JSON must be an array of DynamoDB service items.")

    items: list[dict] = []
    for index, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            raise SystemExit(f"Payload item #{index} is not an object.")
        missing = sorted(REQUIRED_ITEM_KEYS - item.keys())
        if missing:
            raise SystemExit(f"Payload item #{index} is missing keys: {', '.join(missing)}")
        schema = item.get("schema")
        if not isinstance(schema, dict) or not isinstance(schema.get("fields"), list):
            raise SystemExit(f"Payload item #{index} has an invalid schema.fields structure.")
        items.append(item)
    return items


def select_items(items: list[dict], service_ids: list[str]) -> list[dict]:
    wanted = {service_id.strip() for service_id in service_ids if service_id.strip()}
    if not wanted:
        return items
    selected = [item for item in items if str(item.get("id")) in wanted]
    missing = sorted(wanted - {str(item.get("id")) for item in selected})
    if missing:
        raise SystemExit(f"Unknown service_id in payload: {', '.join(missing)}")
    return selected


def target_table_name(override: str) -> str:
    if override.strip():
        return override.strip()
    return get_settings().dynamodb_table_name


def print_plan(items: list[dict], table_name: str, dry_run: bool) -> None:
    mode = "DRY RUN" if dry_run else "APPLY"
    print(f"[{mode}] Target table: {table_name}")
    print(f"[{mode}] Service items: {len(items)}")
    for item in items:
        field_count = len(((item.get("schema") or {}).get("fields") or []))
        print(f"- {item['id']}: {item['name']} ({field_count} fields)")


def upsert_items(items: list[dict], table_name: str) -> None:
    table = get_aws_resource("dynamodb").Table(table_name)
    with table.batch_writer(overwrite_by_pkeys=["PK", "SK"]) as batch:
        for item in items:
            batch.put_item(Item=item)


def main() -> None:
    args = parse_args()
    items = select_items(load_payload(args.payload), args.service_id)
    table_name = target_table_name(args.table_name)

    if not items:
        raise SystemExit("No service items selected for update.")

    print_plan(items, table_name, args.dry_run)
    if args.dry_run:
        return

    upsert_items(items, table_name)
    print(f"[DONE] Upserted {len(items)} service catalog items into {table_name}.")


if __name__ == "__main__":
    main()
