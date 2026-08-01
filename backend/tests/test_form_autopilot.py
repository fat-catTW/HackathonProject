"""AI 代操表單（form autopilot）：Agent 直接驅動前端表單的行為測試。"""
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.app.agent import agent, form_autopilot, nlu
from backend.app.main import app
from backend.app.services import store as store_module
from backend.app.services.conversation_memory import MEMORY

AIRCON_PAGE = "service_form_air_conditioner_cleaning"
AIRCON_SERVICE = "air_conditioner_cleaning"


@pytest.fixture(autouse=True)
def isolated_store(monkeypatch):
    """偏好設定與 session 寫在自己的暫存 store，不影響其他測試。"""
    with tempfile.TemporaryDirectory() as tmp:
        test_store = store_module.MemoryStore(storage_path=Path(tmp) / "store.json")
        monkeypatch.setattr(store_module, "STORE", test_store)
        yield test_store


@pytest.fixture(autouse=True)
def offline_llm():
    """這個環境連不到 Bedrock，真的 llm.extract_fields 一律回 {}。

    改接專案自己的規則式擷取（nlu.extract_fields，其 docstring 就寫明是單元測試基準），
    這樣路由、正規化、動作組裝都還是走真實流程，只是不依賴網路。
    """

    def fake_extract(*, message, fields, collected_fields, **_kwargs):
        return nlu.extract_fields("autopilot", fields, message, collected_fields)

    with patch.object(agent.llm, "extract_fields", side_effect=fake_extract), patch.object(
        agent.llm, "is_available", return_value=False
    ), patch.object(agent.llm, "interpret_yes_no", return_value=None), patch.object(
        agent.llm, "compose_reply", return_value=None
    ), patch.object(agent.llm, "choose_service", return_value=None):
        yield


def _turn(state, message, actor_id="autopilot-user", **kwargs):
    return agent.handle_message(actor_id, "sess-autopilot", state, message, **kwargs)


def _fill_actions(result):
    return {action["field_id"]: action["value"] for action in result["form_actions"]}


def test_page_id_maps_to_service_id():
    assert form_autopilot.page_service_id(AIRCON_PAGE) == AIRCON_SERVICE
    assert form_autopilot.page_service_id("service_form") is None
    assert form_autopilot.page_service_id("home") is None


def test_dedicated_flow_pages_are_not_autopilot_targets():
    # 這幾個服務在前端是專屬流程頁，畫面上沒有可以逐格代填的表單欄位。
    assert not form_autopilot.supports_autopilot("shop_purchase")
    assert not form_autopilot.supports_autopilot("restaurant_reservation")
    assert form_autopilot.supports_autopilot(AIRCON_SERVICE)


def test_autofill_request_fills_form_fields_from_one_sentence():
    state = agent.new_state()
    result = _turn(
        state,
        "幫我填這張表單，兩台壁掛式，不用抗菌膜，明天下午三點",
        current_page_id=AIRCON_PAGE,
        form_context={"service_id": AIRCON_SERVICE, "values": {}},
    )

    actions = _fill_actions(result)
    assert actions["quantity"] == "2"
    assert actions["air_conditioner_type"] == "壁掛式"
    assert actions["antibacterial_film_addon"] == "NO"
    assert actions["preferred_time_slot"] == "15:00"
    assert all(action["type"] == "fill" for action in result["form_actions"])


def test_autofill_reply_matches_the_actions_it_runs():
    state = agent.new_state()
    result = _turn(
        state,
        "幫我填這張表單，兩台壁掛式",
        current_page_id=AIRCON_PAGE,
        form_context={"service_id": AIRCON_SERVICE, "values": {}},
    )

    reply = result["reply"]
    for action in result["form_actions"]:
        assert f"{action['label']}：{action['display_value']}" in reply
    # 還沒填完時要接著問下一格
    assert result["state"]["missing_fields"]
    assert "還缺" in reply


def test_hidden_fields_never_produce_ui_actions():
    """加購數量只有在「要加購」時才會出現在畫面上，隱藏時不能有動作。"""
    state = agent.new_state()
    result = _turn(
        state,
        "幫我填，兩台壁掛式，不用抗菌膜，要 3 個",
        current_page_id=AIRCON_PAGE,
        form_context={"service_id": AIRCON_SERVICE, "values": {}},
    )

    assert "antibacterial_film_quantity" not in _fill_actions(result)


