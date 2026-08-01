from backend.app.agent import agent as agent_module
from backend.app.agent.agent import _detect_service, _extract_fields, _normalize_field_value, _recompute_missing
from backend.app.agent.page_catalog import search_pages
from backend.app.agent.page_help import answer_page_question, looks_like_page_question
from backend.app.services import catalog


def test_quantity_rejects_decimal_text_value():
    field = {"id": "quantity", "type": "number"}
    assert _normalize_field_value(field, "0.1", "是0.1台沒錯") is None


def test_quantity_accepts_integer_text_value():
    field = {"id": "quantity", "type": "number"}
    assert _normalize_field_value(field, "2", "是2台沒錯") == 2


def test_page_question_detects_navigation_for_service_application():
    assert looks_like_page_question("我可以去哪裡申請居家清潔?", current_page_id="assistant")


def test_page_search_prioritizes_air_conditioner_form_for_application_navigation():
    matches = search_pages("我要去哪裡申請冷氣清潔?", current_page_id="assistant")
    assert matches
    assert matches[0]["page_id"] == "service_form_air_conditioner_cleaning"


def test_page_help_formats_service_application_steps():
    matches = search_pages("我要去哪裡申請冷氣清潔?", current_page_id="assistant")
    reply = answer_page_question(
        "我要去哪裡申請冷氣清潔?",
        current_page_id="assistant",
        tool_payload={"success": True, "matches": matches},
    )
    assert reply is not None
    assert "服務首頁" in reply
    assert "冷氣清潔表單" in reply


def test_page_help_supports_voice_filling_on_home_page():
    reply = answer_page_question(
        "我想要用這邊的語音來填打",
        current_page_id="home",
    )
    assert reply is not None
    assert "支援" in reply
    assert "語音" in reply
    assert "不支援" not in reply


def test_page_help_supports_switching_service_form_to_voice_filling():
    reply = answer_page_question(
        "我想要用語音來填",
        current_page_id="service_form_air_conditioner_cleaning",
    )
    assert reply is not None
    assert "冷氣清潔表單" in reply
    assert "語音" in reply
    assert "不支援" not in reply


def test_extract_fields_allows_updating_existing_value(monkeypatch):
    state = {
        "service_id": "home_cleaning",
        "service_name": "居家清潔",
        "service_schema": {
            "fields": [
                {
                    "id": "preferred_time_slot",
                    "label": "服務時間",
                    "type": "time",
                    "required": True,
                    "minValue": "08:30",
                    "maxValue": "18:00",
                    "step": 300,
                }
            ]
        },
        "collected_fields": {"preferred_time_slot": "14:00"},
        "missing_fields": [],
        "status": "COLLECTING_INFORMATION",
        "request_id": None,
    }

    monkeypatch.setattr(
        agent_module.llm,
        "extract_fields",
        lambda **kwargs: {"preferred_time_slot": "15:00"},
    )

    found = _extract_fields("user-1", state, "服務時間改成 15:00", events=[])
    assert found == {"preferred_time_slot": "15:00"}


def test_recompute_missing_skips_fields_hidden_by_visible_when():
    state = {
        "service_schema": {
            "fields": [
                {"id": "pickup_method", "type": "select", "required": True},
                {
                    "id": "sender_store",
                    "type": "text",
                    "required": True,
                    "visibleWhen": {"fieldId": "pickup_method", "value": "STORE_TO_STORE"},
                },
                {
                    "id": "sender_address",
                    "type": "address",
                    "required": True,
                    "visibleWhen": {"fieldId": "pickup_method", "value": "HOME_PICKUP"},
                },
            ]
        },
        "collected_fields": {"pickup_method": "HOME_PICKUP"},
    }

    _recompute_missing(state)

    assert state["missing_fields"] == ["sender_address"]


def test_normalize_field_value_parses_address_type_by_type_not_field_id():
    field = {"id": "receiver_address", "type": "address", "required": True}
    noisy_text = "地址是台北市信義區松仁路100號沒錯"
    result = _normalize_field_value(field, noisy_text, noisy_text)
    assert result == "台北市信義區松仁路100號"


