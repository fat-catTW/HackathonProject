"""廠商後台的「AI 需求摘要」：把一張冗長的諮詢單濃縮成一句話重點。

摘要在**建單當下**算好、跟著案件一起存進 DynamoDB，而不是廠商開明細頁時才臨時算：

1. 廠商後台一天要掃過一長串案件，明細頁不該為了一句話多等一次 Bedrock 來回；
2. 摘要是案件送出當下內容的快照。之後改 prompt、換模型，舊案件的摘要也不會跟著漂移，
   廠商今天看到的那句話跟他昨天接單時看到的是同一句。

**摘要裡不會有聯絡資訊。** 它以明文存在案件上、廠商一開頁就看得到，和
`contact_privacy` 那條「解密必留存取紀錄」的路徑是兩回事；因此組 prompt 前就先把
`CONTACT_FIELDS` 濾掉，姓名／電話／地址根本不會送進模型，也就不可能出現在摘要裡。
"""
from __future__ import annotations

from ..agent import llm
from . import catalog, contact_privacy
from .store import STORE

# 摘要顯示在明細頁標題卡的單行位置，太長就失去「一眼掃完」的意義。模型偶爾會多寫
# 幾個字，超出就在這裡截斷。
MAX_CHARS = 40

# 沒有摘要價值的欄位型別：檔案上傳只會拿到一串路徑或檔名。
_SKIPPED_TYPES = frozenset({"file"})


def _display(value) -> str:
    """欄位值的人話版本；選項代碼（MORNING…）換成中文標籤。"""
    if value in (None, ""):
        return ""
    if isinstance(value, (dict, list)):
        # 外送購物車那類結構化欄位不屬於諮詢單，交給呼叫端的服務自己處理。
        return ""
    return catalog.SELECT_LABELS.get(str(value), str(value))


def _fields_for_summary(service_id: str, form_data: dict) -> list[dict]:
    """要餵給模型的 (label, value)，依服務 schema 的欄位順序排列。

    順序取自 schema 而非 form_data：dict 的順序會隨表單頁與管家的填答路徑而不同，
    同一張單餵進去的內容順序不該影響摘要。
    """
    schema = catalog.get_service_schema(service_id) or {"fields": []}
    labels = {field["id"]: field.get("label", field["id"]) for field in schema["fields"]}
    skipped = {field["id"] for field in schema["fields"] if field.get("type") in _SKIPPED_TYPES}
    ordered = [key for key in labels if key in form_data] + [
        key for key in form_data if key not in labels
    ]

    fields = []
    for key in ordered:
        if key in contact_privacy.CONTACT_FIELDS or key in skipped:
            continue
        value = _display(form_data.get(key))
        if not value:
            continue
        fields.append({"label": labels.get(key, key), "value": value})
    return fields


def _clip(text: str) -> str:
    single_line = " ".join(text.split())
    if len(single_line) <= MAX_CHARS:
        return single_line
    return single_line[: MAX_CHARS - 1] + "…"


def _fallback(service_name: str, fields: list[dict]) -> str:
    """Bedrock 不可用時的機械版摘要：塞得下多少欄位就塞多少。

    寧可整項不寫也不從中間切斷——半截的「問題描述 廚房水管漏水一直」比乾脆跳過那一項
    更難讀。塞不下的欄位是跳過而不是就此打住：長長的問題描述常常排在很前面，一碰到它
    就收工的話，日期、時段這些短欄位會全部落空。
    """
    text = service_name
    for field in fields:
        candidate = f"{text}／{field['label']} {field['value']}"
        if len(candidate) <= MAX_CHARS:
            text = candidate
    return text


def build(service_id: str, form_data: dict) -> str:
    """這張單的一句話重點；沒有廠商會看到的服務回空字串，不必花一次 Bedrock。"""
    service = catalog.get_service(service_id)
    if not service or service.get("service_vendor_id") is None:
        return ""

    service_name = service["name"]
    try:
        fields = _fields_for_summary(service_id, form_data)
        if not fields:
            return service_name
        summary = llm.summarize_service_request(service_name, fields)
        return _clip(summary) if summary else _fallback(service_name, fields)
    except Exception:  # noqa: BLE001
        # 摘要是錦上添花，出什麼事都不能讓住戶送不出單；退回服務名稱至少不是空白。
        return service_name


def attach(actor_id: str, request_id: str, service_id: str, form_data: dict) -> str:
    """算好摘要並補寫到剛建立的案件上——管家送單走這條。

    管家送單時案件不一定是後端寫的：`AGENT_TOOL_MODE` 是 mcp／lambda 時，
    submit_service_request 由 Gateway 端的 Lambda 落地，後端只拿得到 request_id。
    因此摘要在送單成功之後補寫一次，不論工具模式怎麼換，廠商看到的都是建單當下
    算好的那句話。
    """
    summary = build(service_id, form_data)
    if not summary:
        return ""
    try:
        STORE.attach_ai_summary(actor_id, request_id, summary)
    except Exception:  # noqa: BLE001
        # 案件本體已經建好了，補不上摘要只是廠商少一行提示，不該讓送單回報失敗。
        pass
    return summary
