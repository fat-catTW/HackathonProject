"""把既有案件的聯絡資訊改成密文＋遮罩（Milestone 15）。

欄位級加密是 save_request 才開始做的（見 services/contact_privacy.py），之前寫進
DynamoDB 的案件仍是明文。廠商後台對這些舊案件一樣只給遮罩值（明細會就地遮罩），
所以不跑這支腳本也不會外洩到畫面上——但資料庫裡還躺著明文，該補還是要補。

案件本體（SERVICE_REQUEST）與廠商索引（VENDOR_REQUEST_INDEX）都會處理。可重複
執行：已經是密文的項目直接略過。寫回時比對 version，期間被改過的案件會跳過而不是
覆蓋掉別人的更新，下次再跑一次即可。

    python backend/scripts/backfill_encrypt_contacts.py --dry-run
    python backend/scripts/backfill_encrypt_contacts.py
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings
from app.services import contact_privacy
from app.services.aws import get_aws_resource

TARGET_ENTITY_TYPES = ("SERVICE_REQUEST", "VENDOR_REQUEST_INDEX")


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


def needs_backfill(item: dict) -> bool:
    form_data = item.get("form_data")
    if not isinstance(form_data, dict) or not form_data:
        return False
    if not any(key in contact_privacy.CONTACT_FIELDS for key in form_data):
        return False
    return not contact_privacy.is_fully_encrypted(form_data) or "form_data_masked" not in item


def encrypted_item(item: dict) -> dict:
    plain = contact_privacy.decrypt_form_data(item["form_data"])
    return dict(item) | {
        "form_data": contact_privacy.encrypt_form_data(plain),
        "form_data_masked": contact_privacy.masked_form_data(plain),
    }


def write_back(table, item: dict) -> bool:
    """以 version 為條件寫回；期間被改過就跳過（回 False）。"""
    from botocore.exceptions import ClientError

    version = item.get("version")
    if version is None:
        condition, values = "attribute_not_exists(version)", None
    else:
        condition, values = "version = :v", {":v": version}
    try:
        kwargs = {"Item": item, "ConditionExpression": condition}
        if values:
            kwargs["ExpressionAttributeValues"] = values
        table.put_item(**kwargs)
        return True
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return False
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="只列出要處理的項目")
    args = parser.parse_args()

    settings = get_settings()
    if settings.use_mock:
        print("USE_MOCK=true：本地記憶體儲存不需要回填。")
        return 0

    table = get_aws_resource("dynamodb").Table(settings.dynamodb_table_name)
    items = [i for i in scan_all(table) if i.get("entity_type") in TARGET_ENTITY_TYPES]
    todo = [i for i in items if needs_backfill(i)]

    print(f"掃到 {len(items)} 筆案件／索引，其中 {len(todo)} 筆需要加密。")
    if args.dry_run:
        for item in todo:
            # 只印遮罩值：這支腳本的目的就是別讓聯絡資訊到處散落。
            masked = contact_privacy.masked_form_data(
                contact_privacy.decrypt_form_data(item["form_data"])
            )
            print(f"  + {item['PK']} {item['SK']} {masked}")
        return 0

    written = skipped = 0
    for item in todo:
        if write_back(table, encrypted_item(item)):
            written += 1
        else:
            skipped += 1
            print(f"  ! {item['PK']} {item['SK']} 期間被更新，未寫入（可再跑一次）")
    print(f"已加密 {written} 筆，略過 {skipped} 筆。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
