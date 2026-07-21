"""AgentCore Gateway Tool: list_services（設計書 §12.1）。
Milestone 4 部署至 AWS Lambda，讀取 DynamoDB Service Catalog。
"""
import json
import os

import boto3

TABLE = os.environ.get("DYNAMODB_TABLE_NAME", "ServiceAssistant")


def lambda_handler(event, context):
    try:
        ddb = boto3.resource("dynamodb").Table(TABLE)
        # 單表設計：SERVICE#<id> / METADATA
        resp = ddb.scan(
            FilterExpression="entity_type = :t AND enabled = :e",
            ExpressionAttributeValues={":t": "SERVICE", ":e": True},
        )
        services = [
            {"id": i["PK"].split("#", 1)[1], "name": i["name"],
             "description": i.get("description", "")}
            for i in resp.get("Items", [])
        ]
        return {"success": True, "services": services}
    except Exception:
        return {"success": False, "error": {
            "code": "SERVICE_CATALOG_UNAVAILABLE",
            "message": "目前無法取得服務列表"}}
