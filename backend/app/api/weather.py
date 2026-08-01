from fastapi import APIRouter, Depends

from ..auth.cognito import CurrentUser, get_current_user
from ..services import weather

router = APIRouter()


@router.get("/api/weather")
def get_weather(city: str | None = None, user: CurrentUser = Depends(get_current_user)):
    return weather.get_weather(city)
