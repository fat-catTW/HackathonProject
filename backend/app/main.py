"""FastAPI 進入點。"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import auth, chat, requests, sessions
from .config import get_settings

app = FastAPI(title=get_settings().app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(sessions.router)
app.include_router(chat.router)
app.include_router(requests.router)


@app.get("/health")
def health():
    return {"status": "ok", "mock": get_settings().use_mock}
