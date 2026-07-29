"""把既有案件回填成廠商後台的 VENDOR# 索引項目。

廠商清單靠 save_request 時鏡射的 VENDOR#{id} 項目查詢（見 services/store.py），
但這份索引是 Milestone 3 才加的，之前建立的案件不會有——除非它們剛好又被改過
狀態。廠商後台上線後跑一次這支腳本即可補齊。

可重複執行：每次都以案件本體覆寫索引，不會產生重複項目。

    python backend/scripts/backfill_vendor_index.py --dry-run
    python backend/scripts/backfill_vendor_index.py
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings
from app.services import catalog
from app.services.aws import get_aws_resource


def scan_all(table) -> list[dict]:
    items: list[dict] = []
    kwargs: dict = {}
    while True:
        response = table.scan(**kwargs)
        items.extend(response.get("Items", []))
        start_key = response.get("LastEvaluatedKey")
        if not start_key:
            return items
        kwargs["ExclusiveStartKey"] = start_key


def vendor_id_of(request: dict) -> int | None:
    vendor_id = request.get("service_vendor_id")
    if vendor_id is not None:
        return int(vendor_id)
    return catalog.vendor_id_for_service(str(request.get("service_id", "")))


def index_item(request: dict, vendor_id: int) -> dict:
    # PK 是 USER#{actor_id}，索引要記回案件屬於哪位住戶。
    owner_id = str(request["PK"]).removeprefix("USER#")
    return {
        "PK": f"VENDOR#{vendor_id}",
        "SK": f"REQUEST#{request['request_id']}",
        "entity_type": "VENDOR_REQUEST_INDEX",
        "vendor_id": vendor_id,
        "owner_id": owner_id,
        "request_id": request["request_id"],
        "service_id": request.get("service_id", ""),
        "service_name": request.get("service_name", ""),
        "status": request.get("status", ""),
        "form_data": request.get("form_data", {}),
        "created_at": request.get("created_at", ""),
        "updated_at": request.get("updated_at", request.get("created_at", "")),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="只列出要寫入的項目")
    args = parser.parse_args()

    settings = get_settings()
    if settings.use_mock:
        print("USE_MOCK=true：本地記憶體儲存不需要回填。")
        return 0

    table = get_aws_resource("dynamodb").Table(settings.dynamodb_table_name)
    items = scan_all(table)
    requests = [i for i in items if i.get("entity_type") == "SERVICE_REQUEST"]
    existing = {
        (str(i.get("PK")), str(i.get("SK")))
        for i in items
        if i.get("entity_type") == "VENDOR_REQUEST_INDEX"
    }

    to_write, skipped = [], []
    for request in requests:
        vendor_id = vendor_id_of(request)
        if vendor_id is None:
            # 服務目錄查不到廠商（例如只存在於 MCP Gateway 的服務），沒有東西可歸屬。
            skipped.append(request)
            continue
        to_write.append(index_item(request, vendor_id))

    fresh = [i for i in to_write if (i["PK"], i["SK"]) not in existing]
    print(f"案件 {len(requests)} 筆　可歸屬 {len(to_write)} 筆（其中新建 {len(fresh)} 筆）")
    if skipped:
        print(f"略過 {len(skipped)} 筆：服務目錄查不到 service_vendor_id")
        for request in skipped:
            print(f"  - {request.get('request_id')} {request.get('service_name')}")

    if args.dry_run:
        for item in fresh:
            print(f"  + {item['PK']} {item['SK']} {item['service_name']} {item['status']}")
        return 0

    with table.batch_writer() as batch:
        for item in to_write:
            batch.put_item(Item=item)
    print(f"已寫入 {len(to_write)} 筆索引項目。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
