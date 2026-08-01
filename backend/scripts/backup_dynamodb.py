"""備份 DynamoDB 資料表所有項目到本機 JSON 檔案。

用法（在 backend 目錄下執行，會自動讀取 backend/.env 或專案根目錄 .env）：

    python scripts/backup_dynamodb.py
    python scripts/backup_dynamodb.py --table ServiceAssistant --out "C:/Users/user/Desktop/dynamodb_backup.json"

備份檔案是 JSON 陣列，每個元素是一筆 DynamoDB item（已轉換為一般 Python
型別，Decimal 會轉成 int/float）。之後若要還原，可以搭配
scripts/restore_dynamodb.py（同目錄）將資料寫回同一張表或新表。
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND_ROOT))

from app.config import get_settings  # noqa: E402
from app.services.aws import get_aws_resource  # noqa: E402


def _decimal_to_native(value):
    """把 boto3 回傳的 Decimal 轉成 int（整數）或 float（小數）。"""
    if isinstance(value, list):
        return [_decimal_to_native(v) for v in value]
    if isinstance(value, dict):
        return {k: _decimal_to_native(v) for k, v in value.items()}
    if isinstance(value, Decimal):
        if value % 1 == 0:
            return int(value)
        return float(value)
    return value


def scan_all_items(table) -> list[dict]:
    items: list[dict] = []
    scan_kwargs: dict = {}
    while True:
        response = table.scan(**scan_kwargs)
        items.extend(response.get("Items", []))
        start_key = response.get("LastEvaluatedKey")
        if not start_key:
            break
        scan_kwargs["ExclusiveStartKey"] = start_key
    return items


def main() -> None:
    parser = argparse.ArgumentParser(description="備份 DynamoDB 資料表到 JSON 檔案")
    parser.add_argument(
        "--table",
        default=None,
        help="DynamoDB 資料表名稱，預設讀取 .env 的 DYNAMODB_TABLE_NAME",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="輸出檔案路徑，預設輸出到桌面 dynamodb_backup_<table>_<timestamp>.json",
    )
    args = parser.parse_args()

    settings = get_settings()
    table_name = args.table or settings.dynamodb_table_name

    if args.out:
        out_path = Path(args.out)
    else:
        desktop = Path.home() / "Desktop"
        desktop.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = desktop / f"dynamodb_backup_{table_name}_{timestamp}.json"

    print(f"[備份] 區域: {settings.aws_region}")
    print(f"[備份] 資料表: {table_name}")
    print(f"[備份] 輸出檔案: {out_path}")

    table = get_aws_resource("dynamodb").Table(table_name)
    items = scan_all_items(table)
    items = _decimal_to_native(items)

    payload = {
        "table_name": table_name,
        "region": settings.aws_region,
        "backed_up_at": datetime.now(timezone.utc).isoformat(),
        "item_count": len(items),
        "items": items,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"[完成] 已備份 {len(items)} 筆資料到 {out_path}")


if __name__ == "__main__":
    main()
