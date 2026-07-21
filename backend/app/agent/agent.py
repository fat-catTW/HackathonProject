"""Agent 核心狀態機（設計書 §14 Decision Flow 的忠實實作）。

行為規則（14.3）：
- 一次只問一個主要問題
- 不重複詢問已取得資料
- 不自行猜測地址/電話/日期（長期記憶地址需經使用者同意才套用）
- 相對日期轉明確日期（nlu.parse_date）
- 提交前必須顯示摘要並取得確認
- Tool 錯誤不得假裝成功
"""
from __future__ import annotations

import re

from ..services import catalog
from ..services.store import STORE, now_iso
from . import nlu, tools

CONFIRM_WORDS = ("確認", "沒問題", "可以", "好", "對", "是", "OK", "ok", "送出", "正確")
DENY_WORDS = ("不要", "不用", "取消", "修改", "不對", "換", "不")


def _is_yes(text: str) -> bool:
    t = text.strip()
    return any(t.startswith(w) or t == w for w in CONFIRM_WORDS) and not _is_no(t)


def _is_no(text: str) -> bool:
    t = text.strip()
    return any(t.startswith(w) for w in DENY_WORDS)


def _field_display(fid: str, value, fields: list[dict]) -> str:
    f = next((x for x in fields if x["id"] == fid), None)
    label = f["label"] if f else fid
    if isinstance(value, str) and value in catalog.SELECT_LABELS:
        value = catalog.SELECT_LABELS[value]
    unit = ""
    if fid == "quantity":
        unit = " 台"
    elif fid == "hours":
        unit = " 小時"
    return f"{label}：{value}{unit}"


def _summary(state: dict) -> str:
    fields = state["service_schema"]["fields"]
    lines = [f"請確認以下申請內容：", f"服務：{state['service_name']}"]
    for f in fields:
        if f["id"] in state["collected_fields"]:
            lines.append(_field_display(f["id"], state["collected_fields"][f["id"]], fields))
    lines.append("")
    lines.append("內容正確嗎？回覆「確認」即送出，或告訴我要修改的項目。")
    return "\n".join(lines)


def _next_question(state: dict) -> str:
    fields = state["service_schema"]["fields"]
    fid = state["missing_fields"][0]
    f = next(x for x in fields if x["id"] == fid)
    return f.get("question") or f"請提供{f['label']}。"


def _recompute_missing(state: dict) -> None:
    fields = state["service_schema"]["fields"]
    state["missing_fields"] = [
        f["id"] for f in fields
        if f.get("required") and f["id"] not in state["collected_fields"]
    ]


def new_state() -> dict:
    return {
        "service_id": None,
        "service_name": None,
        "service_schema": None,
        "collected_fields": {},
        "missing_fields": [],
        "awaiting_confirmation": False,
        "pending_pref_field": None,   # 正在詢問是否套用長期記憶的欄位
        "pending_pref_value": None,
        "request_id": None,
        "status": "COLLECTING_INFORMATION",
    }


