"""One-shot 'quick purchase' order: match free text to a curated bundle and submit directly."""
from __future__ import annotations

from . import quick_purchase_catalog, shop


def create_quick_purchase_order(
    actor_id: str, query: str, *, contact_name: str, phone: str, address: str
) -> dict:
    bundle = quick_purchase_catalog.match_bundle(query)
    if not bundle:
        return {
            "success": False,
            "error": {"code": "BUNDLE_NOT_FOUND", "message": f"找不到符合「{query}」的商品組合"},
        }

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
