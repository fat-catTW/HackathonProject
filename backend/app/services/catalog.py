"""Service Catalog（Mock 版 DynamoDB SERVICE#... item）。

欄位設計對齊：
- 設計書 11.3 Service Catalog Item schema
- 命題主檔 cms_homepage_service（service_vendor_id / type）
- pms_form_topic 題目類別（number/date/select/text ≒ 簡答/日期/單選/地區）
"""

SERVICES: list[dict] = [
    {
        "id": "plumbing_repair",
        "name": "水電修繕",
        "description": "處理漏水、水龍頭及基本水電問題",
        "service_vendor_id": 11,
        "cms_type": "10",
        "enabled": True,
        "keywords": ["水電", "修繕", "漏水", "水龍頭", "馬桶", "電燈", "跳電", "插座", "燈具"],
        "schema": {
            "fields": [
                {"id": "issue_description", "label": "問題描述", "type": "text", "required": True,
                 "question": "請簡單描述遇到的水電問題（例如：廚房水龍頭漏水）。"},
                {"id": "preferred_date", "label": "希望日期", "type": "date", "required": True,
                 "question": "請問希望師傅哪一天到府？"},
                {"id": "preferred_time_slot", "label": "希望時段", "type": "select", "required": True,
                 "options": ["MORNING", "AFTERNOON", "EVENING"],
                 "question": "請問希望上午、下午還是晚上？"},
                {"id": "address", "label": "服務地址", "type": "text", "required": True,
                 "question": "請問服務地址是？（縣市、行政區與詳細地址）"},
                {"id": "phone", "label": "聯絡電話", "type": "text", "required": True,
                 "question": "請留下方便聯絡的電話號碼。"},
            ]
        },
    },
    {
        "id": "washing_machine_cleaning",
        "name": "洗衣機清潔",
        "description": "提供洗衣機拆洗服務",
        "service_vendor_id": 1,
        "cms_type": "2",
        "enabled": True,
        "keywords": ["洗衣機", "拆洗", "洗衣機清洗", "洗衣機清潔"],
        "schema": {
            "fields": [
                {"id": "quantity", "label": "洗衣機數量", "type": "number", "required": True,
                 "question": "請問需要清洗幾台洗衣機？"},
                {"id": "machine_type", "label": "洗衣機類型", "type": "select", "required": True,
                 "options": ["TOP_LOAD", "FRONT_LOAD"],
                 "question": "請問是直立式還是滾筒式洗衣機？"},
                {"id": "preferred_date", "label": "希望日期", "type": "date", "required": True,
                 "question": "請問希望安排在哪一天？"},
                {"id": "preferred_time_slot", "label": "希望時段", "type": "select", "required": True,
                 "options": ["MORNING", "AFTERNOON", "EVENING"],
                 "question": "請問希望上午、下午還是晚上？"},
                {"id": "address", "label": "服務地址", "type": "text", "required": True,
                 "question": "請問服務地址是？（縣市、行政區與詳細地址）"},
                {"id": "phone", "label": "聯絡電話", "type": "text", "required": True,
                 "question": "請留下方便聯絡的電話號碼。"},
            ]
        },
    },
    {
        "id": "air_conditioner_cleaning",
        "name": "冷氣清潔",
        "description": "提供家用冷氣清洗服務",
        "service_vendor_id": 1,
        "cms_type": "2",
        "enabled": True,
        "keywords": ["冷氣", "冷氣清洗", "冷氣清潔", "洗冷氣", "空調"],
        "schema": {
            "fields": [
                {"id": "quantity", "label": "冷氣數量", "type": "number", "required": True,
                 "question": "請問需要清洗幾台冷氣？"},
                {"id": "preferred_date", "label": "希望日期", "type": "date", "required": True,
                 "question": "請問希望服務的日期是哪一天？"},
                {"id": "preferred_time_slot", "label": "希望時段", "type": "select", "required": True,
                 "options": ["MORNING", "AFTERNOON", "EVENING"],
                 "question": "請問希望上午、下午還是晚上？"},
                {"id": "address", "label": "服務地址", "type": "text", "required": True,
                 "question": "請問服務地址是？（縣市、行政區與詳細地址）"},
                {"id": "phone", "label": "聯絡電話", "type": "text", "required": True,
                 "question": "請留下方便聯絡的電話號碼。"},
            ]
        },
    },
    {
        "id": "home_cleaning",
        "name": "居家清潔",
        "description": "專業清潔團隊，從地板、廚房到浴室徹底清潔",
        "service_vendor_id": 1,
        "cms_type": "1",
        "enabled": True,
        "keywords": ["打掃", "居家清潔", "家事", "大掃除", "掃地", "拖地"],
        "schema": {
            "fields": [
                {"id": "hours", "label": "服務時數", "type": "number", "required": True,
                 "question": "請問需要幾小時的清潔服務？"},
                {"id": "preferred_date", "label": "希望日期", "type": "date", "required": True,
                 "question": "請問希望安排在哪一天？"},
                {"id": "preferred_time_slot", "label": "希望時段", "type": "select", "required": True,
                 "options": ["MORNING", "AFTERNOON", "EVENING"],
                 "question": "請問希望上午、下午還是晚上？"},
                {"id": "address", "label": "服務地址", "type": "text", "required": True,
                 "question": "請問服務地址是？（縣市、行政區與詳細地址）"},
                {"id": "phone", "label": "聯絡電話", "type": "text", "required": True,
                 "question": "請留下方便聯絡的電話號碼。"},
            ]
        },
    },
]

SELECT_LABELS = {
    "MORNING": "上午", "AFTERNOON": "下午", "EVENING": "晚上",
    "TOP_LOAD": "直立式", "FRONT_LOAD": "滾筒式",
}


def list_services() -> list[dict]:
    return [
        {"id": s["id"], "name": s["name"], "description": s["description"]}
        for s in SERVICES if s["enabled"]
    ]


def get_service(service_id: str) -> dict | None:
    return next((s for s in SERVICES if s["id"] == service_id and s["enabled"]), None)


def get_service_schema(service_id: str) -> dict | None:
    s = get_service(service_id)
    if not s:
        return None
    return {"service_id": s["id"], "title": s["name"], "fields": s["schema"]["fields"]}
