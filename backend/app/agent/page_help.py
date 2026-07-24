"""Deterministic page help and app navigation guidance."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PageInfo:
    title: str
    aliases: tuple[str, ...]
    description: str
    features: tuple[str, ...]
    navigation_hint: str


PAGE_CATALOG: dict[str, PageInfo] = {
    "landing": PageInfo(
        title="首頁",
        aliases=("首頁", "開場頁", "landing", "landing page"),
        description="這是應用程式的入口頁，會先介紹 AI 管家和目前提供的主要服務。",
        features=(
            "快速了解這個 app 在做什麼",
            "前往登入頁開始使用",
        ),
        navigation_hint="如果你想開始使用，下一步可以先前往登入頁。",
    ),
    "login": PageInfo(
        title="登入頁",
        aliases=("登入", "登入頁", "login", "sign in"),
        description="這裡用來登入系統，登入後才會進到服務首頁。",
        features=(
            "輸入帳號資料登入",
            "使用 Demo 帳號快速體驗",
        ),
        navigation_hint="登入完成後，系統會帶你進到服務首頁。",
    ),
    "home": PageInfo(
        title="服務首頁",
        aliases=("服務首頁", "首頁", "主頁", "home"),
        description="這裡會列出目前所有服務入口，也可以從底部開啟 AI 管家浮層。",
        features=(
            "查看目前提供的服務卡片",
            "進入我的服務頁查看案件",
            "從底部打開 AI 管家詢問或建立需求",
        ),
        navigation_hint="如果你想直接申請服務，可以點服務卡片；如果想先問問題，就按底部的 AI 管家。",
    ),
    "my_services": PageInfo(
        title="我的服務",
        aliases=("我的服務", "服務紀錄", "我的案件", "案件進度"),
        description="這裡會列出你已經送出的服務案件，包含目前狀態與更新時間。",
        features=(
            "查看所有已送出的案件",
            "點進單一案件看詳情",
            "追蹤目前案件進度",
        ),
        navigation_hint="如果你想追蹤案件進度，可以從這裡點進每一筆服務。",
    ),
    "assistant": PageInfo(
        title="AI 管家",
        aliases=("AI 管家", "管家", "助手", "聊天視窗", "assistant"),
        description="AI 管家會協助你介紹頁面、引導操作、整理需求，並在資料齊全時協助建立服務案件。",
        features=(
            "介紹你目前所在頁面的功能",
            "告訴你其他頁面要怎麼找到",
            "幫你整理服務需求並引導填資料",
        ),
        navigation_hint="每個頁面底部都能看到啟動 AI 管家的按鈕，點下去就會打開。",
    ),
    "service_form": PageInfo(
        title="服務表單頁",
        aliases=("服務表單", "表單頁", "申請表單", "預約表單", "填單頁", "service form"),
        description="這裡是手動填寫服務需求的頁面，使用者可以直接輸入資料並送出案件。",
        features=(
            "填寫服務需求欄位",
            "確認聯絡資訊與地址",
            "送出新的服務案件",
        ),
        navigation_hint="從首頁點任一服務卡片，就會進入對應的服務表單。",
    ),
    "request_detail": PageInfo(
        title="案件詳情頁",
        aliases=("案件詳情", "服務詳情", "訂單詳情", "單筆案件", "request detail"),
        description="這裡會顯示單一案件的詳細資料、欄位內容、狀態與對話紀錄。",
        features=(
            "查看案件完整內容",
            "確認最新狀態與更新時間",
            "查看和 AI 管家的相關對話紀錄",
        ),
        navigation_hint="先進入我的服務，再點其中一筆案件，就能查看案件詳情。",
    ),
}

NAVIGATION_RULES: tuple[dict[str, object], ...] = (
    {
        "target_page_id": "my_services",
        "keywords": ("我的服務", "服務紀錄", "我的案件", "案件進度", "已送出的服務", "案件"),
        "reply": "如果你想查看已送出的案件和進度，可以到「我的服務」。",
    },
    {
        "target_page_id": "assistant",
        "keywords": ("AI 管家", "管家", "助手", "聊天視窗"),
        "reply": "如果你想用聊天方式問功能、整理需求或建立服務，可以打開 AI 管家。",
    },
    {
        "target_page_id": "request_detail",
        "keywords": ("案件詳情", "服務詳情", "訂單詳情", "單筆案件"),
        "reply": "如果你想看某一筆案件的完整內容，可以先進入我的服務，再點進對應案件。",
    },
    {
        "target_page_id": "service_form",
        "keywords": ("服務表單", "申請表單", "預約表單", "填單頁", "手動填表"),
        "reply": "如果你想自己手動填資料送出服務，就可以進入服務表單頁。",
    },
    {
        "target_page_id": "home",
        "keywords": ("服務首頁", "首頁", "主頁", "home"),
        "reply": "如果你想回到服務入口總覽，可以回到「服務首頁」。",
    },
    {
        "target_page_id": "login",
        "keywords": ("登入", "登入頁", "login"),
        "reply": "如果你還沒登入，先到登入頁完成登入就能開始使用。",
    },
)

CURRENT_PAGE_HINTS = (
    "我現在在哪",
    "我現在在哪裡",
    "我現在所在的頁面",
    "這是什麼頁面",
    "目前頁面",
    "當前頁面",
    "現在這頁",
)

CURRENT_PAGE_REFERENCES = (
    "這頁",
    "這一頁",
    "這頁面",
    "這個頁面",
    "這個畫面",
    "這裡",
    "目前這頁",
    "當前這頁",
)

ALL_PAGE_HINTS = (
    "有哪些頁面",
    "所有頁面",
    "全部頁面",
    "app 有哪些頁面",
    "這個 app 有哪些頁面",
    "應用程式有哪些頁面",
)

PAGE_ACTION_HINTS = (
    "功能",
    "做什麼",
    "能做什麼",
    "可以做什麼",
    "用途",
    "怎麼用",
    "介紹",
    "操作",
    "可以幹嘛",
    "在幹嘛",
    "幹嘛用",
    "作用",
)

NAVIGATION_HINTS = (
    "怎麼去",
    "怎麼到",
    "怎麼進去",
    "去哪裡看",
    "在哪裡看",
    "在哪看",
    "哪裡可以看",
    "哪裡可以用",
    "怎麼回",
    "怎麼回首頁",
    "怎麼走",
    "帶我去",
    "怎麼開",
    "怎麼打開",
)

ASSISTANT_ROLE_HINTS = (
    "你的任務",
    "你能做什麼",
    "你可以做什麼",
    "你會什麼",
    "你可以幫我什麼",
    "你知道你的任務",
    "你是做什麼的",
    "還有什麼功能",
    "其他功能",
)


def answer_page_question(message: str, current_page_id: str | None = None) -> str | None:
    text = (message or "").strip()
    if not text:
        return None

    if any(keyword in text for keyword in ("新增服務需求", "新增需求", "新增服務")):
        assistant_page = PAGE_CATALOG["assistant"]
        return "\n".join(
            (
                "如果你想新增服務需求，可以直接打開 AI 管家，用對話方式告訴它你的需求。",
                f"{assistant_page.title}：{assistant_page.description}",
                assistant_page.navigation_hint,
            )
        )

    assistant_reply = _answer_assistant_capability_question(text, current_page_id)
    if assistant_reply:
        return assistant_reply

    navigation_reply = _answer_navigation_question(text)
    if navigation_reply:
        return navigation_reply

    if not _looks_like_page_question(text, current_page_id):
        return None

    if any(hint in text for hint in ALL_PAGE_HINTS):
        return _build_all_pages_reply(current_page_id)

    target_ids = _find_target_pages(text, current_page_id)
    if not target_ids and current_page_id in PAGE_CATALOG:
        target_ids = [current_page_id]
    if not target_ids:
        return _build_all_pages_reply(current_page_id)
    return _build_page_reply(target_ids, current_page_id, text)


def _answer_assistant_capability_question(text: str, current_page_id: str | None) -> str | None:
    if not any(hint in text for hint in ASSISTANT_ROLE_HINTS):
        return None

    lines = [
        "我是這個 app 的 AI 管家，主要會幫你三件事：介紹頁面、帶你找功能、協助整理服務需求。",
        "你可以直接問我現在這頁在做什麼、某個功能要去哪裡找，或是讓我陪你把服務資料一步一步填完。",
    ]

    current_page = PAGE_CATALOG.get(current_page_id or "")
    if current_page:
        lines.append(f"你現在所在的是「{current_page.title}」，如果你要，我也可以直接介紹這一頁。")
    return "\n".join(lines)


def _answer_navigation_question(text: str) -> str | None:
    if not _looks_like_navigation_question(text):
        return None

    matched_rules = [
        rule
        for rule in NAVIGATION_RULES
        if any(keyword in text for keyword in rule["keywords"])
    ]
    if not matched_rules:
        return None

    lines: list[str] = []
    for index, rule in enumerate(matched_rules):
        page = PAGE_CATALOG[rule["target_page_id"]]
        if index > 0:
            lines.append("")
        lines.append(str(rule["reply"]))
        lines.append(f"{page.title}：{page.description}")
        lines.append(page.navigation_hint)
    return "\n".join(lines)


def _looks_like_navigation_question(text: str) -> bool:
    return any(hint in text for hint in NAVIGATION_HINTS)


def _looks_like_page_question(text: str, current_page_id: str | None) -> bool:
    if any(hint in text for hint in CURRENT_PAGE_HINTS):
        return True
    if any(hint in text for hint in ALL_PAGE_HINTS):
        return True
    if (
        current_page_id in PAGE_CATALOG
        and any(reference in text for reference in CURRENT_PAGE_REFERENCES)
        and any(hint in text for hint in PAGE_ACTION_HINTS)
    ):
        return True
    if any(hint in text for hint in PAGE_ACTION_HINTS):
        return any(_mentions_page_alias(text, page.aliases) for page in PAGE_CATALOG.values())
    if current_page_id in PAGE_CATALOG and any(alias in text for alias in PAGE_CATALOG[current_page_id].aliases):
        return True
    return False


def _mentions_page_alias(text: str, aliases: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(alias.lower() in lowered for alias in aliases)


def _find_target_pages(text: str, current_page_id: str | None) -> list[str]:
    targets: list[str] = []
    if current_page_id in PAGE_CATALOG:
        if any(hint in text for hint in CURRENT_PAGE_HINTS) or any(
            reference in text for reference in CURRENT_PAGE_REFERENCES
        ):
            targets.append(current_page_id)
    for page_id, page in PAGE_CATALOG.items():
        if _mentions_page_alias(text, page.aliases) and page_id not in targets:
            targets.append(page_id)
    return targets


def _build_page_reply(target_ids: list[str], current_page_id: str | None, message: str) -> str:
    lines: list[str] = []
    current_page_question = any(hint in message for hint in CURRENT_PAGE_HINTS) or any(
        reference in message for reference in CURRENT_PAGE_REFERENCES
    )

    for index, page_id in enumerate(target_ids):
        page = PAGE_CATALOG[page_id]
        if index == 0 and current_page_id == page_id and current_page_question:
            lines.append(f"你現在看到的是「{page.title}」。")
        else:
            lines.append(f"「{page.title}」的用途是這樣：")
        lines.append(page.description)
        lines.append("這一頁你可以：")
        for item_index, feature in enumerate(page.features, start=1):
            lines.append(f"{item_index}. {feature}")
        lines.append(page.navigation_hint)
        if index != len(target_ids) - 1:
            lines.append("")
    return "\n".join(lines)


def _build_all_pages_reply(current_page_id: str | None) -> str:
    order = ("landing", "login", "home", "my_services", "assistant", "service_form", "request_detail")
    lines = ["目前應用程式主要頁面有："]
    for page_id in order:
        page = PAGE_CATALOG[page_id]
        suffix = "（你目前在這一頁）" if current_page_id == page_id else ""
        lines.append(f"- {page.title}：{page.description}{suffix}")
    return "\n".join(lines)
