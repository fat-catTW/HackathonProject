"""每日問候卡 API。

規格上這張卡是「每天早上 7 點自動推播」的內容。真正的排程與 Web Push 還沒做，
所以這裡先提供一支「今天的卡片」查詢端點，由前端在進場時取用；日後補上排程時，
排程程式呼叫的也是同一份 build_daily_greeting，卡片內容不會兩套。

日期跟 /api/chat 一樣接受前端帶上自己的本地日期（client_date）：使用者裝置時區
不同時，「今天的行程」才不會用伺服器的今天去比對。
"""
from fastapi import APIRouter, Depends, Query

from ..auth.cognito import CurrentUser, get_current_user
from ..services import clock, daily_greeting

router = APIRouter()


@router.get("/api/daily-greeting")
def get_daily_greeting(
    client_date: str | None = Query(default=None, description="使用者裝置的本地日期 YYYY-MM-DD"),
    user: CurrentUser = Depends(get_current_user),
):
    date_token = clock.use_client_date(client_date)
    try:
        return daily_greeting.build_daily_greeting(user.sub, user.name)
    finally:
        clock.reset_client_date(date_token)
