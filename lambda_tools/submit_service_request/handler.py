"""AgentCore Gateway Tool: submit_service_request（設計書 §12.3）。

actorId 不由 Agent／前端傳入，而是取自 Gateway 傳遞的已驗證身分
（requestContext / workload identity），符合 §17.2 資料隔離。
"""
import os
import uuid
from datetime import datetime, timezone, timedelta

import boto3

TABLE = os.environ.get("DYNAMODB_TABLE_NAME", "ServiceAssistant")
TZ = timezone(timedelta(hours=8))


def _verified_actor_id(event, context) -> str | None:
    # AgentCore Gateway 會將已驗證身分放入 context/claims；此處示意
    ident = (event.get("requestContext") or {}).get("identity") or {}
    return ident.get("actorId")


def lambda_handler(event, context):
    service_id = event.get("service_id")
    session_id = event.get("session_id")
    payload = event.get("payload") or {}
    actor_id = _verified_actor_id(event, context)
    if not actor_id:
        return {"success": False, "error": {
            "code": "UNAUTHORIZED", "message": "無法取得已驗證身分"}}

    ddb = boto3.resource("dynamodb").Table(TABLE)
    svc = ddb.get_item(
        Key={"PK": f"SERVICE#{service_id}", "SK": "METADATA"}).get("Item")
    if not svc:
        return {"success": False, "error": {
            "code": "SERVICE_NOT_FOUND", "message": "找不到指定服務"}}

    required = [f["id"] for f in svc["schema"]["fields"] if f.get("required")]
    missing = [fid for fid in required if payload.get(fid) in (None, "")]
    if missing:
        return {"success": False, "error": {
            "code": "INVALID_FORM_DATA", "message": "表單資料不完整",
            "missing_fields": missing}}

    now = datetime.now(TZ).isoformat(timespec="seconds")
    request_id = f"REQ-{datetime.now(TZ):%Y%m%d}-{uuid.uuid4().hex[:6].upper()}"
    ddb.put_item(Item={
        "PK": f"USER#{actor_id}", "SK": f"REQUEST#{request_id}",
        "entity_type": "SERVICE_REQUEST",
        "request_id": request_id, "session_id": session_id,
        "service_id": service_id, "service_name": svc["name"],
        "status": "SUBMITTED", "form_data": payload,
        "created_at": now, "updated_at": now,
    })
    return {"success": True, "request_id": request_id,
            "status": "SUBMITTED", "message": "服務申請已成功建立"}
