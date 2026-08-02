"""每日問候卡：管家每天早上主動整理的一張卡片。

「每天早上 7 點主動關心你」其實是兩件事：**什麼時候送到眼前**（排程／推播）
與**卡片上寫什麼**。這支只負責後者，而且內容一律從使用者自己的案件算出來
——今天的行程、還沒送出的草稿、進行中的案件、剛完成待回饋的服務——不是
一句寫死的罐頭問候。

拆成這樣，Demo 時前端一開 App 就打這支拿卡片；日後真的接上 cron + Web Push
在 07:00 推同一份內容時，要補的只有排程那一半，這支不用改。
"""
from __future__ import annotations

from datetime import date, datetime

from . import clock
from .statuses import STATUS_LABELS
from .store import STORE

# 卡片對外宣告的推播時間。真正的排程還沒做，前端拿它顯示「每天 07:00 為你整理」，
# 之後接上 cron 時兩邊讀同一個常數，不會各寫各的時間。
PUSH_TIME = "07:00"

MAX_ITEMS = 3
MAX_SUGGESTIONS = 3
# 行程只看未來幾天內的：再遠的事今天提醒也沒有意義，只會把版面塞滿。
UPCOMING_DAYS = 3
# 服務完成後幾天內還值得在卡片上問一句「還順利嗎」。
FOLLOWUP_DAYS = 2

# 已結案的狀態不會再有進度，不必每天再提醒一次。
CLOSED_STATUSES = frozenset({"COMPLETED", "CANCELLED", "REJECTED", "FAILED", "VERIFIED"})
# 只有住戶本人能推進的狀態；卡片上優先級最高，因為擺著不動它就永遠不會動。
NEEDS_USER_STATUSES = frozenset({"DRAFT", "AWAITING_USER_CONFIRMATION"})

# 提醒在卡片上的先後順序：今天就要發生的最急，其次是只有住戶本人能推進的草稿。
_KIND_PRIORITY = ("today", "action_needed", "upcoming", "in_progress", "followup")
# 這兩種提醒有排定時間，同一區塊內要由近到遠排；其餘維持案件的新到舊。
_SCHEDULED_KINDS = ("today", "upcoming")

# 每則提醒對應一句管家的開場白，取自最優先那一則。
_KIND_MESSAGES = {
    "today": "今天有安排，出門前記得再確認一次時間。",
    "action_needed": "有一筆需求還沒送出，要我幫你接著完成嗎？",
    "upcoming": "這幾天的安排先讓你有個底，有變動隨時跟我說。",
    "in_progress": "案件都在跑，一有進度我就告訴你。",
    "followup": "上次的服務完成了，還順利嗎？",
}
_EMPTY_MESSAGE = "今天沒有待辦，想到什麼隨時跟我說，我幫你安排。"

# 建議池。每個服務有兩套講法：first 是「還沒用過／隨口提議」，repeat 是
# 「你上次用過，要不要再來一次」。不共用一句「再約一次{服務名}」樣板是因為
# 中文動詞挑對象——外送是「叫」、商城是「逛」、包裹是「寄」，硬套「再約一次
# 商城購物」會立刻露餡。
_SUGGESTION_POOL: tuple[dict, ...] = (
    {
        "service_id": "air_conditioner_cleaning",
        "label": "預約冷氣清洗", "prompt": "我想預約冷氣清洗",
        "repeat_label": "再約一次冷氣清洗", "repeat_prompt": "我想再預約一次冷氣清洗",
    },
    {
        "service_id": "home_cleaning",
        "label": "安排居家清潔", "prompt": "我想安排居家清潔",
        "repeat_label": "再約一次居家清潔", "repeat_prompt": "我想再安排一次居家清潔",
    },
    {
        "service_id": "restaurant_reservation",
        "label": "訂今晚的餐廳", "prompt": "我想訂今晚的餐廳",
        "repeat_label": "再訂一次餐廳", "repeat_prompt": "我想再訂一次餐廳",
    },
    {
        "service_id": "plumbing_repair",
        "label": "報修家裡水電", "prompt": "家裡水電有點狀況，想找師傅來看",
        "repeat_label": "再找一次水電師傅", "repeat_prompt": "我想再找一次水電師傅",
    },
    {
        "service_id": "food_delivery",
        "label": "叫份外送", "prompt": "我想叫外送",
        "repeat_label": "再叫一次外送", "repeat_prompt": "我想再叫一次外送",
    },
    {
        "service_id": "washing_machine_cleaning",
        "label": "洗衣機該洗了", "prompt": "我想預約洗衣機清洗",
        "repeat_label": "再約一次洗衣機清洗", "repeat_prompt": "我想再預約一次洗衣機清洗",
    },
    {
        "service_id": "health_product_recommendation",
        "label": "找點健康好物", "prompt": "幫我推薦適合的健康商品",
        "repeat_label": "再看一次健康推薦", "repeat_prompt": "幫我再推薦一次健康商品",
    },
    {
        "service_id": "package_shipping",
        "label": "寄一件包裹", "prompt": "我想寄包裹",
        "repeat_label": "再寄一件包裹", "repeat_prompt": "我想再寄一件包裹",
    },
    {
        "service_id": "shop_purchase",
        "label": "逛逛商城", "prompt": "我想逛商城買東西",
        "repeat_label": "再逛一次商城", "repeat_prompt": "我想再去商城買東西",
    },
)
# 只有列在池子裡的服務才有「再來一次」的講法；客服諮詢這類沒有重複語意的不列入。
_POOL_BY_SERVICE = {entry["service_id"]: entry for entry in _SUGGESTION_POOL}


