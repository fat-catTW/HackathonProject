"""Health-need -> product recommendation engine for the Lambda tool handler.

Mirrors backend/app/services/health_recommendation.py's rule-based fallback —
duplicated here because lambda_tools is packaged and deployed separately
from backend (see docs/mcp-gateway-lambda-setup.md). The backend's Bedrock+
Google external-search path isn't ported here; this always uses keyword
matching.
"""
from __future__ import annotations

HEALTH_KEYWORDS: dict[str, list[str]] = {
    "減脂": ["減脂", "低碳", "低卡", "高蛋白"],
    "增肌": ["增肌", "高蛋白", "均衡"],
    "三高": ["低鈉", "低脂", "低糖"],
    "低鈉": ["低鈉"],
    "素食": ["素食"],
    "低糖": ["低糖"],
    "高纖": ["高纖"],
}

UNHEALTHY_TAGS = ["高糖", "高鈉", "高脂", "高熱量"]


def fallback_recommend(query: str, products: list[dict]) -> list[dict]:
    matched = [
        product
        for product in products
        if any(tag in query for tag in product["tags"])
        or any(
            keyword in query and any(tag in product["tags"] for tag in related_tags)
            for keyword, related_tags in HEALTH_KEYWORDS.items()
        )
    ]
    pool = matched if matched else [
        product for product in products if not any(tag in UNHEALTHY_TAGS for tag in product["tags"])
    ]
    return [
        {
            "product_id": product["id"],
            "name": product["name"],
            "reason": f"關鍵字比對：商品標籤包含 {'、'.join(product['tags'])}",
            "match_tags": product["tags"],
        }
        for product in pool[:5]
    ]


def recommend(query: str, products: list[dict]) -> dict:
    return {
        "query": query,
        "recommendations": fallback_recommend(query, products),
        "fallback_used": True,
    }