def test_extract_fields_falls_back_to_rule_parser_for_repair_item_alias(monkeypatch):
    state = {
        "service_id": "plumbing_repair",
        "service_name": "水電修繕",
        "service_schema": {
            "fields": [
                {
                    "id": "repair_item",
                    "label": "叫修工項",
                    "type": "select",
                    "required": True,
                    "options": [
                        "水管",
                        "水龍頭",
                        "馬桶",
                        "電燈",
                        "洗手台",
                        "流理臺",
                        "浴廁設備",
                        "插座",
                        "配電箱",
                        "電熱水器",
                        "馬達",
                        "水塔",
                        "防水工程",
                        "門窗/紗窗",
                        "泥作工程(地磚)",
                        "採光罩",
                    ],
                }
            ]
        },
        "collected_fields": {},
        "missing_fields": ["repair_item"],
        "status": "COLLECTING_INFORMATION",
        "request_id": None,
    }

    monkeypatch.setattr(agent_module.llm, "extract_fields", lambda **kwargs: {})

    found = _extract_fields("user-1", state, "浴缸", events=[])

    assert found == {"repair_item": "浴廁設備"}


def test_extract_fields_maps_home_cleaning_alias(monkeypatch):
    schema = catalog.get_service_schema("home_cleaning")
    state = {
        "service_id": "home_cleaning",
        "service_name": "居家清潔",
        "service_schema": {"fields": schema["fields"]},
        "collected_fields": {},
        "missing_fields": ["cleaning_service_option"],
        "status": "COLLECTING_INFORMATION",
        "request_id": None,
    }

    monkeypatch.setattr(agent_module.llm, "extract_fields", lambda **kwargs: {})

    found = _extract_fields("user-1", state, "我要地板清理", events=[])

    assert found == {"cleaning_service_option": "地板清潔"}


def test_extract_fields_maps_air_conditioner_type_alias(monkeypatch):
    schema = catalog.get_service_schema("air_conditioner_cleaning")
    state = {
        "service_id": "air_conditioner_cleaning",
        "service_name": "冷氣清洗",
        "service_schema": {"fields": schema["fields"]},
        "collected_fields": {"quantity": 1},
        "missing_fields": ["air_conditioner_type"],
        "status": "COLLECTING_INFORMATION",
        "request_id": None,
    }

    monkeypatch.setattr(agent_module.llm, "extract_fields", lambda **kwargs: {})

    found = _extract_fields("user-1", state, "我的是天花板的", events=[])

    assert found == {"air_conditioner_type": "天花板嵌入式"}


def test_extract_fields_captures_active_issue_description_free_text(monkeypatch):
    schema = catalog.get_service_schema("plumbing_repair")
    state = {
        "service_id": "plumbing_repair",
        "service_name": "水電修繕",
        "service_schema": {"fields": schema["fields"]},
        "collected_fields": {"repair_item": "馬桶"},
        "missing_fields": ["issue_description"],
        "status": "COLLECTING_INFORMATION",
        "request_id": None,
        "debug_trace": {},
    }

    monkeypatch.setattr(agent_module.llm, "extract_fields", lambda **kwargs: {})

    found = _extract_fields("user-1", state, "問題就是馬桶堵住了", events=[])

    assert found == {"issue_description": "問題就是馬桶堵住了"}
    assert {"field_id": "issue_description", "source": "free_text_capture"} in state["debug_trace"]["field_sources"]


def test_detect_service_prefers_valid_llm_choice(monkeypatch):
    services = [item for item in catalog.list_services() if item["id"] in {"home_cleaning", "air_conditioner_cleaning"}]

    monkeypatch.setattr(
        agent_module.llm,
        "choose_service",
        lambda message, services, short_term_memory="", long_term_memory="": "home_cleaning",
    )

    detected = _detect_service("我想預約這個", services, "", "")

    assert detected == "home_cleaning"


def test_handle_message_prefers_llm_chat_reply_for_identity_question(monkeypatch):
    state = agent_module.new_state()

    monkeypatch.setattr(agent_module.llm, "is_available", lambda: True)
    monkeypatch.setattr(
        agent_module,
        "_available_services",
        lambda auth_token=None: catalog.list_services(),
    )
    monkeypatch.setattr(
        agent_module.llm,
        "plan_turn",
        lambda **kwargs: {
            "mode": "chat",
            "reply": "我是你的 AI 生活服務管家，可以陪你聊天，也可以幫你安排清潔、修繕和其他生活服務。",
            "service_id": None,
        },
    )

    result = agent_module.handle_message(
        "user-1",
        "sess-1",
        state,
        "你是誰",
        current_page_id="home",
    )

    assert "AI 生活服務管家" in result["reply"]
    assert "我目前只支援這幾種服務" not in result["reply"]
    assert result["debug_trace"]["turn_router"]["mode"] == "chat"


