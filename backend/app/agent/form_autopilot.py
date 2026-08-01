"""AI 代操表單（form autopilot）。

`page_help` 只回答「這個功能在哪一頁」；這個模組負責再往前一步：使用者說「幫我填」時，
由 Agent 算出要寫進**前端表單**的欄位值，並輸出一串 UI 動作（form_actions），
讓 ServiceFormPage 逐格高亮、逐格填入。

這裡只放「不需要 agent state 也能決定」的純函式（意圖判斷、頁面 ↔ 服務對應、
動作組裝、回覆文案）；真正要動到 collected_fields / service_schema 的部分留在
agent.py，避免兩邊都在改同一份狀態。
"""
from __future__ import annotations

from collections.abc import Callable, Iterable

FORM_PAGE_PREFIX = "service_form_"

# 這些服務在前端有各自的專屬流程頁（見 frontend/src/App.tsx 的路由），不是通用的
# ServiceFormPage，畫面上沒有一格一格的表單欄位可以代填，所以不開放代操。
DEDICATED_FLOW_SERVICES = frozenset(
    {
        "restaurant_reservation",
        "food_delivery",
        "health_product_recommendation",
        "shop_purchase",
    }
)

AUTOFILL_HINTS = (
    "幫我填",
    "幫忙填",
    "幫我代填",
    "幫我帶入",
    "幫我打",
    "幫我輸入",
    "幫我寫",
    "代填",
    "替我填",
    "你來填",
    "直接填",
    "自動填",
    "自動帶入",
    "幫我把表單填",
    "幫我把資料填",
)

# 拿掉指令字樣後兩端要一起清掉的標點與空白。
_AUTOFILL_TRIM_CHARS = " 　，。、,.!！?？~～：:；;"

# 帶這些字代表使用者是在「問」而不是在「叫我做」。
# 例：「可以用語音幫我填嗎」問的是功能，該回頁面說明；「用語音幫我填，兩台壁掛式冷氣」是要現在填。
QUESTION_MARKERS = (
    "嗎",
    "呢",
    "?",
    "？",
    "可不可以",
    "能不能",
    "是不是",
    "有沒有",
    "怎麼",
    "如何",
)


def page_service_id(current_page_id: str | None) -> str | None:
    """`service_form_air_conditioner_cleaning` -> `air_conditioner_cleaning`。"""
    page_id = (current_page_id or "").strip()
    if not page_id.startswith(FORM_PAGE_PREFIX):
        return None
    return page_id[len(FORM_PAGE_PREFIX) :] or None


def supports_autopilot(service_id: str | None) -> bool:
    return bool(service_id) and service_id not in DEDICATED_FLOW_SERVICES


def looks_like_autofill_request(message: str) -> bool:
    text = (message or "").strip()
    return bool(text) and any(hint in text for hint in AUTOFILL_HINTS)


def strip_autofill_hints(message: str) -> str:
    """把「幫我填」這類指令字樣拿掉，只留使用者真正交代的內容。

    「幫我填，廚房水管漏水」的問題描述是「廚房水管漏水」——指令本身不是描述，
    填進去廠商看到的就是一句「幫我填」。
    """
    text = (message or "").strip()
    for hint in AUTOFILL_HINTS:
        text = text.replace(hint, "")
    return text.strip(_AUTOFILL_TRIM_CHARS)


def looks_like_question(message: str) -> bool:
    text = (message or "").strip()
    return bool(text) and any(marker in text for marker in QUESTION_MARKERS)


def _input_value(value) -> str | None:
    """把 collected_fields 的值轉成可以直接寫進 <input> 的字串。

    購物車（goods）這種清單型欄位在前端沒有對應的輸入框，回 None 代表略過。
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return str(int(value)) if float(value).is_integer() else str(value)
    return None


def build_actions(
    fields: Iterable[dict],
    before: dict,
    after: dict,
    *,
    label_of: Callable[[str], str],
    display_of: Callable[[str, object], str],
    is_visible: Callable[[dict], bool] | None = None,
    notes: dict | None = None,
) -> list[dict]:
    """把「這一輪 collected_fields 的變動」轉成前端要執行的 UI 動作。

    只輸出有變動的欄位：使用者自己在表單打的字會先同步進 collected_fields，
    因此不會被當成 AI 的動作再回填一次（避免打字打到一半被覆蓋）。
    """
    actions: list[dict] = []
    for field in fields:
        field_id = field.get("id")
        if not field_id:
            continue
        if is_visible and not is_visible(field):
            continue

        old_value = before.get(field_id)
        new_value = after.get(field_id)
        if old_value == new_value:
            continue

        if field_id not in after:
            actions.append(
                {
                    "type": "clear",
                    "field_id": field_id,
                    "label": label_of(field_id),
                    "value": "",
                    "display_value": "",
                    "note": None,
                }
            )
            continue

        value = _input_value(new_value)
        if value is None:
            continue

        actions.append(
            {
                "type": "fill",
                "field_id": field_id,
                "label": label_of(field_id),
                "value": value,
                "display_value": display_of(field_id, new_value),
                "note": (notes or {}).get(field_id),
            }
        )
    return actions


def compose_reply(
    *,
    service_title: str,
    actions: list[dict],
    missing_label: str = "",
    missing_question: str = "",
    redirecting: bool = False,
) -> str:
    """代操模式的回覆一律用固定文案組裝，不交給 LLM 重寫。

    這段話要和畫面上正在跑的 form_actions 完全對得起來（填了哪幾格、值是什麼），
    交給模型改寫容易講出和實際動作不一致的內容。
    """
    filled = [action for action in actions if action["type"] == "fill"]
    lines: list[str] = []

    if redirecting:
        lines.append(f"好，我帶你到「{service_title}」，直接幫你填。")
    else:
        lines.append(f"好，我直接幫你填「{service_title}」。")

    if filled:
        lines.append("已經幫你填好這幾格：")
        for action in filled:
            note = f"（{action['note']}）" if action.get("note") else ""
            lines.append(f"・{action['label']}：{action['display_value']}{note}")
    else:
        lines.append("目前還沒有可以直接帶入的資料。")

    if missing_label:
        lines.append(f"還缺「{missing_label}」。{missing_question}")
    else:
        lines.append("表單已經填完了，你檢查一下，沒問題就按「送出服務需求」，或直接跟我說「送出」我幫你送。")

    lines.append("想改哪一格直接告訴我，我會幫你改掉。")
    return "\n".join(lines)