def handle_message(actor_id: str, session_id: str, state: dict, message: str) -> dict:
    """處理一則使用者訊息，回傳 {reply, state}。"""
    text = message.strip()

    # ---- 0. 已送出的案件 ----
    if state.get("request_id"):
        return _reply(state, "此案件已建立完成。您可以回到首頁查看案件狀態，或開啟新需求。")

    # ---- 1. 長期記憶偏好詢問中 ----
    if state.get("pending_pref_field"):
        fid = state["pending_pref_field"]
        if _is_yes(text):
            state["collected_fields"][fid] = state["pending_pref_value"]
        else:
            # 使用者拒絕或直接給了新值 → 嘗試從訊息擷取
            found = nlu.extract_fields(
                state["service_id"], state["service_schema"]["fields"], text,
                {k: v for k, v in state["collected_fields"].items()})
            if fid in found:
                state["collected_fields"][fid] = found[fid]
        state["pending_pref_field"] = None
        state["pending_pref_value"] = None
        _recompute_missing(state)
        return _continue_collection(actor_id, state, text)

    # ---- 2. 確認階段 ----
    if state["awaiting_confirmation"]:
        if _is_yes(text):
            return _submit(actor_id, session_id, state)
        if _is_no(text) or True:
            # 嘗試視為修改指令：重新擷取欄位
            fields = state["service_schema"]["fields"]
            override = nlu.extract_fields(state["service_id"], fields, text, {})
            if override:
                state["collected_fields"].update(override)
                _recompute_missing(state)
                if not state["missing_fields"]:
                    return _reply(state, _summary(state))
                state["awaiting_confirmation"] = False
                return _reply(state, _next_question(state))
            state["awaiting_confirmation"] = False
            return _reply(state, "好的，請告訴我要修改哪一項？例如「日期改成後天」或「地址改成⋯⋯」。")

    # ---- 3. 尚未確認服務類型 ----
    if not state["service_id"]:
        result = tools.call("list_services", {})
        if not result.get("success", True):
            return _reply(state, "抱歉，目前無法取得服務列表，請稍後再試。")
        best, candidates = nlu.detect_service(text)
        if not best:
            names = "、".join(s["name"] for s in result["services"])
            return _reply(state, f"我目前可以協助的服務有：{names}。請告訴我您需要哪一項？")
        service = catalog.get_service(best)
        schema_result = tools.call("get_service_schema", {"service_id": best})
        if not schema_result.get("success", True):
            return _reply(state, "抱歉，目前無法取得此服務的表單，請稍後再試。")
        state["service_id"] = best
        state["service_name"] = service["name"]
        state["service_schema"] = {"fields": schema_result["fields"]}
        _recompute_missing(state)

    # ---- 4. 從訊息擷取欄位 ----
    fields = state["service_schema"]["fields"]
    found = nlu.extract_fields(state["service_id"], fields, text, state["collected_fields"])

    # 問題描述：若正在等此欄位且訊息非空，取整句
    if state["missing_fields"] and state["missing_fields"][0] == "issue_description" \
            and "issue_description" not in found and len(text) >= 2:
        found["issue_description"] = text
    elif "issue_description" in [f["id"] for f in fields] \
            and "issue_description" not in state["collected_fields"]:
        # 首句含具體問題（漏水、跳電…）直接取
        if re.search(r"漏水|不通|堵塞|跳電|不亮|壞了|故障|沒電|漏電", text):
            found.setdefault("issue_description", text)

    state["collected_fields"].update(found)
    _recompute_missing(state)

    return _continue_collection(actor_id, state, text)


def _continue_collection(actor_id: str, state: dict, text: str) -> dict:
    # ---- 5. 長期記憶：地址 / 電話 / 偏好時段主動建議（設計書 Demo 3） ----
    prefs = STORE.get_preferences(actor_id)
    for fid, pref_key, ask in (
        ("address", "last_address", "要使用您上次的服務地址「{v}」嗎？"),
        ("phone", "last_phone", "聯絡電話要使用上次留的 {v} 嗎？"),
        ("preferred_time_slot", "preferred_time_slot", "要安排在您偏好的{v}時段嗎？"),
    ):
        if fid in state["missing_fields"] and prefs.get(pref_key) \
                and state["missing_fields"][0] == fid:
            v = prefs[pref_key]
            shown = catalog.SELECT_LABELS.get(v, v)
            state["pending_pref_field"] = fid
            state["pending_pref_value"] = v
            return _reply(state, ask.format(v=shown))

    # ---- 6. 缺欄位 → 問下一題；齊了 → 顯示摘要 ----
    if state["missing_fields"]:
        return _reply(state, _next_question(state))

    state["awaiting_confirmation"] = True
    state["status"] = "AWAITING_USER_CONFIRMATION"
    return _reply(state, _summary(state))


def _submit(actor_id: str, session_id: str, state: dict) -> dict:
    result = tools.call("submit_service_request", {
        "service_id": state["service_id"],
        "session_id": session_id,
        "actor_id": actor_id,  # 實際部署時由 Gateway/Lambda 已驗證身分注入
        "payload": dict(state["collected_fields"]),
    })
    if not result.get("success"):
        # 14.3：Tool 錯誤不得假裝成功
        msg = result.get("error", {}).get("message", "系統暫時無法送出")
        return _reply(state, f"抱歉，目前無法送出申請（{msg}）。您的資料已保留，稍後可再試一次。")

    state["request_id"] = result["request_id"]
    state["status"] = result["status"]
    state["awaiting_confirmation"] = False

    # 更新長期記憶偏好
    prefs = {}
    cf = state["collected_fields"]
    if cf.get("address"):
        prefs["last_address"] = cf["address"]
    if cf.get("phone"):
        prefs["last_phone"] = cf["phone"]
    if cf.get("preferred_time_slot"):
        prefs["preferred_time_slot"] = cf["preferred_time_slot"]
    if prefs:
        STORE.save_preferences(actor_id, prefs)

    return _reply(
        state,
        f"已成功建立案件 {result['request_id']}，目前狀態為「等待廠商確認」。"
        f"您可以在首頁「我的服務」查看進度。",
    )


def _reply(state: dict, reply: str) -> dict:
    return {"reply": reply, "state": state}