def _period(hour: int) -> tuple[str, str]:
    """時段代號與招呼語。卡片是給早上 7 點看的，但 Demo 隨時會開，招呼語照實際時間走。"""
    if 5 <= hour < 11:
        return "morning", "早安"
    if 11 <= hour < 17:
        return "afternoon", "午安"
    if 17 <= hour < 23:
        return "evening", "晚安"
    return "night", "夜深了"


def _status_text(status: str) -> str:
    """狀態中文標籤；外送單的 PENDING 等未列管狀態不要把英文代號印在卡片上。"""
    return STATUS_LABELS.get(status, "處理中")


def _clock_text(value) -> str | None:
    """把欄位值當成 HH:MM 時刻讀。

    訂位的 time_slot 是 LUNCH／DINNER 這種時段代號而不是時刻，直接印在卡片上
    會變成「今天 DINNER 的餐廳訂位」，所以這裡只認真正的 HH:MM。
    """
    if not isinstance(value, str):
        return None
    text = value.strip()
    if len(text) == 5 and text[2] == ":" and text[:2].isdigit() and text[3:].isdigit():
        return text
    return None


def _scheduled_at(request: dict) -> tuple[date | None, str | None]:
    """案件排定的日期與時刻；各服務把它放在不同欄位，這裡統一收斂。"""
    service_time = request.get("service_time")
    if isinstance(service_time, str):
        try:
            parsed = datetime.fromisoformat(service_time)
        except ValueError:
            parsed = None
        if parsed is not None:
            return parsed.date(), f"{parsed:%H:%M}"

    form = request.get("form_data")
    form = form if isinstance(form, dict) else {}
    raw_date = form.get("reserved_date") or form.get("preferred_date")
    if not isinstance(raw_date, str):
        return None, None
    try:
        scheduled = date.fromisoformat(raw_date.strip())
    except ValueError:
        return None, None
    at = _clock_text(form.get("specific_time")) or _clock_text(form.get("preferred_time_slot"))
    return scheduled, at


def _merchant_name(request: dict) -> str | None:
    """訂位／外送單上的店家名稱，讓提醒具體到「哪一家」而不只是服務類別。"""
    order_items = request.get("order_items")
    if not isinstance(order_items, dict):
        return None
    store = order_items.get("store")
    if isinstance(store, dict) and store.get("name"):
        return str(store["name"])
    if order_items.get("restaurant_name"):
        return str(order_items["restaurant_name"])
    return None


def _day_label(scheduled: date, today: date) -> str:
    delta = (scheduled - today).days
    if delta == 0:
        return "今天"
    if delta == 1:
        return "明天"
    if delta == 2:
        return "後天"
    return f"{scheduled.month}/{scheduled.day}"


def _last_touched_date(request: dict) -> date | None:
    """案件最後一次異動的日期。狀態變更都會走 save_request 蓋掉 updated_at，
    因此對已完工的案件來說，這就是「哪天完工的」。"""
    raw = request.get("updated_at") or request.get("created_at")
    if not isinstance(raw, str):
        return None
    try:
        return datetime.fromisoformat(raw).date()
    except ValueError:
        return None


