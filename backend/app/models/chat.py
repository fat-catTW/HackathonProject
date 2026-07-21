from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=8)
    message: str = Field(min_length=1, max_length=1000)


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    service_id: str | None = None
    service_name: str | None = None
    collected_fields: dict = {}
    missing_fields: list[str] = []
    request_id: str | None = None
    status: str = "COLLECTING_INFORMATION"
