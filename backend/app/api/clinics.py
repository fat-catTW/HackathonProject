"""Clinic directory, symptom triage, appointment, and cross-sell API endpoints."""
from fastapi import APIRouter, Depends, HTTPException

from ..agent import llm
from ..auth.cognito import CurrentUser, get_current_user
from ..services import clinic_appointment, clinic_catalog, health_catalog

router = APIRouter()


def _raise_api_error(status_code: int, code: str, message: str):
    raise HTTPException(status_code=status_code, detail={"success": False, "error": {"code": code, "message": message}})


@router.get("/api/clinics")
def list_clinics(
    city: str,
    district: str,
    specialty: str | None = None,
    user: CurrentUser = Depends(get_current_user),
):
    return {"clinics": clinic_catalog.list_clinics(city, district, specialty)}


@router.post("/api/symptom-triage")
def symptom_triage(payload: dict, user: CurrentUser = Depends(get_current_user)):
    symptom_text = str(payload.get("symptom_text") or "").strip()
    if not symptom_text:
        _raise_api_error(400, "INVALID_FORM_DATA", "請描述您的症狀。")
    city = str(payload.get("city") or "台中市").strip()
    district = str(payload.get("district") or "西屯區").strip()

    triage = llm.triage_symptom(symptom_text)
    candidates = clinic_catalog.list_clinics(city, district, triage["specialty"])
    recommendation = llm.recommend_clinic(symptom_text, candidates)

    return {
        "specialty": triage["specialty"],
        "advisory": triage["advisory"],
        "clinics": candidates,
        "recommended_clinic_id": recommendation["id"] if recommendation else None,
        "recommend_reason": recommendation["reason"] if recommendation else None,
    }


@router.post("/api/clinic-appointments")
def submit_appointment(payload: dict, user: CurrentUser = Depends(get_current_user)):
    result = clinic_appointment.create_appointment(user.sub, payload)
    if not result.get("success"):
        error = result.get("error", {})
        status_code = 404 if error.get("code") == "CLINIC_NOT_FOUND" else 400
        _raise_api_error(status_code, error.get("code", "APPOINTMENT_FAILED"), error.get("message", "掛號失敗"))
    return result


@router.get("/api/clinic-appointments/{request_id}")
def get_clinic_appointment_detail(request_id: str, user: CurrentUser = Depends(get_current_user)):
    order = clinic_appointment.get_appointment(user.sub, request_id)
    if not order:
        _raise_api_error(404, "REQUEST_NOT_FOUND", "找不到對應的掛號紀錄。")
    return order


@router.post("/api/clinic-appointments/{request_id}/cross-sell")
def cross_sell(request_id: str, user: CurrentUser = Depends(get_current_user)):
    order = clinic_appointment.get_appointment(user.sub, request_id)
    if not order:
        _raise_api_error(404, "REQUEST_NOT_FOUND", "找不到對應的掛號紀錄。")
    symptom_text = order["form_data"].get("symptom_note", "")
    products = health_catalog.list_products()
    result = llm.recommend_health_products_for_symptom(symptom_text, products)
    name_by_product_id = {product["id"]: product["name"] for product in products}
    for rec in result["recommendations"]:
        rec["name"] = name_by_product_id.get(rec["product_id"], "")
    return result