def test_handle_message_prefers_llm_chat_reply_for_capability_question(monkeypatch):
    state = agent_module.new_state()

    monkeypatch.setattr(agent_module.llm, "is_available", lambda: True)
    monkeypatch.setattr(
        agent_module,
        "_available_services",
        lambda auth_token=None: catalog.list_services(),
    )
    monkeypatch.setattr(
        agent_module.llm,
        "plan_turn",
        lambda **kwargs: {
            "mode": "chat",
            "reply": "我可以回答你的問題、協助你找頁面，也能幫你一步一步把服務申請資料填完。",
            "service_id": None,
        },
    )

    result = agent_module.handle_message(
        "user-1",
        "sess-1",
        state,
        "你的功能是什麼",
        current_page_id="home",
    )

    assert "一步一步把服務申請資料填完" in result["reply"]
    assert "你現在看到的是「服務首頁」" not in result["reply"]


def test_handle_message_prioritizes_page_help_over_service_start_for_navigation_query(monkeypatch):
    state = agent_module.new_state()

    monkeypatch.setattr(agent_module.llm, "is_available", lambda: True)
    monkeypatch.setattr(
        agent_module,
        "_available_services",
        lambda auth_token=None: catalog.list_services(),
    )
    monkeypatch.setattr(
        agent_module.llm,
        "plan_turn",
        lambda **kwargs: {
            "mode": "service_request",
            "reply": None,
            "service_id": "air_conditioner_cleaning",
        },
    )

    result = agent_module.handle_message(
        "user-1",
        "sess-1",
        state,
        "如果我要訂冷氣清潔的話可以去哪裡訂",
        current_page_id="assistant",
    )

    assert "冷氣清潔表單" in result["reply"] or "服務首頁" in result["reply"]
    assert "幾台" not in result["reply"]
    assert result["state"]["service_id"] is None


def test_handle_message_active_form_can_return_llm_reply_without_forcing_field_prompt(monkeypatch):
    schema = catalog.get_service_schema("air_conditioner_cleaning")
    state = agent_module.new_state()
    state["service_id"] = "air_conditioner_cleaning"
    state["service_name"] = "冷氣清洗"
    state["service_schema"] = {"fields": schema["fields"]}
    state["collected_fields"] = {"quantity": 1}
    state["missing_fields"] = ["air_conditioner_type", "antibacterial_film_addon", "preferred_date", "preferred_time_slot", "address", "phone"]

    monkeypatch.setattr(agent_module.llm, "is_available", lambda: True)
    monkeypatch.setattr(
        agent_module.llm,
        "plan_form_turn",
        lambda **kwargs: {
            "mode": "reply",
            "reply": "我是 AI 管家，會繼續幫你把冷氣清洗資料整理好。",
            "fields": {},
        },
    )

    result = agent_module.handle_message(
        "user-1",
        "sess-1",
        state,
        "你是誰",
        current_page_id="assistant",
    )

    assert result["reply"] == "我是 AI 管家，會繼續幫你把冷氣清洗資料整理好。"
    assert result["state"]["collected_fields"] == {"quantity": 1}
    assert result["state"]["missing_fields"][0] == "air_conditioner_type"


def test_handle_message_active_form_applies_llm_field_update_before_fallback(monkeypatch):
    schema = catalog.get_service_schema("air_conditioner_cleaning")
    state = agent_module.new_state()
    state["service_id"] = "air_conditioner_cleaning"
    state["service_name"] = "冷氣清洗"
    state["service_schema"] = {"fields": schema["fields"]}
    state["collected_fields"] = {"quantity": 1}
    state["missing_fields"] = ["air_conditioner_type", "antibacterial_film_addon", "preferred_date", "preferred_time_slot", "address", "phone"]

    monkeypatch.setattr(agent_module.llm, "is_available", lambda: True)
    monkeypatch.setattr(
        agent_module.llm,
        "plan_form_turn",
        lambda **kwargs: {
            "mode": "reply_and_update",
            "reply": "了解，我先幫你記成天花板嵌入式。",
            "fields": {"air_conditioner_type": "天花板嵌入式"},
        },
    )

    result = agent_module.handle_message(
        "user-1",
        "sess-1",
        state,
        "我的是天花板的",
        current_page_id="assistant",
    )

    assert result["state"]["collected_fields"]["air_conditioner_type"] == "天花板嵌入式"
    assert result["state"]["missing_fields"][0] == "antibacterial_film_addon"
    assert "了解，我先幫你記成天花板嵌入式。" in result["reply"]
    assert result["debug_trace"]["form_router"]["mode"] == "reply_and_update"


