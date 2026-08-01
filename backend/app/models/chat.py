from pydantic import BaseModel, Field


class FormContext(BaseModel):
    """前端表單頁目前畫面上的內容。

    代操表單模式下，Agent 以畫面上的值為準（使用者可能自己先填了幾格，或在代操後
    又手動改過），所以每一次對話都會把目前的表單快照一起送上來。
    """

    service_id: str = Field(max_length=64)
    values: dict[str, str] = Field(default_factory=dict)


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=8)
    message: str = Field(min_length=1, max_length=1000)
    current_page_id: str | None = Field(default=None, max_length=64)
    form_context: FormContext | None = None
    # 使用者裝置上的今天（YYYY-MM-DD）。「這禮拜三」要用使用者當下的日期換算，
    # 不是伺服器的日期；沒帶時後端退回台灣時間。
    client_date: str | None = Field(default=None, max_length=10)


class FormUpdateRequest(BaseModel):
    session_id: str = Field(min_length=8)
    fields: dict = Field(default_factory=dict)


class FormAction(BaseModel):
    """要前端在表單上執行的一個動作（逐格高亮填入）。"""

    type: str = "fill"
    field_id: str
    label: str = ""
    value: str = ""
    display_value: str = ""
    note: str | None = None


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
    form_actions: list[FormAction] = []
    request_id: str | None = None
    status: str = "COLLECTING_INFORMATION"
    redirect_path: str | None = None
    redirect_requires_confirmation: bool = False
    clinic_recommendation: dict | None = None
    debug_trace: dict = {}
    task_cards: list[dict] | None = None
    restaurant_cards: list[dict] | None = None
    share_text: str | None = None
