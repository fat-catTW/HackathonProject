"""Local service catalog used by the manual service pages."""

from .delivery_catalog import list_stores
from .restaurant_catalog import RESTAURANTS

# health_product_recommendation is a query-and-answer service (like
# restaurant_reservation / food_delivery), not a form-and-submit one: the
# agent (see app/agent/agent.py) intercepts it before the generic
# submit_service_request flow and calls tools.call("recommend_products_by_health_need", ...)
# directly, replying with the recommendation instead of creating a case.
# The single "query" field below only exists so list_services/get_service_schema
# has something to describe; it is never validated/submitted.

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
    {
        "id": "quick_purchase",
        "name": "快速下單",
        "description": "供品、水果等常用組合，說出需求直接下單，不用逛商城",
        "service_vendor_id": None,
        "cms_type": None,
        "enabled": True,
        "keywords": ["供品", "三牲", "水果盆", "祭拜", "祭祖", "牲禮"],
        "schema": {
            "fields": [
                {
                    "id": "query",
                    "label": "想買的東西",
                    "type": "textarea",
                    "required": True,
                    "question": "想買點什麼呢？例如供品或水果。",
                },
                {
                    "id": "address",
                    "label": "收件地址",
                    "type": "text",
                    "required": True,
                    "question": "請提供收件地址。",
                },
                {
                    "id": "phone",
                    "label": "聯絡電話",
                    "type": "text",
                    "required": True,
                    "question": "請提供聯絡電話。",
                },
            ]
        },
    },
    {
        "id": "health_product_recommendation",
        "name": "健康商品推薦",
        "description": "說出健康或飲食需求，推薦適合的 7-11 商品",
        "service_vendor_id": None,
        "cms_type": None,
        "enabled": True,
        "keywords": ["健康", "營養", "減脂", "增肌", "低糖", "低鈉", "推薦", "飲食", "吃什麼"],
        "schema": {
            "fields": [
                {
                    "id": "query",
                    "label": "健康或飲食需求",
                    "type": "textarea",
                    "required": True,
                    "question": "請問想解決什麼健康或飲食需求呢？例如：我在減脂但想吃點甜食。",
                },
            ]
        },
    },
    {
        "id": "shop_purchase",
        "name": "商城購物",
        "description": "多店家商城購物，可用點數折抵",
        "service_vendor_id": None,
        "cms_type": None,
        "enabled": True,
        "keywords": ["商城", "購物", "買東西", "逛街", "點數", "兌換", "shop", "mall"],
        "schema": {
            "fields": [
                {
                    "id": "note",
                    "label": "購物需求",
                    "type": "text",
                    "required": True,
                    "question": "想買點什麼呢？",
                },
            ],
        },
    },
    {
        "id": "shop_price_compare",
        "name": "商品比價",
        "description": "說出想比價的商品名稱，馬上看到各店家價格",
        "service_vendor_id": None,
        "cms_type": None,
        "enabled": True,
        "keywords": ["比價", "比較", "比較價格", "哪裡最便宜", "哪家最便宜", "最便宜", "價格比較"],
        "schema": {
            "fields": [
                {
                    "id": "query",
                    "label": "想比價的商品",
                    "type": "textarea",
                    "required": True,
                    "question": "請問想比較哪一個商品的價格呢？",
                },
            ],
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
    {
        "id": "food_delivery",
        "name": "美食外送",
        "description": "附近店家美食外送到府服務",
        "service_vendor_id": 30,
        "cms_type": "06",
        "enabled": True,
        "keywords": ["外送", "美食", "外帶", "便當", "飲料", "點餐", "delivery"],
        "schema": {
            "fields": [
                {
                    "id": "address",
                    "label": "外送地址",
                    "type": "address",
                    "required": True,
                    "question": "請提供外送地址（含樓層備註）。",
                },
                {
                    "id": "store_id",
                    "label": "選擇店家",
                    "type": "select",
                    "required": True,
                    "question": "請問想點哪一間店家？目前提供："
                    + "、".join(s["name"] for s in list_stores())
                    + "。",
                },
                {
                    "id": "goods",
                    "label": "餐點品項",
                    "type": "cart",
                    "required": True,
                    "question": "請選擇要訂購的餐點與數量。",
                },
                {
                    "id": "contact_name",
                    "label": "收件人姓名",
                    "type": "text",
                    "required": True,
                    "question": "請填寫收件人姓名。",
                },
                {
                    "id": "note",
                    "label": "備註需求",
                    "type": "text",
                    "required": True,
                    "question": "有沒有其他需求呢？例如全糖去冰、不辣等，沒有的話可以直接說「沒有」。",
                },
            ],
        },
    },
    {
        "id": "package_shipping",
        "name": "包裹寄送",
        "description": "統一速達（黑貓宅急便）到府收件或 7-11 店到店寄件",
        "service_vendor_id": 2,
        "cms_type": "20",
        "enabled": True,
        "keywords": ["包裹", "寄件", "寄送", "宅配", "黑貓", "交貨便", "寄快遞", "寄包裹"],
        "schema": {
            "fields": [
                {
                    "id": "pickup_method",
                    "label": "取件方式",
                    "type": "select",
                    "required": True,
                    "options": ["HOME_PICKUP", "STORE_TO_STORE"],
                    "question": "請問希望到府收件，還是要用 7-11 店到店寄件呢？",
                },
                {
                    "id": "sender_address",
                    "label": "寄件地址",
                    "type": "address",
                    "required": True,
                    "visibleWhen": {"fieldId": "pickup_method", "value": "HOME_PICKUP"},
                    "question": "請提供寄件地址。",
                },
                {
                    "id": "receiver_address",
                    "label": "收件地址",
                    "type": "address",
                    "required": True,
                    "visibleWhen": {"fieldId": "pickup_method", "value": "HOME_PICKUP"},
                    "question": "請提供收件地址。",
                },
                {
                    "id": "sender_store",
                    "label": "寄件門市",
                    "type": "text",
                    "required": True,
                    "visibleWhen": {"fieldId": "pickup_method", "value": "STORE_TO_STORE"},
                    "question": "請問要從哪一間 7-11 門市寄件呢？",
                },
                {
                    "id": "receiver_store",
                    "label": "收件門市",
                    "type": "text",
                    "required": True,
                    "visibleWhen": {"fieldId": "pickup_method", "value": "STORE_TO_STORE"},
                    "question": "請問收件人要在哪一間 7-11 門市取件呢？",
                },
                {
                    "id": "weight_kg",
                    "label": "包裹重量（公斤）",
                    "type": "number",
                    "required": True,
                    "question": "請問包裹大約多重呢？（公斤，請填整數）",
                },
                {
                    "id": "length_cm",
                    "label": "包裹長度（公分）",
                    "type": "number",
                    "required": True,
                    "question": "請問包裹的長是幾公分呢？",
                },
                {
                    "id": "width_cm",
                    "label": "包裹寬度（公分）",
                    "type": "number",
                    "required": True,
                    "question": "請問包裹的寬是幾公分呢？",
                },
                {
                    "id": "height_cm",
                    "label": "包裹高度（公分）",
                    "type": "number",
                    "required": True,
                    "question": "請問包裹的高是幾公分呢？",
                },
                {
                    "id": "item_description",
                    "label": "內容物概述",
                    "type": "textarea",
                    "required": True,
                    "question": "請簡單描述包裹內容物是什麼。",
                },
                {
                    "id": "declared_value",
                    "label": "申報價值（元）",
                    "type": "number",
                    "required": True,
                    "question": "請問包裹內容物大約值多少錢呢？",
                },
                {
                    "id": "pickup_time_slot",
                    "label": "取件時段",
                    "type": "time",
                    "required": True,
                    "minValue": "08:30",
                    "maxValue": "18:00",
                    "step": 300,
                    "question": "請問希望什麼時間取件呢？",
                },
                {
                    "id": "contact_name",
                    "label": "聯絡人姓名",
                    "type": "text",
                    "required": True,
                    "question": "請問聯絡人姓名是？",
                },
                {
                    "id": "phone",
                    "label": "聯絡電話",
                    "type": "text",
                    "required": True,
                    "question": "請提供聯絡手機號碼。",
                },
            ]
        },
    },
    {
        "id": "customer_support",
        "name": "客服諮詢",
        "description": "FAQ 無法解決時，建立客服諮詢單並帶入目前頁面與案件資訊。",
        "enabled": True,
        "show_in_catalog": False,
        "keywords": [],
        "request_category": "CUSTOMER_SUPPORT",
        "pms_form_type": 5,
        "schema": {
            "fields": [
                {"id": "faq_reference", "label": "參考 FAQ", "type": "text", "required": False},
                {"id": "current_page_id", "label": "頁面代碼", "type": "text", "required": False},
                {"id": "current_page_label", "label": "目前頁面", "type": "text", "required": False},
                {"id": "related_request_id", "label": "關聯案件編號", "type": "text", "required": False},
                {"id": "related_service_name", "label": "關聯服務", "type": "text", "required": False},
                {
                    "id": "issue_topic",
                    "label": "問題分類",
                    "type": "select",
                    "required": True,
                    "options": ["訂單取消", "廠商回覆進度", "查看報價", "其他問題"],
                },
                {"id": "issue_summary", "label": "問題摘要", "type": "text", "required": True},
                {"id": "issue_details", "label": "問題說明", "type": "textarea", "required": True},
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
    "HOME_PICKUP": "到府收件",
    "STORE_TO_STORE": "7-11 店到店",
}


def list_services() -> list[dict]:
    return [
        {"id": service["id"], "name": service["name"], "description": service["description"]}
        for service in SERVICES
        if service["enabled"] and service.get("show_in_catalog", True)
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
