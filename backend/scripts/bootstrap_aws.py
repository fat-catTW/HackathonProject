"""Bootstrap the minimum AWS resources needed by the backend."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from botocore.exceptions import ClientError

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings
from app.services.aws import get_aws_client


def ensure_table() -> str:
    settings = get_settings()
    client = get_aws_client("dynamodb")
    table_name = settings.dynamodb_table_name

    try:
        client.describe_table(TableName=table_name)
        return f"DynamoDB table already exists: {table_name}"
    except ClientError as exc:
        if exc.response["Error"]["Code"] != "ResourceNotFoundException":
            raise

    client.create_table(
        TableName=table_name,
        AttributeDefinitions=[
            {"AttributeName": "PK", "AttributeType": "S"},
            {"AttributeName": "SK", "AttributeType": "S"},
        ],
        KeySchema=[
            {"AttributeName": "PK", "KeyType": "HASH"},
            {"AttributeName": "SK", "KeyType": "RANGE"},
        ],
        BillingMode="PAY_PER_REQUEST",
    )
    waiter = client.get_waiter("table_exists")
    waiter.wait(TableName=table_name, WaiterConfig={"Delay": 2, "MaxAttempts": 30})
    return f"DynamoDB table created: {table_name}"


def probe_bedrock() -> str:
    settings = get_settings()
    client = get_aws_client("bedrock-runtime")
    response = client.converse(
        modelId=settings.bedrock_model_id,
        system=[{"text": "Reply with JSON only."}],
        messages=[{"role": "user", "content": [{"text": "{\"status\":\"ping\"}"}]}],
        inferenceConfig={"maxTokens": 64, "temperature": 0},
    )
    text = ""
    for block in (((response.get("output") or {}).get("message") or {}).get("content") or []):
        if isinstance(block, dict):
            text += block.get("text", "")
    return f"Bedrock invoke ok for model {settings.bedrock_model_id}: {text[:120]}"


def main() -> None:
    settings = get_settings()
    summary = {
        "region": settings.aws_region,
        "table": settings.dynamodb_table_name,
        "tool_mode": settings.agent_tool_mode,
        "allow_demo_auth": settings.allow_demo_auth,
        "steps": [],
    }
    summary["steps"].append(ensure_table())
    try:
        summary["steps"].append(probe_bedrock())
    except Exception as exc:  # noqa: BLE001
        summary["steps"].append(f"Bedrock check skipped or failed: {exc}")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