def _build_item(request: dict, today: date) -> dict | None:
    """把一筆案件轉成卡片上的一則提醒；今天不值得提的回 None。"""
    status = request.get("status", "")
    service_name = request.get("service_name") or "服務"
    merchant = _merchant_name(request)
    scheduled, at = _scheduled_at(request)
    base = {
        "id": request.get("request_id", ""),
        "service_id": request.get("service_id", ""),
        "action_path": f"/requests/{request.get('request_id', '')}",
    }

    if status not in CLOSED_STATUSES and scheduled is not None:
        delta = (scheduled - today).days
        if 0 <= delta <= UPCOMING_DAYS:
            day = _day_label(scheduled, today)
            return base | {
                "kind": "today" if delta == 0 else "upcoming",
                # 同一天沒寫明時刻的排在有時刻的後面：「今天 09:00 的清潔」比
                # 「今天的冷氣清洗」明確，該先讓使用者看到。
                "sort_key": (scheduled.isoformat(), at or "99:99"),
                "title": f"{day} {at} {service_name}" if at else f"{day}的{service_name}",
                "detail": f"{merchant} · {_status_text(status)}" if merchant else _status_text(status),
                "action_label": "查看詳情",
            }

    if status in NEEDS_USER_STATUSES:
        return base | {
            "kind": "action_needed",
            "sort_key": (request.get("created_at", ""), ""),
            "title": f"還沒送出的{service_name}",
            "detail": "填到一半的需求還留著，要接著完成嗎？",
            "action_label": "繼續完成",
        }

    if status == "COMPLETED":
        completed_on = _last_touched_date(request)
        if completed_on is not None and 0 <= (today - completed_on).days <= FOLLOWUP_DAYS:
            return base | {
                "kind": "followup",
                "sort_key": (completed_on.isoformat(), ""),
                "title": f"{service_name}已完成",
                "detail": "有任何不滿意都可以跟我說，我幫你處理。",
                "action_label": "查看紀錄",
            }
        return None

    if status in CLOSED_STATUSES:
        return None

    return base | {
        "kind": "in_progress",
        "sort_key": (request.get("updated_at", ""), ""),
        "title": service_name,
        "detail": _status_text(status),
        "action_label": "查看進度",
    }


def _build_items(requests: list[dict], today: date) -> list[dict]:
    """組出今天的提醒清單，最多 MAX_ITEMS 則。

    requests 由 STORE.list_requests 給出、已是建立時間新到舊，這裡只需要把有排定
    時間的那兩種區塊改成由近到遠——「明天的訂位」排在「後天的清潔」前面才合理。
    """
    by_kind: dict[str, list[dict]] = {}
    for request in requests:
        item = _build_item(request, today)
        if item:
            by_kind.setdefault(item["kind"], []).append(item)
    for kind in _SCHEDULED_KINDS:
        by_kind.get(kind, []).sort(key=lambda item: item["sort_key"])
    ordered = [item for kind in _KIND_PRIORITY for item in by_kind.get(kind, [])]
    return [{k: v for k, v in item.items() if k != "sort_key"} for item in ordered[:MAX_ITEMS]]


def _build_suggestions(requests: list[dict], items: list[dict], today: date) -> list[dict]:
    """先個人化、再輪替補滿。

    第一則優先接續使用者真的用過的服務（「再約一次冷氣清洗」），其餘從建議池
    依日期輪替補滿，讓每天翻開卡片看到的不會一模一樣。已經出現在今天提醒裡的
    服務一律跳過——同一件事沒必要在同一張卡上講兩次。
    """
    busy = {item["service_id"] for item in items if item.get("service_id")}
    suggestions: list[dict] = []

    def _entry(service_id: str, repeat: bool) -> dict:
        pool = _POOL_BY_SERVICE[service_id]
        prefix = "repeat_" if repeat else ""
        return {
            "service_id": service_id,
            "label": pool[f"{prefix}label"],
            "prompt": pool[f"{prefix}prompt"],
        }

    for request in requests:  # list_requests 已依建立時間新到舊排序
        service_id = request.get("service_id", "")
        if service_id in busy or service_id not in _POOL_BY_SERVICE:
            continue
        suggestions.append(_entry(service_id, repeat=True))
        busy.add(service_id)
        break

    offset = today.toordinal() % len(_SUGGESTION_POOL)
    for index in range(len(_SUGGESTION_POOL)):
        if len(suggestions) >= MAX_SUGGESTIONS:
            break
        service_id = _SUGGESTION_POOL[(offset + index) % len(_SUGGESTION_POOL)]["service_id"]
        if service_id in busy:
            continue
        suggestions.append(_entry(service_id, repeat=False))
        busy.add(service_id)

    return suggestions


def build_daily_greeting(actor_id: str, display_name: str, *, now: datetime | None = None) -> dict:
    """組出這位使用者今天的問候卡。"""
    moment = now or clock.now()
    today = clock.today() if now is None else moment.date()
    period, greeting = _period(moment.hour)

    requests = STORE.list_requests(actor_id)
    items = _build_items(requests, today)
    name = (display_name or "").strip()

    return {
        "date": today.isoformat(),
        "weekday": clock.weekday_zh(today),
        "date_label": f"{today.month} 月 {today.day} 日 {clock.weekday_zh(today)}",
        "push_time": PUSH_TIME,
        "period": period,
        "greeting": f"{greeting}，{name}" if name else greeting,
        "headline": f"今天有 {len(items)} 件事要提醒你" if items else "今天沒有待辦，輕鬆一點",
        "message": _KIND_MESSAGES[items[0]["kind"]] if items else _EMPTY_MESSAGE,
        "items": items,
        "suggestions": _build_suggestions(requests, items, today),
    }