def test_handle_message_restarts_in_progress_service_when_user_starts_new_request(monkeypatch):
    service = next(item for item in catalog.list_services() if item["id"] == "air_conditioner_cleaning")
    schema = catalog.get_service_schema("air_conditioner_cleaning")
    state = agent_module.new_state()
    state["service_id"] = "air_conditioner_cleaning"
    state["service_name"] = "冷氣清洗"
    state["service_schema"] = {"fields": schema["fields"]}
    state["collected_fields"] = {
        "antibacterial_film_addon": "YES",
        "antibacterial_film_quantity": 1,
    }
    state["missing_fields"] = ["quantity", "air_conditioner_type", "preferred_date", "preferred_time_slot", "address", "phone"]

    monkeypatch.setattr(
        agent_module,
        "_available_services",
        lambda auth_token=None: [service],
    )
    monkeypatch.setattr(
        agent_module,
        "_service_schema",
        lambda service_id, auth_token=None: schema,
    )
    monkeypatch.setattr(
        agent_module.llm,
        "choose_service",
        lambda message, services, short_term_memory="", long_term_memory="": "air_conditioner_cleaning",
    )
    monkeypatch.setattr(agent_module.llm, "extract_fields", lambda **kwargs: {})

    result = agent_module.handle_message(
        "user-1",
        "sess-1",
        state,
        "我想要設定一個冷氣清潔的服務",
        current_page_id="assistant",
    )

    assert result["state"]["service_id"] == "air_conditioner_cleaning"
    assert result["state"]["collected_fields"] == {}
    assert "quantity" in result["state"]["missing_fields"]
    assert "antibacterial_film_addon" in result["state"]["missing_fields"]
    assert "幾台" in result["reply"]


def test_handle_message_does_not_restart_active_service_for_field_answer(monkeypatch):
    schema = catalog.get_service_schema("air_conditioner_cleaning")
    state = agent_module.new_state()
    state["service_id"] = "air_conditioner_cleaning"
    state["service_name"] = "冷氣清洗"
    state["service_schema"] = {"fields": schema["fields"]}
    state["collected_fields"] = {"air_conditioner_type": "壁掛式"}
    state["missing_fields"] = [
        "quantity",
        "antibacterial_film_addon",
        "preferred_date",
        "preferred_time_slot",
        "address",
        "phone",
    ]

    monkeypatch.setattr(agent_module.llm, "extract_fields", lambda **kwargs: {})

    result = agent_module.handle_message(
        "user-1",
        "sess-1",
        state,
        "我要兩台冷氣",
        current_page_id="assistant",
    )

    assert result["state"]["service_id"] == "air_conditioner_cleaning"
    assert result["state"]["collected_fields"]["air_conditioner_type"] == "壁掛式"
    assert result["state"]["collected_fields"]["quantity"] == 2
    assert "antibacterial_film_addon" in result["state"]["missing_fields"]


def test_handle_message_accepts_reuse_preference_shortcut(monkeypatch):
    schema = catalog.get_service_schema("home_cleaning")
    state = agent_module.new_state()
    state["service_id"] = "home_cleaning"
    state["service_name"] = "居家清潔"
    state["service_schema"] = {"fields": schema["fields"]}
    state["collected_fields"] = {"cleaning_service_option": "地板清潔", "preferred_date": "2026-08-10"}
    state["missing_fields"] = ["preferred_time_slot", "address", "phone"]
    state["pending_pref_field"] = "address"
    state["pending_pref_value"] = "桃園市中壢區"
    state["pending_pref_question"] = "我這邊有你上次使用的服務地址：桃園市中壢區。這次要沿用嗎？"

    monkeypatch.setattr(agent_module.llm, "interpret_yes_no", lambda question, reply: None)
    monkeypatch.setattr(agent_module.llm, "extract_fields", lambda **kwargs: {})

    result = agent_module.handle_message(
        "user-1",
        "sess-1",
        state,
        "用上次的",
        current_page_id="assistant",
    )

    assert result["state"]["collected_fields"]["address"] == "桃園市中壢區"
    assert "phone" in result["state"]["missing_fields"]


