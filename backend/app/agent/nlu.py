"""規則式中文 NLU（Milestone 1 Mock LLM）。

Milestone 2 換成 Bedrock 後，這個模組仍保留作為：
1. 離線備援  2. 單元測試基準  3. 欄位後驗證（相對日期轉換等）
"""
from __future__ import annotations

import json
import re
from datetime import date, timedelta
from pathlib import Path

from ..services import delivery_catalog
from ..services.catalog import SERVICES
from ..services.restaurant_catalog import RESTAURANTS

# ---- 縣市行政區資料（來自命題縣市區域檔） ----
_REGIONS = json.loads(
    (Path(__file__).resolve().parent.parent / "data" / "tw_regions.json").read_text(encoding="utf-8")
)
COUNTY_NAMES = [c["name"] for c in _REGIONS["counties"]]
# 台/臺 互換
_COUNTY_ALT = {n.replace("台", "臺"): n for n in COUNTY_NAMES if "台" in n}

_CN_NUM = {"一": 1, "兩": 2, "二": 2, "三": 3, "四": 4, "五": 5,
           "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}

_CN_MINUTE = {
    "零": 0,
    "五": 5,
    "十分": 10,
    "十": 10,
    "十五": 15,
    "二十": 20,
    "二十五": 25,
    "三十": 30,
    "三十五": 35,
    "四十": 40,
    "四十五": 45,
    "五十": 50,
    "五十五": 55,
}


def parse_quantity(text: str, unit_chars: str = "台臺部間") -> int | None:
    """擷取「兩台」「3 台」等數量。"""
    m = re.search(rf"([0-9]+|[{''.join(_CN_NUM)}])\s*[{unit_chars}]", text)
    if m:
        tok = m.group(1)
        return int(tok) if tok.isdigit() else _CN_NUM.get(tok)
    return None


def parse_number(text: str) -> int | None:
    m = re.search(rf"([0-9]+|[{''.join(_CN_NUM)}])", text)
    if m:
        tok = m.group(1)
        return int(tok) if tok.isdigit() else _CN_NUM.get(tok)
    return None


def parse_hours(text: str) -> int | None:
    m = re.search(rf"([0-9]+|[{''.join(_CN_NUM)}])\s*(小時|個小時|hr|小時)", text)
    if m:
        tok = m.group(1)
        return int(tok) if tok.isdigit() else _CN_NUM.get(tok)
    return None


_WEEKDAYS = {"一": 0, "二": 1, "三": 2, "四": 3, "五": 4, "六": 5, "日": 6, "天": 6}


def parse_date(text: str, today: date | None = None) -> str | None:
    """相對日期 → ISO 日期字串（設計書 14.3：相對日期需轉成明確日期）。"""
    today = today or date.today()
    if "大後天" in text:
        return (today + timedelta(days=3)).isoformat()
    if "後天" in text:
        return (today + timedelta(days=2)).isoformat()
    if "明天" in text or "明日" in text:
        return (today + timedelta(days=1)).isoformat()
    if "今天" in text or "今日" in text:
        return today.isoformat()

    m = re.search(r"(下)?(?:週|周|星期|禮拜)([一二三四五六日天])", text)
    if m:
        target = _WEEKDAYS[m.group(2)]
        delta = (target - today.weekday()) % 7
        if delta == 0:
            delta = 7
        if m.group(1):  # 「下週X」再加一週
            delta += 7 if delta <= 7 else 0
        return (today + timedelta(days=delta)).isoformat()

    m = re.search(r"(\d{1,2})\s*月\s*(\d{1,2})\s*[日號]", text)
    if m:
        month, day = int(m.group(1)), int(m.group(2))
        year = today.year + (1 if (month, day) < (today.month, today.day) else 0)
        try:
            return date(year, month, day).isoformat()
        except ValueError:
            return None
    m = re.search(r"(20\d{2})[-/](\d{1,2})[-/](\d{1,2})", text)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3))).isoformat()
        except ValueError:
            return None
    return None


