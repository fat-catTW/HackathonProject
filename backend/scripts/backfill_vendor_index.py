"""把既有案件回填成廠商後台的 VENDOR# 索引項目。

廠商清單靠 save_request 時鏡射的 VENDOR#{id} 項目查詢（見 services/store.py），
但這份索引是 Milestone 3 才加的，之前建立的案件不會有——除非它們剛好又被改過
狀態。廠商後台上線後、或 catalog.py 的 service_vendor_id 對應改變後，跑一次
這支腳本即可補齊。DynamoDB 與本地 MemoryStore（USE_MOCK=true）都支援。

可重複執行：每次都以案件本體覆寫索引，不會產生重複項目。

    python backend/scripts/backfill_vendor_index.py --dry-run
    python backend/scripts/backfill_vendor_index.py
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services import catalog, store as store_module


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
        "order_status": request.get("order_status"),
        # 廠商後台接單／拒單要帶回版本比對，索引跟著鏡射（舊案件沒有就是 0）。
        "version": int(request.get("version") or 0),
        "form_data": request.get("form_data", {}),
        "created_at": request.get("created_at", ""),
        "updated_at": request.get("updated_at", request.get("created_at", "")),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="只列出要寫入的項目")
    args = parser.parse_args()

    backend = store_module.build_store()
    requests = backend.scan_by_entity_type("SERVICE_REQUEST")
    existing = {
        (str(i.get("PK")), str(i.get("SK")))
        for i in backend.scan_by_entity_type("VENDOR_REQUEST_INDEX")
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
    print(f"（backend={backend.backend_name}）案件 {len(requests)} 筆　可歸屬 {len(to_write)} 筆（其中新建 {len(fresh)} 筆）")
    if skipped:
        print(f"略過 {len(skipped)} 筆：服務目錄查不到 service_vendor_id")
        for request in skipped:
            print(f"  - {request.get('request_id')} {request.get('service_name')}")

    if args.dry_run:
        for item in fresh:
            print(f"  + {item['PK']} {item['SK']} {item['service_name']} {item['status']}")
        return 0

    for item in to_write:
        backend.put_item(item)
    print(f"已寫入 {len(to_write)} 筆索引項目。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