def test_handle_message_accepts_plain_reuse_when_llm_is_unclear(monkeypatch):
    schema = catalog.get_service_schema("home_cleaning")
    state = agent_module.new_state()
    state["service_id"] = "home_cleaning"
    state["service_name"] = "居家清潔"
    state["service_schema"] = {"fields": schema["fields"]}
    state["collected_fields"] = {"cleaning_service_option": "地板清潔", "preferred_date": "2026-08-10"}
    state["missing_fields"] = ["preferred_time_slot", "address", "phone"]
    state["pending_pref_field"] = "phone"
    state["pending_pref_value"] = "0912345678"
    state["pending_pref_question"] = "我這邊有你上次使用的聯絡電話：0912345678。這次要沿用嗎？"

    monkeypatch.setattr(agent_module.llm, "interpret_yes_no", lambda question, reply: "unclear")
    monkeypatch.setattr(agent_module.llm, "extract_fields", lambda **kwargs: {})

    result = agent_module.handle_message(
        "user-1",
        "sess-1",
        state,
        "沿用",
        current_page_id="assistant",
    )

    assert result["state"]["collected_fields"]["phone"] == "0912345678"


def test_handle_message_keeps_pending_preference_when_reply_is_unclear(monkeypatch):
    schema = catalog.get_service_schema("home_cleaning")
    state = agent_module.new_state()
    state["service_id"] = "home_cleaning"
    state["service_name"] = "居家清潔"
    state["service_schema"] = {"fields": schema["fields"]}
    state["collected_fields"] = {"cleaning_service_option": "地板清潔", "preferred_date": "2026-08-10"}
    state["missing_fields"] = ["preferred_time_slot", "address", "phone"]
    state["pending_pref_field"] = "phone"
    state["pending_pref_value"] = "0912345678"
    state["pending_pref_question"] = "我這邊有你上次使用的聯絡電話：0912345678。這次要沿用嗎？"

    monkeypatch.setattr(agent_module.llm, "interpret_yes_no", lambda question, reply: "unclear")
    monkeypatch.setattr(agent_module.llm, "extract_fields", lambda **kwargs: {})

    result = agent_module.handle_message(
        "user-1",
        "sess-1",
        state,
        "蛤",
        current_page_id="assistant",
    )

    assert result["reply"] == "我這邊有你上次使用的聯絡電話：0912345678。這次要沿用嗎？"
    assert result["state"]["pending_pref_field"] == "phone"


def _plumbing_state(collected: dict | None = None) -> dict:
    schema = catalog.get_service_schema("plumbing_repair")
    return {
        "service_id": "plumbing_repair",
        "service_name": "水電修繕",
        "service_schema": {"fields": schema["fields"]},
        "collected_fields": collected or {},
        "missing_fields": ["issue_description"],
        "status": "COLLECTING_INFORMATION",
        "request_id": None,
        "debug_trace": {},
    }


def test_field_extraction_only_sees_reusable_preferences(monkeypatch):
    """抽欄位時不能看到上一張單的內容，否則模型會照抄成使用者沒說過的話。"""
    monkeypatch.setattr(
        agent_module,
        "_safe_memory_snapshot",
        lambda actor_id: {
            "preferences": {"last_address": "台北市信義區松高路1號", "last_phone": "0912345678"},
            "long_term_memory": {
                "last_service_name": "水電修繕",
                "last_request_summary": "服務：水電修繕；問題描述：廚房水管漏水；聯絡電話：0912345678",
            },
        },
    )

    seen: dict = {}

    def spy(**kwargs):
        seen.update(kwargs)
        return {}

    monkeypatch.setattr(agent_module.llm, "extract_fields", spy)
    _extract_fields("user-1", _plumbing_state(), "幫我填水電修繕", events=[])

    long_term = seen["long_term_memory"]
    assert "常用地址: 台北市信義區松高路1號" in long_term
    assert "問題描述" not in long_term
    assert "上次摘要" not in long_term


def test_llm_cannot_fill_a_description_the_user_never_said(monkeypatch):
    """模型即使自己生出問題描述（多半抄自記憶），也不寫進表單。"""
    monkeypatch.setattr(
        agent_module.llm,
        "extract_fields",
        lambda **kwargs: {"issue_description": "廚房水槽下方水管漏水"},
    )

    state = _plumbing_state({"repair_item": "水管"})
    found = _extract_fields("user-1", state, "幫我填", events=[])

    assert "issue_description" not in found
    assert "ungrounded_free_text:issue_description" in state["debug_trace"]["fallbacks"]


def test_llm_may_still_quote_the_description_from_this_message(monkeypatch):
    """使用者這次講了，模型摘出其中一段仍然照填。"""
    monkeypatch.setattr(
        agent_module.llm,
        "extract_fields",
        lambda **kwargs: {"issue_description": "廚房水管漏水"},
    )

    state = _plumbing_state({"repair_item": "水管"})
    found = _extract_fields("user-1", state, "幫我填，廚房水管漏水，地板都濕了", events=[])

    assert found["issue_description"] == "廚房水管漏水"