def parse_time_slot(text: str) -> str | None:
    if re.search(r"早上|上午|一早|早班", text):
        return "MORNING"
    if re.search(r"下午|中午過後|午後", text):
        return "AFTERNOON"
    if re.search(r"晚上|傍晚|晚間|夜間", text):
        return "EVENING"
    return None


def parse_service_time(text: str) -> str | None:
    m = re.search(r"\b([01]?\d|2[0-3]):([0-5]\d)\b", text)
    if m:
        return f"{int(m.group(1)):02d}:{int(m.group(2)):02d}"

    m = re.search(r"(上午|早上|中午|下午|晚上|傍晚|晚間|夜間)?\s*([0-9]{1,2}|[一二三四五六七八九十兩]+)\s*點(?:\s*([0-9]{1,2}|半|[一二三四五六七八九十兩零]+)\s*分?)?", text)
    if not m:
        return None

    period = m.group(1) or ""
    hour_token = m.group(2)
    minute_token = m.group(3)

    hour = int(hour_token) if hour_token.isdigit() else _CN_NUM.get(hour_token)
    if hour is None:
        return None

    minute = 0
    if minute_token:
        if minute_token == "半":
            minute = 30
        elif minute_token.isdigit():
            minute = int(minute_token)
        else:
            minute = _CN_MINUTE.get(minute_token, 0)

    if minute > 59:
        return None

    if period in ("下午", "晚上", "傍晚", "晚間", "夜間") and hour < 12:
        hour += 12
    elif period == "中午":
        if hour < 11:
            hour += 12
    elif period in ("上午", "早上") and hour == 12:
        hour = 0

    if hour > 23:
        return None

    return f"{hour:02d}:{minute:02d}"


def parse_machine_type(text: str) -> str | None:
    if "滾筒" in text:
        return "FRONT_LOAD"
    if "直立" in text:
        return "TOP_LOAD"
    return None


def parse_restaurant(text: str) -> str | None:
    """依餐廳全名或分店關鍵字比對，回傳 restaurant_id。"""
    for restaurant in RESTAURANTS:
        if restaurant["name"] in text:
            return restaurant["id"]
    for restaurant in RESTAURANTS:
        branch = restaurant["name"].split(" ")[-1] if " " in restaurant["name"] else restaurant["name"]
        if branch and branch in text:
            return restaurant["id"]
    return None


def parse_delivery_store(text: str) -> str | None:
    """依店家名稱比對文字，回傳 store_id。"""
    for store in delivery_catalog.list_stores():
        if store["name"] in text:
            return store["id"]
    return None


def parse_menu_item(text: str, store_id: str) -> dict | None:
    """依指定店家菜單比對品項名稱，並擷取數量（找不到數量時預設 1 份）。"""
    store = delivery_catalog.get_store(store_id)
    if not store:
        return None
    for item in store["menu"]:
        if item["title"] in text:
            quantity = parse_quantity(text, unit_chars="份個杯碗") or 1
            return {
                "id": item["id"],
                "title": item["title"],
                "price": item["price"],
                "quantity": quantity,
            }
    return None


def parse_meal_slot(text: str) -> str | None:
    """訂位餐期：午餐／晚餐（與既有 parse_time_slot 的上午/下午/晚上不同語意，分開一個函式避免混用）。"""
    if re.search(r"午餐|中午|午飯", text):
        return "LUNCH"
    if re.search(r"晚餐|晚上|夜間|晚飯", text):
        return "DINNER"
    return None


def parse_option(text: str, options: list[str]) -> str | None:
    normalized = text.strip()
    for option in options:
        if option == normalized or option in normalized or normalized in option:
            return option
    return None


def parse_yes_no_option(text: str) -> str | None:
    if re.search(r"不要|不用|不需要|先不要", text):
        return "NO"
    if re.search(r"要|需要|加購|加買|好", text):
        return "YES"
    return None


