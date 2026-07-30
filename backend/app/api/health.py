"""Health product recommendation API endpoints.

This mirrors the read-only, query-and-answer shape of the standalone
711-health-mcp prototype's REST API (POST /api/recommendations,
GET /api/products/:id), adapted to this project's auth (CurrentUser) and
service-layer conventions (health_catalog.py / health_recommendation.py).
Unlike the form-and-submit services, there is no /requests endpoint here —
this feature never creates a SERVICE_REQUEST case.
"""
from fastapi import APIRouter, Depends, HTTPException

from ..auth.cognito import CurrentUser, get_current_user
from ..services import health_catalog, health_recommendation

router = APIRouter()


def _raise_api_error(status_code: int, code: str, message: str):
    raise HTTPException(status_code=status_code, detail={"success": False, "error": {"code": code, "message": message}})


@router.post("/api/health/recommendations")
def recommend_products(body: dict, user: CurrentUser = Depends(get_current_user)):
    query = str(body.get("query") or "").strip()
    if not query:
        _raise_api_error(400, "INVALID_QUERY", "query 不可為空字串")
    result = health_recommendation.recommend(query, health_catalog.list_products())
    return {"success": True, **result}


@router.get("/api/health/products")
def list_products(user: CurrentUser = Depends(get_current_user)):
    return {"products": health_catalog.list_products()}


@router.get("/api/health/products/{product_id}")
def get_product(product_id: str, user: CurrentUser = Depends(get_current_user)):
    product = health_catalog.get_product(product_id)
    if not product:
        _raise_api_error(404, "PRODUCT_NOT_FOUND", f"找不到 product_id: {product_id}")
    return product
