"""Health-need -> product recommendation engine.

Ported from the standalone 711-health-mcp prototype
(src/services/recommendationEngine.ts). Kept as a direct Gemini API call
(not routed through app/agent/llm.py's Bedrock client) per product decision:
this feature keeps using Gemini for now, the rest of the agent stays on
Bedrock. Falls back to keyword/tag matching when GEMINI_API_KEY is not
configured or the Gemini call fails for any reason, mirroring the
original's fallback_used flag.
"""
from __future__ import annotations

import json
from functools import lru_cache

from ..config import get_settings

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

_RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "recommendations": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "product_id": {"type": "STRING"},
                    "reason": {"type": "STRING"},
                },
                "required": ["product_id", "reason"],
            },
        },
    },
    "required": ["recommendations"],
}


def fallback_recommend(query: str, products: list[dict]) -> list[dict]:
    """Rule-based keyword/tag matching, used when Gemini is unavailable."""
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


@lru_cache
def _get_client():
    settings = get_settings()
    if not settings.gemini_api_key:
        return None
    try:
        from google import genai
    except ImportError:
        return None
    try:
        return genai.Client(api_key=settings.gemini_api_key)
    except Exception:
        return None


def _analyze_with_gemini(query: str, products: list[dict]) -> list[dict] | None:
    client = _get_client()
    if client is None:
        return None

    from google.genai import types

    product_list = "\n".join(
        f"{p['id']}|{p['name']}|{p['category']}|熱量{p['calories']}kcal|"
        f"蛋白質{p['protein_g']}g|碳水{p['carbs_g']}g|脂肪{p['fat_g']}g|"
        f"鈉{p['sodium_mg']}mg|標籤:{','.join(p['tags'])}"
        for p in products
    )
    prompt = (
        "你是一個 7-11 商品營養顧問。根據使用者的健康需求，從以下商品清單中挑選最多 5 樣"
        "最符合需求的商品，並用一句話說明理由。\n\n"
        f"使用者需求：{query}\n\n"
        f"商品清單（格式：id|名稱|分類|熱量|蛋白質|碳水|脂肪|鈉|標籤）：\n{product_list}\n\n"
        "只能挑選清單中真實存在的 product_id，不可自行編造。"
    )

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_json_schema=_RESPONSE_SCHEMA,
            ),
        )
        text = response.text
        if not text:
            return None
        parsed = json.loads(text)
    except Exception:
        return None

    by_id = {p["id"]: p for p in products}
    items: list[dict] = []
    for rec in parsed.get("recommendations", []):
        product = by_id.get(rec.get("product_id"))
        if not product:
            continue
        items.append(
            {
                "product_id": product["id"],
                "name": product["name"],
                "reason": rec.get("reason", ""),
                "match_tags": product["tags"],
            }
        )
    return items or None


def recommend(query: str, products: list[dict]) -> dict:
    """Returns {"query", "recommendations", "fallback_used"}."""
    recommendations = _analyze_with_gemini(query, products)
    if recommendations is not None:
        return {"query": query, "recommendations": recommendations, "fallback_used": False}
    return {
        "query": query,
        "recommendations": fallback_recommend(query, products),
        "fallback_used": True,
    }