def parse_pickup_method(text: str) -> str | None:
    if re.search(r"店到店|超商|7-11|7-eleven|7-ELEVEN", text, re.IGNORECASE):
        return "STORE_TO_STORE"
    if re.search(r"到府|宅配到府|到家|上門", text):
        return "HOME_PICKUP"
    return None


def parse_phone(text: str) -> str | None:
    m = re.search(r"09\d{2}[-\s]?\d{3}[-\s]?\d{3}", text)
    if m:
        return re.sub(r"[-\s]", "", m.group(0))
    m = re.search(r"0\d{1,2}[-\s]?\d{6,8}", text)
    return re.sub(r"[-\s]", "", m.group(0)) if m else None


def parse_address(text: str) -> str | None:
    """偵測含縣市名的地址片段（利用命題縣市區域檔）。"""
    norm = text
    for alt, std in _COUNTY_ALT.items():
        norm = norm.replace(alt, std)
    for county in COUNTY_NAMES:
        idx = norm.find(county)
        if idx >= 0:
            tail = norm[idx:]
            m = re.match(r"^[\u4e00-\u9fffA-Za-z0-9０-９\-之號樓巷弄路街段區鄉鎮市村里鄰]+", tail)
            addr = m.group(0) if m else county
            # 去掉結尾標點與贅字；若含「號/樓」則截到最後一個門牌單位
            addr = re.sub(r"[，。,\.、\s]+$", "", addr)
            m2 = re.search(r"^.*?(?:\d+\s*號(?:之\d+)?(?:\s*\d+\s*樓)?)", addr)
            if m2:
                addr = m2.group(0)
            if len(addr) >= len(county):
                return addr
    return None


def detect_service(text: str) -> tuple[str | None, list[dict]]:
    """回傳 (最佳 service_id, 候選列表)。以關鍵字出現次數與長度加權。"""
    scores: list[tuple[int, dict]] = []
    for s in SERVICES:
        if not s["enabled"]:
            continue
        score = 0
        # 沒列 keywords 的服務不參與關鍵字比對（例如 customer_support，只從 FAQ
        # 升級流程建立，不該被「我想…」這類自由輸入誤觸）。
        for kw in s.get("keywords", ()):
            if kw in text:
                score += len(kw)
        if score:
            scores.append((score, s))
    scores.sort(key=lambda x: -x[0])
    best = scores[0][1]["id"] if scores else None
    return best, [s for _, s in scores]


# ---- 欄位擷取 dispatcher ----
def extract_fields(service_id: str, fields: list[dict], text: str,
                   collected: dict) -> dict:
    """從一則訊息擷取尚未收集的欄位值，回傳新擷取到的 {field_id: value}。"""
    found: dict = {}
    for f in fields:
        fid = f["id"]
        if fid in collected:
            continue
        value = None
        if fid == "quantity":
            value = parse_quantity(text)
        elif fid == "antibacterial_film_quantity":
            value = parse_quantity(text, unit_chars="個片張") or parse_number(text)
        elif fid == "hours":
            value = parse_hours(text)
        elif fid == "preferred_date":
            value = parse_date(text)
        elif fid == "preferred_time_slot":
            value = parse_service_time(text)
        elif fid == "machine_type":
            value = parse_machine_type(text)
        elif fid == "pickup_method":
            value = parse_pickup_method(text)
        elif fid == "restaurant_id":
            value = parse_restaurant(text)
        elif fid == "time_slot":
            value = parse_meal_slot(text)
        elif fid == "repair_item":
            value = parse_option(text, f.get("options", []))
        elif fid == "air_conditioner_type":
            value = parse_option(text, f.get("options", []))
        elif fid == "cleaning_service_option":
            value = parse_option(text, f.get("options", []))
        elif fid == "antibacterial_film_addon":
            value = parse_yes_no_option(text)
        elif fid == "phone":
            value = parse_phone(text)
        elif fid == "address":
            value = parse_address(text)
        elif fid == "issue_description":
            # 問題描述：在被詢問時取整句；首句若含關鍵詞也直接取
            value = None
        if value is not None:
            found[fid] = value
    return found
