"""服務所在地（台灣）的「現在」。

使用者說「禮拜三」「明天」指的是**他當下**的日期，而伺服器可能跑在 UTC
（Lambda／ECS 預設就是）。直接用 `date.today()` 的話，台灣時間 16:00 之後整整差一天，
「這禮拜三」就會被算成上一天對應的星期，填出來的日期整個錯掉。
"""
from contextvars import ContextVar
from datetime import date, datetime, timedelta, timezone

TZ = timezone(timedelta(hours=8))

WEEKDAY_NAMES_ZH = ("星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日")

# 這一次請求裡「使用者當下的日期」。前端每則訊息都會附上自己的本地日期，
# 使用者不在台灣（或裝置時區不同）時才不會用錯基準日推算「這禮拜三」。
_client_date: ContextVar[date | None] = ContextVar("client_date", default=None)


def use_client_date(value: str | date | None):
    """設定這次請求的使用者日期；回傳 token 供 reset 用（見 api/chat.py）。"""
    if isinstance(value, str):
        try:
            value = date.fromisoformat(value.strip())
        except ValueError:
            value = None
    return _client_date.set(value if isinstance(value, date) else None)


def reset_client_date(token) -> None:
    _client_date.reset(token)


def now() -> datetime:
    return datetime.now(TZ)


def today() -> date:
    """使用者當下的日期；沒帶就退回台灣時間（服務在台灣，不是伺服器所在時區）。"""
    return _client_date.get() or now().date()


def weekday_zh(value: date | None = None) -> str:
    return WEEKDAY_NAMES_ZH[(value or today()).weekday()]
