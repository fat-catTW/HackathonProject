"""One-shot 'quick purchase' order: match free text to a curated bundle and
submit directly. Falls back to a Bedrock-ranked Google search when no
internal bundle keyword matches, creating a PENDING_PROVIDER case for the
externally-sourced pick instead of a real stocked/pointed order."""
from __future__ import annotations

from ..agent import llm
from . import external_search, quick_purchase_catalog, shop
from .store import STORE, now_iso


def create_quick_purchase_order(
    actor_id: str, query: str, *, contact_name: str, phone: str, address: str
) -> dict:
    bundle = quick_purchase_catalog.match_bundle(query)
    if bundle:
        payload = {
            "cart": [{"sku_id": bundle["sku_id"], "quantity": 1}],
            "contact_name": contact_name,
            "phone": phone,
            "address": {"city": "", "street": address, "contact_name": contact_name},
        }
        result = shop.create_shop_order(actor_id, payload)
        if result.get("success"):
            result["bundle_name"] = bundle["name"]
        return result

    external = _find_external_bundle(query)
    if not external:
        return {
            "success": False,
            "error": {"code": "BUNDLE_NOT_FOUND", "message": f"找不到符合「{query}」的商品組合"},
        }
    return _create_external_quick_purchase_order(
        actor_id, external, contact_name=contact_name, phone=phone, address=address
    )


def _find_external_bundle(query: str) -> dict | None:
    if not llm.is_available():
        return None
    search_query = llm.plan_external_query(query, purpose="one-shot 供品/生活用品採購")
    if not search_query:
        return None
    results = external_search.google_text_search(search_query)
    if not results:
        return None
    candidates = [
        {"result_id": str(i), "name": r["title"], "detail": r["snippet"], "link": r["link"]}
        for i, r in enumerate(results)
    ]
    picks = llm.rank_external_results(query, candidates, id_key="result_id", max_results=1)
    return picks[0] if picks else None


def _create_external_quick_purchase_order(
    actor_id: str, external: dict, *, contact_name: str, phone: str, address: str
) -> dict:
    request_id = STORE.next_request_id()
    created_at = now_iso()
    order = {
        "request_id": request_id,
        "service_id": "shop_purchase",
        "service_name": "商城購物（網路搜尋商品）",
        "order_type": "10",
        "status": "PENDING_PROVIDER",
        "source": "google_search",
        "form_data": {
            "query_matched_name": external["name"],
            "external_detail": external.get("detail", ""),
            "external_link": external.get("link", ""),
            "contact_name": contact_name,
            "phone": phone,
            "address": address,
        },
        "status_history": [{"status": "PENDING_PROVIDER", "at": created_at}],
        "created_at": created_at,
    }
    try:
        STORE.save_request(actor_id, order)
    except Exception:
        return {
            "success": False,
            "error": {"code": "ORDER_SAVE_FAILED", "message": "訂單建立失敗，請稍後再試"},
        }
    return {
        "success": True,
        "request_id": request_id,
        "status": "PENDING_PROVIDER",
        "bundle_name": external["name"],
        "source": "google_search",
    }