def test_values_already_on_screen_are_not_filled_again():
    """使用者自己打的值只同步進 Agent，不會被當成 AI 動作再寫一次（會蓋掉游標）。"""
    state = agent.new_state()
    _turn(
        state,
        "幫我填這張表單",
        current_page_id=AIRCON_PAGE,
        form_context={"service_id": AIRCON_SERVICE, "values": {}},
    )

    result = _turn(
        state,
        "電話 0912345678",
        current_page_id=AIRCON_PAGE,
        form_context={
            "service_id": AIRCON_SERVICE,
            "values": {"quantity": "2", "air_conditioner_type": "壁掛式"},
        },
    )

    actions = _fill_actions(result)
    assert "quantity" not in actions
    assert "air_conditioner_type" not in actions
    assert actions["phone"] == "0912345678"
    # 畫面上的值仍然要進到 Agent 的認知，才不會重複問
    assert result["state"]["collected_fields"]["quantity"] == 2


def test_manual_edit_on_screen_wins_over_agent_memory():
    state = agent.new_state()
    _turn(
        state,
        "幫我填這張表單，兩台壁掛式",
        current_page_id=AIRCON_PAGE,
        form_context={"service_id": AIRCON_SERVICE, "values": {}},
    )

    result = _turn(
        state,
        "電話 0912345678",
        current_page_id=AIRCON_PAGE,
        form_context={"service_id": AIRCON_SERVICE, "values": {"quantity": "5"}},
    )

    assert result["state"]["collected_fields"]["quantity"] == 5
    assert "quantity" not in _fill_actions(result)


@pytest.mark.parametrize(
    ("message", "expected_service_id"),
    [
        # 「冷氣清洗」同時命中洗衣機清洗的「清洗」關鍵字，之前會被帶到錯的表單
        ("幫我填冷氣清洗", "air_conditioner_cleaning"),
        ("幫我填洗衣機清洗的表單", "washing_machine_cleaning"),
        ("幫我填水電維修的表單", "plumbing_repair"),
        ("幫我填居家清潔表單", "home_cleaning"),
    ],
)
def test_autofill_from_another_page_redirects_to_the_right_form(message, expected_service_id):
    state = agent.new_state()
    result = _turn(state, message, current_page_id="home")

    assert result["redirect_path"] == f"/services/{expected_service_id}"
    assert result["state"]["service_id"] == expected_service_id


def test_naming_another_service_on_a_form_page_moves_to_that_form():
    state = agent.new_state()
    result = _turn(
        state,
        "幫我填冷氣清洗",
        current_page_id="service_form_home_cleaning",
        form_context={"service_id": "home_cleaning", "values": {}},
    )

    assert result["state"]["service_id"] == AIRCON_SERVICE
    assert result["redirect_path"] == f"/services/{AIRCON_SERVICE}"


def test_page_question_on_a_form_page_still_gets_page_help():
    state = agent.new_state()
    result = _turn(
        state,
        "這頁可以做什麼",
        current_page_id=AIRCON_PAGE,
        form_context={"service_id": AIRCON_SERVICE, "values": {}},
    )

    assert result["form_actions"] == []
    assert result["state"]["form_autopilot"] is None
    assert "冷氣清潔表單" in result["reply"]


def test_asking_for_another_service_on_a_form_page_is_not_treated_as_form_input():
    state = agent.new_state()
    result = _turn(
        state,
        "我要預約居家清潔",
        current_page_id=AIRCON_PAGE,
        form_context={"service_id": AIRCON_SERVICE, "values": {"quantity": "2"}},
    )

    assert result["state"]["service_id"] == "home_cleaning"
    assert result["form_actions"] == []


def test_changing_your_mind_mid_autopilot_moves_to_the_other_form():
    """代操進行中改口要別的服務時，帶去那張表單，而不是硬塞進眼前這張。"""
    state = agent.new_state()
    _turn(
        state,
        "幫我填這張表單，兩台壁掛式",
        current_page_id=AIRCON_PAGE,
        form_context={"service_id": AIRCON_SERVICE, "values": {}},
    )
    assert state["form_autopilot"]["service_id"] == AIRCON_SERVICE

    result = _turn(
        state,
        "算了，我要預約居家清潔",
        current_page_id=AIRCON_PAGE,
        form_context={"service_id": AIRCON_SERVICE, "values": {"quantity": "2"}},
    )

    assert result["state"]["service_id"] == "home_cleaning"
    assert result["redirect_path"] == "/services/home_cleaning"
    # 舊表單收到的資料不會跟著搬過去
    assert "quantity" not in result["state"]["collected_fields"]


