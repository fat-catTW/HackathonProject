"""Local service catalog used by the manual service pages."""

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
                    "question": "請問這次主要的叫修工項是什麼？",
                },
                {
                    "id": "issue_description",
                    "label": "問題描述",
                    "type": "textarea",
                    "required": True,
                    "question": "請描述目前遇到的狀況，例如漏水位置或設備故障情形。",
                },
                {
                    "id": "issue_photo",
                    "label": "現場照片",
                    "type": "file",
                    "required": False,
                    "question": "若方便的話，也可以上傳現場照片讓師傅更快了解狀況。",
                },
                {
                    "id": "preferred_date",
                    "label": "服務日期",
                    "type": "date",
                    "required": True,
                    "question": "請問希望安排哪一天服務？",
                },
                {
                    "id": "preferred_time_slot",
                    "label": "服務時間",
                    "type": "time",
                    "required": True,
                    "minValue": "08:30",
                    "maxValue": "18:00",
                    "step": 300,
                    "question": "請問希望安排什麼時間服務？",
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
                {
                    "id": "notes",
                    "label": "備註",
                    "type": "textarea",
                    "required": False,
                    "question": "如果有其他補充，也可以留下備註。",
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
                    "label": "希望時間",
                    "type": "time",
                    "required": True,
                    "minValue": "08:30",
                    "maxValue": "18:00",
                    "step": 300,
                    "question": "請問希望安排什麼時間清洗？",
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
                {
                    "id": "notes",
                    "label": "備註",
                    "type": "textarea",
                    "required": False,
                    "question": "如果有其他補充，也可以留下備註。",
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
                    "id": "air_conditioner_type",
                    "label": "冷氣機種",
                    "type": "select",
                    "required": True,
                    "options": ["壁掛式", "天花板嵌入式", "四方吹業務型"],
                    "question": "請問要清洗的冷氣機種是哪一種？",
                },
                {
                    "id": "antibacterial_film_addon",
                    "label": "是否加購日本抗菌膜",
                    "type": "select",
                    "required": True,
                    "options": ["YES", "NO"],
                    "question": "請問是否需要加購日本抗菌膜？",
                },
                {
                    "id": "antibacterial_film_quantity",
                    "label": "日本抗菌膜數量",
                    "type": "number",
                    "required": False,
                    "visibleWhen": {"fieldId": "antibacterial_film_addon", "value": "YES"},
                    "question": "如果需要加購，請問要加購幾個日本抗菌膜？",
                },
                {
                    "id": "preferred_date",
                    "label": "服務日期",
                    "type": "date",
                    "required": True,
                    "question": "請問希望安排哪一天服務？",
                },
                {
                    "id": "preferred_time_slot",
                    "label": "服務時間",
                    "type": "time",
                    "required": True,
                    "minValue": "08:30",
                    "maxValue": "18:00",
                    "step": 300,
                    "question": "請問希望安排什麼時間服務？",
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
                {
                    "id": "notes",
                    "label": "備註",
                    "type": "textarea",
                    "required": False,
                    "question": "如果有其他補充，也可以留下備註。",
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
                    "id": "cleaning_service_option",
                    "label": "服務選項",
                    "type": "select",
                    "required": True,
                    "options": [
                        "地板清潔",
                        "石材地板研磨 晶化 拋光",
                        "地毯清潔",
                        "玻璃清潔",
                        "天花板除塵",
                        "廁所清潔",
                    ],
                    "question": "請問這次需要哪一種居家清潔服務？",
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
                    "label": "服務時間",
                    "type": "time",
                    "required": True,
                    "minValue": "08:30",
                    "maxValue": "18:00",
                    "step": 300,
                    "question": "請問希望安排什麼時間到府服務？",
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
                {
                    "id": "notes",
                    "label": "備註",
                    "type": "textarea",
                    "required": False,
                    "question": "如果有其他補充，也可以留下備註。",
                },
            ]
        },
    },
]

SELECT_LABELS = {
    "MORNING": "上午",
    "AFTERNOON": "下午",
    "EVENING": "晚上",
    "TOP_LOAD": "直立式",
    "FRONT_LOAD": "滾筒式",
    "YES": "需要",
    "NO": "不需要",
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


def vendor_id_for_service(service_id: str) -> int | None:
    """服務所屬的廠商；已下架的服務也要能查到，既有案件仍屬於原廠商。"""
    service = next((s for s in SERVICES if s["id"] == service_id), None)
    if not service:
        return None
    vendor_id = service.get("service_vendor_id")
    return int(vendor_id) if vendor_id is not None else None


def service_ids_for_vendor(vendor_id: int) -> list[str]:
    return [s["id"] for s in SERVICES if s.get("service_vendor_id") == vendor_id]


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
