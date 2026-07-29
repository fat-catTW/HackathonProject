"""Local service catalog used by the manual service pages."""

from .restaurant_catalog import RESTAURANTS

SERVICES: list[dict] = [
    {
        "id": "plumbing_repair",
        "name": "水電修繕",
        "description": "漏水、插座、燈具與設備修繕",
        "service_vendor_id": 11,
        "cms_type": "10",
        "enabled": True,
        "keywords": ["水電", "修繕", "漏水", "插座", "燈具", "浴室", "維修"],
        "schema": {
            "fields": [
                {
                    "id": "issue_description",
                    "label": "問題描述",
                    "type": "text",
                    "required": True,
                    "question": "請描述目前遇到的狀況，例如漏水位置或設備故障情形。",
                },
                {
                    "id": "preferred_date",
                    "label": "希望日期",
                    "type": "date",
                    "required": True,
                    "question": "請問希望安排哪一天服務？",
                },
                {
                    "id": "preferred_time_slot",
                    "label": "希望時段",
                    "type": "select",
                    "required": True,
                    "options": ["MORNING", "AFTERNOON", "EVENING"],
                    "question": "請問希望安排上午、下午還是晚上？",
                },
                {
                    "id": "address",
                    "label": "服務地址",
                    "type": "text",
                    "required": True,
                    "question": "請提供完整服務地址，方便安排人員前往。",
                },
                {
                    "id": "phone",
                    "label": "聯絡電話",
                    "type": "text",
                    "required": True,
                    "question": "請提供可聯絡的手機號碼。",
                },
            ]
        },
    },
    {
        "id": "washing_machine_cleaning",
        "name": "洗衣機清洗",
        "description": "直立式與滾筒式居家清洗",
        "service_vendor_id": 1,
        "cms_type": "2",
        "enabled": True,
        "keywords": ["洗衣機", "清洗", "滾筒式", "直立式", "內槽"],
        "schema": {
            "fields": [
                {
                    "id": "quantity",
                    "label": "洗衣機數量",
                    "type": "number",
                    "required": True,
                    "question": "請問需要清洗幾台洗衣機？",
                },
                {
                    "id": "machine_type",
                    "label": "洗衣機類型",
                    "type": "select",
                    "required": True,
                    "options": ["TOP_LOAD", "FRONT_LOAD"],
                    "question": "請問是直立式還是滾筒式洗衣機？",
                },
                {
                    "id": "preferred_date",
                    "label": "希望日期",
                    "type": "date",
                    "required": True,
                    "question": "請問希望安排哪一天清洗？",
                },
                {
                    "id": "preferred_time_slot",
                    "label": "希望時段",
                    "type": "select",
                    "required": True,
                    "options": ["MORNING", "AFTERNOON", "EVENING"],
                    "question": "請問希望安排上午、下午還是晚上？",
                },
                {
                    "id": "address",
                    "label": "服務地址",
                    "type": "text",
                    "required": True,
                    "question": "請提供完整服務地址，方便安排人員前往。",
                },
                {
                    "id": "phone",
                    "label": "聯絡電話",
                    "type": "text",
                    "required": True,
                    "question": "請提供可聯絡的手機號碼。",
                },
            ]
        },
    },
    {
        "id": "air_conditioner_cleaning",
        "name": "冷氣清洗",
        "description": "壁掛式冷氣清潔與保養",
        "service_vendor_id": 1,
        "cms_type": "2",
        "enabled": True,
        "keywords": ["冷氣", "清洗", "保養", "壁掛式", "室內機"],
        "schema": {
            "fields": [
                {
                    "id": "quantity",
                    "label": "冷氣數量",
                    "type": "number",
                    "required": True,
                    "question": "請問需要清洗幾台冷氣？",
                },
                {
                    "id": "preferred_date",
                    "label": "希望日期",
                    "type": "date",
                    "required": True,
                    "question": "請問希望安排哪一天服務？",
                },
                {
                    "id": "preferred_time_slot",
                    "label": "希望時段",
                    "type": "select",
                    "required": True,
                    "options": ["MORNING", "AFTERNOON", "EVENING"],
                    "question": "請問希望安排上午、下午還是晚上？",
                },
                {
                    "id": "address",
                    "label": "服務地址",
                    "type": "text",
                    "required": True,
                    "question": "請提供完整服務地址，方便安排人員前往。",
                },
                {
                    "id": "phone",
                    "label": "聯絡電話",
                    "type": "text",
                    "required": True,
                    "question": "請提供可聯絡的手機號碼。",
                },
            ]
        },
    },
    {
        "id": "home_cleaning",
        "name": "居家清潔",
        "description": "日常打掃與深度整理服務",
        "service_vendor_id": 1,
        "cms_type": "1",
        "enabled": True,
        "keywords": ["清潔", "居家", "打掃", "整理", "到府"],
        "schema": {
            "fields": [
                {
                    "id": "hours",
                    "label": "服務時數",
                    "type": "number",
                    "required": True,
                    "question": "請問預計需要幾小時的清潔服務？",
                },
                {
                    "id": "preferred_date",
                    "label": "希望日期",
                    "type": "date",
                    "required": True,
                    "question": "請問希望安排哪一天清潔？",
                },
                {
                    "id": "preferred_time_slot",
                    "label": "希望時段",
                    "type": "select",
                    "required": True,
                    "options": ["MORNING", "AFTERNOON", "EVENING"],
                    "question": "請問希望安排上午、下午還是晚上？",
                },
                {
                    "id": "address",
                    "label": "服務地址",
                    "type": "text",
                    "required": True,
                    "question": "請提供完整服務地址，方便安排人員前往。",
                },
                {
                    "id": "phone",
                    "label": "聯絡電話",
                    "type": "text",
                    "required": True,
                    "question": "請提供可聯絡的手機號碼。",
                },
            ]
        },
    },
    {
        "id": "restaurant_reservation",
        "name": "餐廳訂位",
        "description": "22世紀風味館 精選餐廳訂位服務",
        "service_vendor_id": 22,
        "cms_type": "02",
        "enabled": True,
        "keywords": ["餐廳", "訂位", "訂餐廳", "吃飯", "用餐", "22世紀", "風味館"],
        "schema": {
            "fields": [
                {
                    "id": "restaurant_id",
                    "label": "餐廳選擇",
                    "type": "select",
                    "required": True,
                    "options": [r["id"] for r in RESTAURANTS],
                    "question": "請問想訂哪一間餐廳？目前提供："
                    + "、".join(r["name"] for r in RESTAURANTS)
                    + "。",
                },
                {
                    "id": "reserved_date",
                    "label": "用餐日期",
                    "type": "date",
                    "required": True,
                    "question": "請問希望哪一天用餐？（限今天起 60 天內）",
                },
                {
                    "id": "time_slot",
                    "label": "用餐時段",
                    "type": "select",
                    "required": True,
                    "options": ["LUNCH", "DINNER"],
                    "question": "請問想約午餐還是晚餐？",
                },
                {
                    "id": "people",
                    "label": "用餐人數",
                    "type": "number",
                    "required": True,
                    "question": "請問幾位用餐？（1 至 20 人）",
                },
                {
                    "id": "contact_name",
                    "label": "聯絡人姓名",
                    "type": "text",
                    "required": True,
                    "question": "請問訂位人的姓名？",
                },
                {
                    "id": "phone",
                    "label": "聯絡電話",
                    "type": "text",
                    "required": True,
                    "question": "請提供聯絡手機號碼。",
                },
                {
                    "id": "is_premium",
                    "label": "訂位類型",
                    "type": "select",
                    "required": True,
                    "options": ["STANDARD", "PREMIUM"],
                    "question": "請問需要指定餐廳或高級訂位服務嗎？高級訂位將由專人為您安排指定餐廳或特殊座位需求。",
                },
            ],
        },
    },
]

SELECT_LABELS = {
    "MORNING": "上午",
    "AFTERNOON": "下午",
    "EVENING": "晚上",
    "TOP_LOAD": "直立式",
    "FRONT_LOAD": "滾筒式",
}


def list_services() -> list[dict]:
    return [
        {"id": service["id"], "name": service["name"], "description": service["description"]}
        for service in SERVICES
        if service["enabled"]
    ]


def get_service(service_id: str) -> dict | None:
    return next(
        (service for service in SERVICES if service["id"] == service_id and service["enabled"]),
        None,
    )


def get_service_schema(service_id: str) -> dict | None:
    service = get_service(service_id)
    if not service:
        return None
    return {
        "service_id": service["id"],
        "title": service["name"],
        "description": service["description"],
        "fields": service["schema"]["fields"],
    }
