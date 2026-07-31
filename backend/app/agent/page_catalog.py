"""Shared page knowledge helpers for backend page guidance."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
PAGE_CATALOG_PATH = REPO_ROOT / "lambda_tools" / "page_knowledge" / "pages.json"

CURRENT_PAGE_HINTS = ("這頁", "這一頁", "目前頁面", "當前頁面", "現在這頁")
NAVIGATION_HINTS = (
    "怎麼去",
    "怎麼到",
    "去哪裡",
    "哪裡看",
    "哪裡可以",
    "怎麼看",
    "從哪裡",
    "如何前往",
    "如何進入",
    "在哪",
    "在哪裡",
)
APPLICATION_HINTS = (
    "申請",
    "表單",
    "填表",
    "填單",
    "填寫",
    "預約",
    "手動填",
    "送出",
)
ORDER_HISTORY_HINTS = (
    "我的服務",
    "我的訂單",
    "訂單",
    "下訂",
    "已下訂",
    "已經下訂",
    "查看訂單",
    "查訂單",
    "訂單進度",
    "案件進度",
)

SERVICE_FORM_ALIASES = {
    "service_form_plumbing_repair": (
        "水電",
        "維修",
        "修繕",
        "漏水",
        "堵塞",
    ),
    "service_form_washing_machine_cleaning": (
        "洗衣機",
        "洗衣機清潔",
        "洗衣機清洗",
        "清洗洗衣機",
    ),
    "service_form_air_conditioner_cleaning": (
        "冷氣",
        "冷氣清潔",
        "冷氣清洗",
        "洗冷氣",
        "冷氣機",
    ),
    "service_form_home_cleaning": (
        "居家清潔",
        "家庭清潔",
        "打掃",
        "居家打掃",
    ),
    "service_form_restaurant_reservation": (
        "餐廳",
        "訂位",
        "訂餐廳",
        "吃飯",
        "用餐",
    ),
    "service_form_food_delivery": (
        "外送",
        "美食",
        "外帶",
        "叫外送",
        "點餐",
    ),
    "service_form_health_product_recommendation": (
        "健康",
        "營養",
        "減脂",
        "增肌",
        "低鈉",
        "推薦",
    ),
}


def _normalize(text: str) -> str:
    return " ".join((text or "").strip().lower().split())


def _page_fragments(page: dict) -> list[str]:
    fragments = [
        page.get("page_id", ""),
        page.get("route", ""),
        page.get("title", ""),
        page.get("summary", ""),
    ]
    fragments.extend(page.get("features", []))
    fragments.extend(page.get("available_actions", []))
    fragments.extend(page.get("next_steps", []))
    fragments.extend(page.get("related_pages", []))
    fragments.extend(page.get("keywords", []))
    return [fragment for fragment in fragments if fragment]


def is_navigation_query(text: str) -> bool:
    normalized_text = _normalize(text)
    return any(hint in normalized_text for hint in NAVIGATION_HINTS)


def is_application_query(text: str) -> bool:
    normalized_text = _normalize(text)
    return any(hint in normalized_text for hint in APPLICATION_HINTS)


def _current_page_query(text: str) -> bool:
    return any(hint in text for hint in CURRENT_PAGE_HINTS)


def _service_alias_hits(page_id: str, text: str) -> list[str]:
    return [alias for alias in SERVICE_FORM_ALIASES.get(page_id, ()) if alias in text]


def _push_reason(reasons: list[str], reason: str) -> None:
    if reason not in reasons:
        reasons.append(reason)


@lru_cache
def load_pages() -> list[dict]:
    with PAGE_CATALOG_PATH.open("r", encoding="utf-8") as fp:
        payload = json.load(fp)
    if not isinstance(payload, list):
        raise ValueError("pages.json must contain a list of pages.")
    return payload


def load_page(page_id: str) -> dict | None:
    return next((page for page in load_pages() if page.get("page_id") == page_id), None)


def page_ids() -> set[str]:
    return {page.get("page_id", "") for page in load_pages()}


def page_keywords() -> set[str]:
    values: set[str] = set()
    for page in load_pages():
        for keyword in page.get("keywords", []):
            if keyword:
                values.add(keyword)
        title = page.get("title")
        if title:
            values.add(title)
        page_id = page.get("page_id")
        if page_id:
            values.add(page_id)
    return values


def search_pages(query: str, current_page_id: str | None = None, *, limit: int = 5) -> list[dict]:
    normalized_query = _normalize(query)
    if not normalized_query:
        return []

    navigation_query = is_navigation_query(normalized_query)
    application_query = is_application_query(normalized_query)
    current_page_query = _current_page_query(query)

    scored: list[tuple[int, dict, list[str]]] = []
    for page in load_pages():
        score = 0
        reasons: list[str] = []
        page_id = page.get("page_id", "")
        title = page.get("title", "")

        if page_id and page_id.lower() in normalized_query:
            score += 10
            _push_reason(reasons, f"matched page id '{page_id}'")
        if title and title.lower() in normalized_query:
            score += 9
            _push_reason(reasons, f"matched page title '{title}'")

        for keyword in page.get("keywords", []):
            if keyword and keyword.lower() in normalized_query:
                score += 6
                _push_reason(reasons, f"matched keyword '{keyword}'")

        for fragment in _page_fragments(page):
            lowered = fragment.lower()
            if lowered and lowered in normalized_query and not any(fragment in reason for reason in reasons):
                score += 2
                _push_reason(reasons, f"matched page detail '{fragment}'")

        alias_hits = _service_alias_hits(page_id, normalized_query)
        if alias_hits:
            score += 7 + len(alias_hits) * 3
            _push_reason(reasons, f"matched service terms '{'、'.join(alias_hits[:3])}'")

        if page_id.startswith("service_form_") and application_query and alias_hits:
            score += 12
            _push_reason(reasons, "matched service application intent")
            if navigation_query:
                score += 6
                _push_reason(reasons, "matched navigation intent for a service form")

        if page_id == "service_form" and application_query:
            score += 3
            _push_reason(reasons, "matched generic form intent")

        if page_id == "home" and navigation_query and application_query:
            score += 4
            _push_reason(reasons, "home is the entry page for service applications")

        if page_id == "my_services" and navigation_query and any(
            hint.lower() in normalized_query for hint in ORDER_HISTORY_HINTS
        ):
            score += 18
            _push_reason(reasons, "matched order history navigation intent")

        if current_page_id and current_page_id == page_id and current_page_query:
            score += 8
            _push_reason(reasons, "boosted current page context")

        if score > 0:
            scored.append((score, page, reasons))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [
        {
            "page_id": page["page_id"],
            "title": page["title"],
            "summary": page["summary"],
            "route": page.get("route", ""),
            "relevance_score": score,
            "relevance_reason": "; ".join(reasons[:3]),
        }
        for score, page, reasons in scored[:limit]
    ]