def test_answering_a_form_question_is_never_mistaken_for_a_service_switch():
    """包裹寄送頁回答「我需要到府收件」時，「到府」剛好是居家清潔的關鍵字。

    這種正常作答不能被當成改口換服務（會把整張表單的資料清掉）。
    """
    state = agent.new_state()
    _turn(
        state,
        "幫我填這張表單，包裹五公斤",
        current_page_id="service_form_package_shipping",
        form_context={"service_id": "package_shipping", "values": {}},
    )
    assert state["form_autopilot"]["service_id"] == "package_shipping"

    result = _turn(
        state,
        "我需要到府收件",
        current_page_id="service_form_package_shipping",
        form_context={"service_id": "package_shipping", "values": {"weight_kg": "5"}},
    )

    assert result["state"]["service_id"] == "package_shipping"
    assert result["redirect_path"] is None
    assert result["state"]["collected_fields"].get("weight_kg") == 5


def test_follow_up_after_a_reopened_panel_still_drives_the_form():
    """重新打開管家會開新 session；畫面上已有資料時仍要接得下去。"""
    state = agent.new_state()
    result = _turn(
        state,
        "服務時間改成下午三點",
        current_page_id=AIRCON_PAGE,
        form_context={"service_id": AIRCON_SERVICE, "values": {"quantity": "2"}},
    )

    assert _fill_actions(result)["preferred_time_slot"] == "15:00"


def test_saved_preferences_are_filled_in_with_a_note():
    actor_id = "autopilot-prefs-user"
    MEMORY.save_preferences(
        actor_id,
        {"last_address": "台南市東區大學路一段 168 號", "last_phone": "0987654321"},
    )

    state = agent.new_state()
    result = _turn(
        state,
        "幫我填這張表單",
        actor_id=actor_id,
        current_page_id=AIRCON_PAGE,
        form_context={"service_id": AIRCON_SERVICE, "values": {}},
    )

    actions = {action["field_id"]: action for action in result["form_actions"]}
    assert actions["address"]["value"] == "台南市東區大學路一段 168 號"
    assert actions["phone"]["value"] == "0987654321"
    assert actions["address"]["note"] == "沿用你上次填的資料"
    assert "沿用你上次填的資料" in result["reply"]


def test_asking_to_fill_again_after_a_submitted_case_starts_a_new_form():
    """已經送出過案件的對話，再說「幫我填」要開新的一張單。

    之前這種情況會掉回頁面問答，回一句「你可以在冷氣清潔表單填寫需求…」，
    看起來就像代填功能壞掉。
    """
    state = agent.new_state()
    state["request_id"] = "REQ-20260801-ABC123"
    state["service_id"] = "washing_machine_cleaning"
    state["service_name"] = "洗衣機清洗"

    result = _turn(
        state,
        "幫我填，兩台壁掛式冷氣，不用抗菌膜，禮拜三下午兩點半",
        current_page_id=AIRCON_PAGE,
        form_context={"service_id": AIRCON_SERVICE, "values": {}},
    )

    actions = _fill_actions(result)
    assert actions["quantity"] == "2"
    assert actions["air_conditioner_type"] == "壁掛式"
    assert result["state"]["request_id"] is None
    assert result["state"]["service_id"] == AIRCON_SERVICE


def test_a_finished_session_still_answers_page_questions_normally():
    state = agent.new_state()
    state["request_id"] = "REQ-20260801-ABC123"
    state["service_id"] = "washing_machine_cleaning"
    state["service_name"] = "洗衣機清洗"

    result = _turn(state, "我的案件在哪裡看", current_page_id="home")

    assert result["form_actions"] == []
    assert result["state"]["request_id"] == "REQ-20260801-ABC123"


def test_ordinary_chat_never_carries_form_actions():
    state = agent.new_state()
    result = _turn(state, "我要預約冷氣清洗", current_page_id="assistant")

    assert result["form_actions"] == []
    assert result["state"]["form_autopilot"] is None


