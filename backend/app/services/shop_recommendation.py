"""Shopping need -> product recommendation engine. Bedrock-backed (see
app/agent/llm.py's recommend_shop_products, which reuses the same
_converse_json client already used for service routing/form-filling),
with a keyword/tag/rating fallback when Bedrock is unavailable. Mirrors the
shape of health_recommendation.py's recommend()/fallback_recommend()."""
from __future__ import annotations

from ..agent import llm


def fallback_recommend(query: str, products: list[dict]) -> list[dict]:
    def match_score(product: dict) -> int:
        tags = product.get("tags", [])
        name_hit = 1 if product["name"] in query else 0
        return sum(1 for tag in tags if tag in query) + name_hit

    scored = [(match_score(p), p) for p in products]
    matched = [p for score, p in scored if score > 0]
    pool = matched if matched else products
    ranked = sorted(pool, key=lambda p: (-p.get("rating_avg", 0), -p.get("rating_count", 0)))
    return [
        {
            **p,
            "reason": (
                f"依標籤與評分挑選：{'、'.join(p.get('tags', [])) or p['description']}"
                f"（★{p.get('rating_avg')}，{p.get('rating_count')} 則評價）"
            ),
        }
        for p in ranked[:5]
    ]


def recommend(query: str, products: list[dict]) -> dict:
    """Returns {"query", "recommendations", "fallback_used"}."""
    recommendations = llm.recommend_shop_products(query, products)
    if recommendations is not None:
        return {"query": query, "recommendations": recommendations, "fallback_used": False}
    return {"query": query, "recommendations": fallback_recommend(query, products), "fallback_used": True}
