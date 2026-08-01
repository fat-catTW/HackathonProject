"""Keyword-matched bundles for one-shot 'quick purchase' requests.

Used by the multi-task orchestrator (see app/agent/agent.py) so a task like
"買供品跟水果" resolves straight to a single-SKU order instead of the full
shop_purchase cart/browse flow.
"""
from __future__ import annotations

QUICK_PURCHASE_BUNDLES: list[dict] = [
    {
        "sku_id": "sku_fruit_offering_set",
        "name": "清明祭祖水果盆",
        "keywords": ["水果", "供品", "祭拜", "拜拜", "祭祖", "水果盆"],
    },
    {
        "sku_id": "sku_three_sacrifice_set",
        "name": "三牲祭祀組合",
        "keywords": ["三牲", "牲禮", "祭祀"],
    },
]


def match_bundle(query: str) -> dict | None:
    for bundle in QUICK_PURCHASE_BUNDLES:
        if any(keyword in query for keyword in bundle["keywords"]):
            return bundle
    return None