def test_clearing_a_field_on_screen_clears_it_for_the_agent_too():
    """畫面是唯一真相：使用者把某格刪掉，Agent 不能還以為那格是填好的。"""
    state = agent.new_state()
    _turn(
        state,
        "幫我填這張表單，兩台壁掛式",
        current_page_id=AIRCON_PAGE,
        form_context={"service_id": AIRCON_SERVICE, "values": {}},
    )
    assert state["collected_fields"]["quantity"] == 2

    result = _turn(
        state,
        "先這樣",
        current_page_id=AIRCON_PAGE,
        # 使用者把冷氣數量刪掉了（空字串代表畫面上這格是空的）
        form_context={
            "service_id": AIRCON_SERVICE,
            "values": {"quantity": "", "air_conditioner_type": "壁掛式"},
        },
    )

    assert "quantity" not in result["state"]["collected_fields"]
    assert "quantity" in result["state"]["missing_fields"]


def test_prohibited_shipping_item_from_the_message_is_stopped():
    """訊息裡講的內容物同樣要過違禁品這一關。

    規則式擷取抓不到 item_description（那是 LLM 的工作），所以這裡直接模擬擷取結果，
    測的是代填流程本身有沒有把關。
    """
    state = agent.new_state()
    with patch.object(
        agent, "_extract_fields", return_value={"item_description": "鋰電池行動電源", "weight_kg": 5}
    ):
        result = _turn(
            state,
            "幫我填，寄鋰電池行動電源，五公斤",
            current_page_id="service_form_package_shipping",
            form_context={"service_id": "package_shipping", "values": {}},
        )

    assert "寄送有限制" in result["reply"]
    assert result["state"]["pending_prohibited_item"] == "鋰電池行動電源"
    assert "item_description" not in result["state"]["collected_fields"]
    # 沒確認過就不能讓表單看起來已經填完（送出一定會被擋下來）
    assert result["state"]["status"] != "AWAITING_USER_CONFIRMATION"


def test_prohibited_item_typed_on_screen_is_also_stopped():
    state = agent.new_state()
    result = _turn(
        state,
        "幫我填",
        current_page_id="service_form_package_shipping",
        form_context={
            "service_id": "package_shipping",
            "values": {"item_description": "鋰電池行動電源", "weight_kg": "3"},
        },
    )

    assert "寄送有限制" in result["reply"]
    assert "item_description" not in result["state"]["collected_fields"]


def test_time_is_snapped_to_an_option_the_form_actually_offers():
    """LLM 可能回 14:03，但畫面上的時間下拉每 5 分鐘一格，沒有這個選項。"""
    state = agent.new_state()
    _turn(
        state,
        "幫我填這張表單",
        current_page_id=AIRCON_PAGE,
        form_context={"service_id": AIRCON_SERVICE, "values": {}},
    )
    state["collected_fields"]["preferred_time_slot"] = "14:03"

    result = _turn(
        state,
        "幫我填",
        current_page_id=AIRCON_PAGE,
        form_context={"service_id": AIRCON_SERVICE, "values": {}},
    )

    assert result["state"]["collected_fields"]["preferred_time_slot"] == "14:00"


def test_leaving_the_form_page_stops_the_agent_driving_it():
    state = agent.new_state()
    _turn(
        state,
        "幫我填這張表單，兩台壁掛式",
        current_page_id=AIRCON_PAGE,
        form_context={"service_id": AIRCON_SERVICE, "values": {}},
    )

    # 使用者離開表單頁，之後的一般對話不該再回動作給一張不在畫面上的表單
    result = _turn(state, "服務時間改成下午三點", current_page_id="my_services")

    assert result["form_actions"] == []


@pytest.mark.parametrize(
    "message",
    ["可以用語音幫我填嗎", "這頁支援語音填單嗎", "要怎麼用說的填表"],
)
def test_asking_whether_voice_filling_works_is_still_answered_as_page_help(message):
    state = agent.new_state()
    result = _turn(
        state,
        message,
        current_page_id=AIRCON_PAGE,
        form_context={"service_id": AIRCON_SERVICE, "values": {}},
    )

    assert result["form_actions"] == []
    assert "語音" in result["reply"]


