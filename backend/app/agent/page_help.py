"""Page guidance helpers backed by shared page knowledge."""
from __future__ import annotations

from .page_catalog import (
    is_application_query,
    is_navigation_query,
    load_page,
    load_pages,
    page_keywords,
    search_pages,
)

CURRENT_PAGE_HINTS = (
    "\u9019\u9801",
    "\u9019\u4e00\u9801",
    "\u76ee\u524d\u9801\u9762",
    "\u7576\u524d\u9801\u9762",
    "\u73fe\u5728\u9019\u9801",
    "\u73fe\u5728\u9019\u500b\u9801\u9762",
    "\u76ee\u524d\u9019\u500b\u756b\u9762",
)

ALL_PAGE_HINTS = (
    "\u6709\u54ea\u4e9b\u9801\u9762",
    "\u6240\u6709\u9801\u9762",
    "\u6574\u500b app \u6709\u54ea\u4e9b\u9801\u9762",
    "\u6574\u500b app \u6709\u4ec0\u9ebc\u9801\u9762",
    "\u9019\u500b app \u6709\u54ea\u4e9b\u9801\u9762",
)

NAVIGATION_HINTS = (
    "\u600e\u9ebc\u53bb",
    "\u600e\u9ebc\u5230",
    "\u53bb\u54ea\u88e1",
    "\u54ea\u88e1\u770b",
    "\u54ea\u88e1\u53ef\u4ee5",
    "\u600e\u9ebc\u770b",
    "\u5f9e\u54ea\u88e1",
    "\u5982\u4f55\u524d\u5f80",
    "\u5982\u4f55\u9032\u5165",
)

PAGE_ACTION_HINTS = (
    "\u53ef\u4ee5\u505a\u4ec0\u9ebc",
    "\u80fd\u505a\u4ec0\u9ebc",
    "\u600e\u9ebc\u7528",
    "\u7528\u9014",
    "\u529f\u80fd",
    "\u4e0b\u4e00\u6b65",
    "\u63a5\u4e0b\u4f86",
    "\u5728\u54ea\u88e1",
    "\u770b\u4ec0\u9ebc",
)

APPLICATION_HINTS = (
    "\u7533\u8acb",
    "\u8868\u55ae",
    "\u586b\u8868",
    "\u586b\u55ae",
    "\u586b\u5beb",
    "\u9810\u7d04",
    "\u624b\u52d5\u586b",
    "\u9001\u51fa",
)

PAGE_TERMS = (
    "\u9801\u9762",
    "\u756b\u9762",
    "app",
    "\u4ecb\u9762",
    "\u529f\u80fd",
)

VOICE_HINTS = (
    "\u8a9e\u97f3",
    "\u9ea5\u514b\u98a8",
    "\u7528\u8aaa\u7684",
    "\u7528\u8b1b\u7684",
    "\u8aaa\u7d66\u4f60",
    "\u8b1b\u7d66\u4f60",
    "\u8a9e\u97f3\u4f86\u586b",
    "\u8a9e\u97f3\u586b",
    "\u8a9e\u97f3\u8f38\u5165",
)


def is_voice_filling_question(message: str) -> bool:
    text = (message or "").strip()
    return bool(text) and any(hint in text for hint in VOICE_HINTS)


def looks_like_page_question(message: str, current_page_id: str | None = None) -> bool:
    text = (message or "").strip()
    if not text:
        return False
    if is_voice_filling_question(text):
        return True
    if any(hint in text for hint in CURRENT_PAGE_HINTS + ALL_PAGE_HINTS + NAVIGATION_HINTS + PAGE_ACTION_HINTS):
        return True
    if any(term in text for term in PAGE_TERMS):
        return True
    if current_page_id and current_page_id in text:
        return True
    return any(keyword in text for keyword in page_keywords())


def build_page_tool_request(message: str, current_page_id: str | None = None) -> tuple[str, dict] | None:
    text = (message or "").strip()
    if not looks_like_page_question(text, current_page_id):
        return None
    if any(hint in text for hint in ALL_PAGE_HINTS):
        return None
    if current_page_id and _prefer_current_page(text):
        return ("get_page_context", {"page_id": current_page_id})
    return ("search_pages", {"query": text, "current_page_id": current_page_id})


