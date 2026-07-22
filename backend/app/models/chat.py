from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=8)
    message: str = Field(min_length=1, max_length=1000)


class FormUpdateRequest(BaseModel):
    session_id: str = Field(min_length=8)
    fields: dict = Field(default_factory=dict)


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    service_id: str | None = None
    service_name: str | None = None
    collected_fields: dict = {}
    missing_fields: list[str] = []
    form_schema: dict | None = None
    form_draft: dict | None = None
    active_field: str | None = None
    request_id: str | None = None
    status: str = "COLLECTING_INFORMATION"