@pytest.mark.parametrize(
    "message",
    [
        "我用說的，幫我填兩台壁掛式冷氣，不用抗菌膜，禮拜三下午兩點半",
        "用語音幫我填，兩台壁掛式冷氣，不用抗菌膜",
    ],
)
def test_speaking_the_request_out_loud_still_fills_the_form(message):
    """提到語音不代表在問功能——這是使用者「用說的」把需求講完，要真的幫他填。"""
    state = agent.new_state()
    result = _turn(
        state,
        message,
        current_page_id=AIRCON_PAGE,
        form_context={"service_id": AIRCON_SERVICE, "values": {}},
    )

    actions = _fill_actions(result)
    assert actions["quantity"] == "2"
    assert actions["air_conditioner_type"] == "壁掛式"


def test_autofill_without_a_recognisable_service_asks_which_one():
    """聽得出要代填、聽不出是哪一種服務時，要回問，而不是丟一句「表單在那邊」。"""
    state = agent.new_state()
    result = _turn(state, "幫我填", current_page_id="home")

    assert result["form_actions"] == []
    assert "哪一種" in result["reply"]
    for name in ("冷氣清洗", "居家清潔", "水電修繕"):
        assert name in result["reply"]


def test_autofill_for_a_dedicated_flow_service_takes_the_user_there():
    """美食外送這類專屬流程頁沒有可以逐格代填的欄位，但也不能只丟頁面說明。"""
    state = agent.new_state()
    result = _turn(state, "幫我填美食外送", current_page_id="home")

    assert result["redirect_path"] == "/services/food_delivery"
    assert result["form_actions"] == []
    assert "店家" in result["reply"]


def test_a_question_on_a_form_page_is_not_adopted_as_form_input():
    """畫面上有資料時，問句仍然是問句，不該被當成在給欄位值。"""
    state = agent.new_state()
    result = _turn(
        state,
        "冷氣清洗多少錢？",
        current_page_id=AIRCON_PAGE,
        form_context={"service_id": AIRCON_SERVICE, "values": {"quantity": "2"}},
    )

    assert result["form_actions"] == []
    assert result["state"]["form_autopilot"] is None


def test_adopting_a_form_page_does_not_silently_write_saved_contact_details():
    """沒說「幫我填」時只是接手繼續收單，不會自作主張把上次的地址電話填進去。"""
    actor_id = "autopilot-adopt-user"
    MEMORY.save_preferences(
        actor_id,
        {"last_address": "台南市東區大學路一段 168 號", "last_phone": "0987654321"},
    )

    state = agent.new_state()
    result = _turn(
        state,
        "服務時間改成下午三點",
        actor_id=actor_id,
        current_page_id=AIRCON_PAGE,
        form_context={"service_id": AIRCON_SERVICE, "values": {"quantity": "2"}},
    )

    filled = _fill_actions(result)
    assert filled.get("preferred_time_slot") == "15:00"
    assert "address" not in filled
    assert "phone" not in filled


def test_chat_api_returns_form_actions_for_the_frontend():
    """走完整 HTTP 介面，確認 form_context 進得去、form_actions 出得來。"""
    client = TestClient(app)
    accounts = client.get("/api/auth/demo-accounts").json()["accounts"]
    headers = {"Authorization": f"Bearer {accounts[0]['token']}"}
    session_id = client.post("/api/sessions", headers=headers).json()["session_id"]

    response = client.post(
        "/api/chat",
        headers=headers,
        json={
            "session_id": session_id,
            "message": "幫我填這張表單，兩台壁掛式",
            "current_page_id": AIRCON_PAGE,
            "form_context": {"service_id": AIRCON_SERVICE, "values": {}},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["service_id"] == AIRCON_SERVICE
    actions = {action["field_id"]: action for action in payload["form_actions"]}
    assert actions["quantity"]["value"] == "2"
    assert actions["quantity"]["type"] == "fill"
    assert actions["air_conditioner_type"]["display_value"] == "壁掛式"


def test_chat_api_accepts_a_request_without_form_context():
    client = TestClient(app)
    accounts = client.get("/api/auth/demo-accounts").json()["accounts"]
    headers = {"Authorization": f"Bearer {accounts[0]['token']}"}
    session_id = client.post("/api/sessions", headers=headers).json()["session_id"]

    response = client.post(
        "/api/chat",
        headers=headers,
        json={"session_id": session_id, "message": "這頁可以做什麼", "current_page_id": "home"},
    )

    assert response.status_code == 200
    assert response.json()["form_actions"] == []