def answer_page_question(
    message: str,
    current_page_id: str | None = None,
    tool_payload: dict | None = None,
) -> str | None:
    text = (message or "").strip()
    if not looks_like_page_question(text, current_page_id):
        return None

    if is_voice_filling_question(text):
        if current_page_id:
            page = load_page(current_page_id)
            if page:
                return _format_voice_filling_reply(page)
        return _format_voice_filling_reply({"page_id": "", "title": "AI 管家"})

    if any(hint in text for hint in ALL_PAGE_HINTS):
        return _build_all_pages_reply(current_page_id)

    if isinstance(tool_payload, dict) and tool_payload.get("success"):
        if isinstance(tool_payload.get("page"), dict):
            return _format_page_reply(tool_payload["page"], current_page_id=current_page_id)
        matches = tool_payload.get("matches")
        if isinstance(matches, list) and matches:
            return _format_search_reply(matches, message=text, current_page_id=current_page_id)

    if current_page_id and _prefer_current_page(text):
        page = load_page(current_page_id)
        if page:
            return _format_page_reply(page, current_page_id=current_page_id)

    matches = search_pages(text, current_page_id=current_page_id)
    if matches:
        return _format_search_reply(matches, message=text, current_page_id=current_page_id)

    if current_page_id:
        page = load_page(current_page_id)
        if page:
            return _format_page_reply(page, current_page_id=current_page_id)
    return _build_all_pages_reply(current_page_id)


def _prefer_current_page(text: str) -> bool:
    if is_voice_filling_question(text):
        return True
    if any(hint in text for hint in CURRENT_PAGE_HINTS):
        return True
    if any(hint in text for hint in PAGE_ACTION_HINTS) and not any(keyword in text for keyword in page_keywords()):
        return True
    return False


def _format_voice_filling_reply(page: dict) -> str:
    page_id = page.get("page_id", "")
    title = page.get("title", "這個頁面")

    if page_id == "assistant":
        return (
            "可以，AI 管家支援語音輸入。"
            "你可以直接按語音按鈕說出需求，例如「我要預約冷氣清洗」或「我要報修水管漏水」，"
            "我會一步一步幫你整理成表單。"
        )

    if page_id == "home":
        return (
            "可以，AI 管家支援用語音填服務需求。"
            "你現在可以直接對我說想申請的服務，例如「我要預約冷氣清洗」或「我要居家清潔」，"
            "我會接著幫你一步一步把資料補齊。"
        )

    if page_id.startswith("service_form_"):
        service_name = title.removesuffix("表單")
        return (
            f"可以，不一定要手動填這張「{title}」。"
            f"如果你想改用語音填單，直接告訴我像「我要申請{service_name}」這樣的需求，"
            "我就會接手一步一步幫你整理資料。"
        )

    return (
        "可以，AI 管家支援用語音整理服務需求。"
        "你直接說想申請的服務和需求內容，我會幫你接著往下填。"
    )


def _format_page_reply(page: dict, current_page_id: str | None = None) -> str:
    is_current = page.get("page_id") == current_page_id
    lines = [
        f"\u4f60\u73fe\u5728\u770b\u5230\u7684\u662f\u300c{page['title']}\u300d\u3002"
        if is_current
        else f"\u300c{page['title']}\u300d\u9019\u9801\u4e3b\u8981\u662f\uff1a"
    ]
    lines.append(page["summary"])
    actions = page.get("available_actions") or page.get("features") or []
    if actions:
        lines.append("\u4f60\u53ef\u4ee5\u5728\u9019\u88e1\u505a\u7684\u4e8b\u60c5\uff1a")
        for index, action in enumerate(actions[:4], start=1):
            lines.append(f"{index}. {action}")
    next_steps = page.get("next_steps") or []
    if next_steps:
        lines.append(f"\u5efa\u8b70\u4e0b\u4e00\u6b65\uff1a{next_steps[0]}")
    return "\n".join(lines)


