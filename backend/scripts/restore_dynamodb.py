"""從備份 JSON 檔案還原資料到 DynamoDB 資料表。

搭配 scripts/backup_dynamodb.py 產生的備份檔使用。

用法（在 backend 目錄下執行）：

    python scripts/restore_dynamodb.py --in "C:/Users/user/Desktop/dynamodb_backup_ServiceAssistant_20260802_120000.json"
    python scripts/restore_dynamodb.py --in backup.json --table ServiceAssistant

注意：
- 還原前請確認目標資料表已存在（可先執行 scripts/bootstrap_aws.py 建立）。
- 還原採用 put_item（batch_writer），若目標表已有相同 PK/SK 的項目會被覆蓋。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND_ROOT))

from app.config import get_settings  # noqa: E402
from app.services.aws import get_aws_resource  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="從備份 JSON 檔案還原資料到 DynamoDB")
    parser.add_argument("--in", dest="in_path", required=True, help="備份 JSON 檔案路徑")
    parser.add_argument(
        "--table",
        default=None,
        help="目標資料表名稱，預設使用備份檔內記錄的表名，或 .env 的 DYNAMODB_TABLE_NAME",
    )
    args = parser.parse_args()

    in_path = Path(args.in_path)
    if not in_path.exists():
        raise SystemExit(f"找不到備份檔案：{in_path}")

    with in_path.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    settings = get_settings()
    table_name = args.table or payload.get("table_name") or settings.dynamodb_table_name
    items = payload.get("items", [])

    print(f"[還原] 區域: {settings.aws_region}")
    print(f"[還原] 目標資料表: {table_name}")
    print(f"[還原] 備份筆數: {len(items)}")

    if not items:
        print("[還原] 備份檔內沒有任何資料，結束。")
        return

    confirm = input(f"確定要把 {len(items)} 筆資料寫入 {table_name} 嗎？(y/N): ").strip().lower()
    if confirm != "y":
        print("已取消。")
        return

    table = get_aws_resource("dynamodb").Table(table_name)
    with table.batch_writer() as batch:
        for item in items:
            batch.put_item(Item=item)

    print(f"[完成] 已還原 {len(items)} 筆資料到 {table_name}")


if __name__ == "__main__":
    main()
