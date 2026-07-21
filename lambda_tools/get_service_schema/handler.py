"""AgentCore Gateway Tool: get_service_schema（設計書 §12.2）。"""
import os

import boto3

TABLE = os.environ.get("DYNAMODB_TABLE_NAME", "ServiceAssistant")


def lambda_handler(event, context):
    service_id = (event or {}).get("service_id")
    if not service_id:
        return {"success": False, "error": {
            "code": "INVALID_FORM_DATA", "message": "缺少 service_id"}}
    ddb = boto3.resource("dynamodb").Table(TABLE)
    resp = ddb.get_item(Key={"PK": f"SERVICE#{service_id}", "SK": "METADATA"})
    item = resp.get("Item")
    if not item or not item.get("enabled"):
        return {"success": False, "error": {
            "code": "SERVICE_NOT_FOUND", "message": "找不到指定服務"}}
    return {"success": True, "service_id": service_id,
            "title": item["name"], "fields": item["schema"]["fields"]}