def _format_search_reply(
    matches: list[dict],
    message: str = "",
    current_page_id: str | None = None,
) -> str:
    top = matches[0]
    if _should_guide_service_application(message, top):
        return _format_service_application_reply(top, current_page_id=current_page_id)

    lines = [
        f"\u548c\u4f60\u7684\u554f\u984c\u6700\u76f8\u95dc\u7684\u662f\u300c{top['title']}\u300d\u3002",
        top["summary"],
    ]
    reason = top.get("relevance_reason")
    if reason:
        lines.append(f"\u6211\u6703\u9019\u6a23\u5224\u65b7\uff1a{reason}")
    if top.get("page_id") != current_page_id:
        lines.append(
            f"\u5982\u679c\u4f60\u8981\u627e\u9019\u500b\u529f\u80fd\uff0c\u512a\u5148\u524d\u5f80\u9019\u4e00\u9801\uff1a{top['title']}\u3002"
        )
    else:
        lines.append("\u4f60\u73fe\u5728\u5c31\u5728\u9019\u4e00\u9801\uff0c\u53ef\u4ee5\u76f4\u63a5\u5728\u9019\u88e1\u7e7c\u7e8c\u64cd\u4f5c\u3002")
    if len(matches) > 1:
        alternatives = "\u3001".join(match["title"] for match in matches[1:3])
        lines.append(f"\u53e6\u5916\u4e5f\u53ef\u80fd\u548c\u300c{alternatives}\u300d\u6709\u95dc\u3002")
    return "\n".join(lines)


def _should_guide_service_application(message: str, top: dict) -> bool:
    if not top.get("page_id", "").startswith("service_form_"):
        return False
    return is_navigation_query(message) and (
        is_application_query(message) or any(hint in message for hint in APPLICATION_HINTS)
    )


def _format_service_application_reply(top: dict, current_page_id: str | None = None) -> str:
    service_name = top["title"].removesuffix("\u8868\u55ae")
    lines = [f"\u4f60\u8981\u627e\u7684\u662f\u300c{top['title']}\u300d\u3002"]

    if top.get("page_id") == current_page_id:
        lines.append("\u4f60\u73fe\u5728\u5df2\u7d93\u5728\u9019\u4e00\u9801\uff0c\u53ef\u4ee5\u76f4\u63a5\u958b\u59cb\u586b\u5beb\u8cc7\u6599\u3002")
    elif current_page_id == "home":
        lines.append(f"1. \u4f60\u73fe\u5728\u5c31\u5728\u300c\u670d\u52d9\u9996\u9801\u300d\uff0c\u76f4\u63a5\u9ede\u9078\u300c{service_name}\u300d\u670d\u52d9\u5361\u7247\u3002")
        lines.append(f"2. \u9032\u5165\u300c{top['title']}\u300d\u5f8c\uff0c\u586b\u5b8c\u8cc7\u6599\u5c31\u80fd\u9001\u51fa\u7533\u8acb\u3002")
        return "\n".join(lines)
    else:
        lines.append("1. \u5148\u5230\u300c\u670d\u52d9\u9996\u9801\u300d\u3002")
        lines.append(f"2. \u5728\u9996\u9801\u9ede\u9078\u300c{service_name}\u300d\u670d\u52d9\u5361\u7247\u3002")

    lines.append(f"3. \u9032\u5165\u300c{top['title']}\u300d\u5f8c\uff0c\u586b\u5beb\u8cc7\u6599\u4e26\u9001\u51fa\u7533\u8acb\u3002")
    return "\n".join(lines)


def _build_all_pages_reply(current_page_id: str | None = None) -> str:
    lines = ["\u76ee\u524d app \u4e3b\u8981\u9801\u9762\u6709\uff1a"]
    for page in load_pages():
        suffix = "\uff08\u4f60\u76ee\u524d\u5728\u9019\u4e00\u9801\uff09" if page.get("page_id") == current_page_id else ""
        lines.append(f"- {page['title']}\uff1a{page['summary']}{suffix}")
    return "\n".join(lines)
