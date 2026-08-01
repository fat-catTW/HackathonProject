"""Health-need -> product recommendation engine.

Uses the shared Bedrock two-step orchestration (app/agent/llm.py's
plan_external_query / rank_external_results) to search Google for products
beyond the static internal catalog, then falls back to rule-based
keyword/tag matching when Bedrock is unavailable, no Google key is
configured, or the Google call fails for any reason.
"""
from __future__ import annotations

from ..agent import llm
from . import external_search

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

MAX_RECOMMENDATIONS = 5


def fallback_recommend(query: str, products: list[dict]) -> list[dict]:
    """Rule-based keyword/tag matching, used when Bedrock/Google are unavailable."""
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
            "source": "internal",
        }
        for product in pool[:MAX_RECOMMENDATIONS]
    ]


def _internal_candidates(products: list[dict]) -> list[dict]:
    return [
        {
            "product_id": p["id"],
            "name": p["name"],
            "source": "internal",
            "detail": f"{p['category']}|熱量{p['calories']}kcal|標籤:{','.join(p['tags'])}",
        }
        for p in products
    ]


def _analyze_with_bedrock_and_google(query: str, products: list[dict]) -> list[dict] | None:
    if not llm.is_available():
        return None

    candidates = _internal_candidates(products)
    search_query = llm.plan_external_query(query, purpose="health/diet product search")
    if search_query:
        external_results = external_search.google_text_search(search_query)
        if external_results:
            for index, item in enumerate(external_results):
                candidates.append({
                    "product_id": f"external:{index}",
                    "name": item["title"],
                    "source": "google_search",
                    "detail": item["snippet"],
                    "link": item["link"],
                })

    picks = llm.rank_external_results(
        query, candidates, id_key="product_id", max_results=MAX_RECOMMENDATIONS
    )
    if not picks:
        return None

    by_internal_id = {p["id"]: p for p in products}
    recommendations = []
    for pick in picks:
        product = by_internal_id.get(pick["product_id"])
        recommendations.append({
            "product_id": pick["product_id"],
            "name": pick["name"],
            "reason": pick["reason"],
            "match_tags": product["tags"] if product else [],
            "source": pick["source"],
            "link": pick.get("link"),
        })
    return recommendations


def recommend(query: str, products: list[dict]) -> dict:
    """Returns {"query", "recommendations", "fallback_used"}."""
    recommendations = _analyze_with_bedrock_and_google(query, products)
    if recommendations is not None:
        return {"query": query, "recommendations": recommendations, "fallback_used": False}
    return {
        "query": query,
        "recommendations": fallback_recommend(query, products),
        "fallback_used": True,
    }
