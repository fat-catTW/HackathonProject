"""Service catalog and direct form submission APIs."""
from fastapi import APIRouter, Depends, HTTPException

from ..auth.cognito import CurrentUser, get_current_user
from ..services import catalog, shipping
from ..services.submission import create_manual_service_request

router = APIRouter()


def _raise_api_error(status_code: int, code: str, message: str, **extra):
    detail = {"success": False, "error": {"code": code, "message": message}}
    if extra:
        detail["error"].update(extra)
    raise HTTPException(status_code=status_code, detail=detail)


@router.get("/api/services")
def list_services(user: CurrentUser = Depends(get_current_user)):
    return {"services": catalog.list_services()}


@router.get("/api/services/{service_id}/schema")
def get_service_schema(service_id: str, user: CurrentUser = Depends(get_current_user)):
    schema = catalog.get_service_schema(service_id)
    if not schema:
        _raise_api_error(404, "SERVICE_NOT_FOUND", "Service was not found.")
    return schema


@router.post("/api/services/{service_id}/requests")
def create_service_request(
    service_id: str,
    body: dict,
    user: CurrentUser = Depends(get_current_user),
):
    payload = body.get("payload") or {}

    if service_id == "package_shipping":
        result = shipping.create_shipping_order(actor_id=user.sub, payload=payload)
    else:
        result = create_manual_service_request(
            actor_id=user.sub,
            service_id=service_id,
            payload=payload,
        )

    if not result.get("success", True):
        error = result.get("error", {})
        client_error_codes = {
            "INVALID_FORM_DATA",
            "PACKAGE_TOO_LARGE",
            "OUT_OF_SERVICE_AREA",
            "DECLARED_VALUE_TOO_HIGH",
        }
        status_code = (
            400
            if error.get("code") in client_error_codes
            else 404
            if error.get("code") == "SERVICE_NOT_FOUND"
            else 503
        )
        _raise_api_error(
            status_code,
            error.get("code", "REQUEST_CREATE_FAILED"),
            error.get("message", "Failed to create service request."),
            missing_fields=error.get("missing_fields", []),
        )

    message = result.get("message", "")
    if result.get("estimated_fee_min") is not None:
        message = (
            f"預估運費約 NT${result['estimated_fee_min']}–{result['estimated_fee_max']}，"
            "正式報價將由客服於 30 分鐘內回覆確認。"
        )
    return {
        "success": True,
        "request_id": result.get("request_id"),
        "status": result.get("status"),
        "message": message,
    }
