"""Static shop catalog: categories, stores, dual-spec products, and their SKUs.

SKU stock is intentionally NOT part of this module — it is dynamic runtime
state (see store.py's get_sku_stock/decrement_sku_stock/restock_sku), because
this module's data is plain Python source and cannot be written to at
request time.
"""
from __future__ import annotations

from . import shop_reviews

SHOP_CATEGORIES: list[dict] = [
    {"id": "cat_beverage", "name": "飲品兌換"},
    {"id": "cat_food", "name": "美食兌換"},
    {"id": "cat_daily", "name": "生活日用品"},
    {"id": "cat_cleaning", "name": "居家清潔用品"},
    {"id": "cat_health", "name": "保健營養品"},
    {"id": "cat_electronics", "name": "3C 影音周邊"},
]

SHOP_STORES: list[dict] = [
    {"id": "store_711_taipei", "name": "7-11 台北車站店", "category": "超商", "image": None},
    {"id": "store_uni_style", "name": "統一時代生活選物", "category": "百貨選物", "image": None},
    {"id": "store_family_mart", "name": "全家便利商店 台北忠孝店", "category": "超商", "image": None},
    {"id": "store_louisa", "name": "路易莎咖啡 信義店", "category": "連鎖咖啡", "image": None},
    {"id": "store_mos_burger", "name": "摩斯漢堡 台北車站店", "category": "連鎖速食", "image": None},
    {"id": "store_daiso", "name": "大創生活館 西門店", "category": "生活雜貨", "image": None},
    {"id": "store_shujie", "name": "舒潔生活館", "category": "居家清潔", "image": None},
    {"id": "store_miaojie", "name": "妙潔小舖", "category": "居家清潔", "image": None},
    {"id": "store_health_mart", "name": "健康藥妝", "category": "藥妝保健", "image": None},
    {"id": "store_lohas_health", "name": "樂活保健", "category": "藥妝保健", "image": None},
    {"id": "store_watsons", "name": "屈臣氏 台北信義店", "category": "藥妝", "image": None},
    {"id": "store_carrefour", "name": "家樂福 內湖店", "category": "量販", "image": None},
    {"id": "store_fifine_official", "name": "FIFINE 官方旗艦店", "category": "3C影音", "image": None},
    {"id": "store_blue_mic_tw", "name": "Blue 麥克風台灣旗艦店", "category": "3C影音", "image": None},
    {"id": "store_rode_tw", "name": "Rode 台灣官方旗艦店", "category": "3C影音", "image": None},
    {"id": "store_hyperx_tw", "name": "HyperX 官方旗艦店", "category": "3C影音", "image": None},
    {"id": "store_audio_technica_tw", "name": "Audio-Technica 台灣總代理", "category": "3C影音", "image": None},
    {"id": "store_logitech_tw", "name": "羅技官方旗艦店", "category": "3C影音", "image": None},
    {"id": "store_pro_audio_tw", "name": "音響數位樂器行", "category": "3C影音", "image": None},
]

SHOP_PRODUCTS: list[dict] = [
    {
        "id": "prod_tshirt_basic",
        "store_id": "store_uni_style",
        "category_id": "cat_daily",
        "name": "純棉基本款 T 恤",
        "description": "百搭素色棉 T，透氣舒適，四季皆宜。",
        "product_type": "PHYSICAL",
        "image": None,
        "specs": [
            {"name": "顏色", "options": ["白", "黑"]},
            {"name": "尺寸", "options": ["S", "M", "L"]},
        ],
        "skus": [
            {"sku_id": "sku_tshirt_white_s", "attributes": {"顏色": "白", "尺寸": "S"}, "unit_price": 390, "unit_points": 39},
            {"sku_id": "sku_tshirt_white_m", "attributes": {"顏色": "白", "尺寸": "M"}, "unit_price": 390, "unit_points": 39},
            {"sku_id": "sku_tshirt_black_m", "attributes": {"顏色": "黑", "尺寸": "M"}, "unit_price": 390, "unit_points": 39},
            {"sku_id": "sku_tshirt_black_l", "attributes": {"顏色": "黑", "尺寸": "L"}, "unit_price": 390, "unit_points": 39},
        ],
    },
    {
        "id": "prod_tumbler",
        "store_id": "store_uni_style",
        "category_id": "cat_daily",
        "compare_group_id": "cmp_tumbler",
        "name": "不鏽鋼保溫杯 500ml",
        "description": "12 小時保冷、6 小時保溫，附背帶。",
        "product_type": "PHYSICAL",
        "image": None,
        "specs": [{"name": "顏色", "options": ["粉", "藍"]}],
        "skus": [
            {"sku_id": "sku_tumbler_pink", "attributes": {"顏色": "粉"}, "unit_price": 590, "unit_points": 59},
            {"sku_id": "sku_tumbler_blue", "attributes": {"顏色": "藍"}, "unit_price": 590, "unit_points": 59},
        ],
    },
    {
        "id": "prod_coffee_coupon",
        "store_id": "store_711_taipei",
        "category_id": "cat_beverage",
        "name": "City Café 中杯美式兌換券",
        "description": "全台 7-11 門市皆可兌換，效期 30 天。",
        "product_type": "SERIAL_CODE",
        "image": None,
        "specs": [],
        "skus": [
            {"sku_id": "sku_coffee_americano_m", "attributes": {}, "unit_price": 45, "unit_points": 4},
        ],
    },
    {
        "id": "prod_onigiri_coupon",
        "store_id": "store_711_taipei",
        "category_id": "cat_food",
        "name": "御飯糰任選兌換券",
        "description": "全台 7-11 門市御飯糰系列任選一顆，效期 14 天。",
        "product_type": "SERIAL_CODE",
        "image": None,
        "specs": [],
        "skus": [
            {"sku_id": "sku_onigiri_any", "attributes": {}, "unit_price": 35, "unit_points": 3},
        ],
    },
    {
        "id": "prod_familymart_latte",
        "store_id": "store_family_mart",
        "category_id": "cat_beverage",
        "name": "現萃拿鐵兌換券",
        "description": "全台全家門市咖啡機現萃拿鐵，效期 30 天。",
        "product_type": "SERIAL_CODE",
        "image": None,
        "specs": [],
        "skus": [
            {"sku_id": "sku_familymart_latte_m", "attributes": {}, "unit_price": 50, "unit_points": 5},
        ],
    },
    {
        "id": "prod_louisa_iced_americano",
        "store_id": "store_louisa",
        "category_id": "cat_beverage",
        "name": "冰美式兌換券",
        "description": "全台路易莎門市皆可兌換，效期 30 天。",
        "product_type": "SERIAL_CODE",
        "image": None,
        "specs": [],
        "skus": [
            {"sku_id": "sku_louisa_iced_americano", "attributes": {}, "unit_price": 55, "unit_points": 5},
        ],
    },
    {
        "id": "prod_familymart_egg",
        "store_id": "store_family_mart",
        "category_id": "cat_food",
        "name": "茶葉蛋兌換券（3入）",
        "description": "全台全家門市茶葉蛋 3 顆兌換，效期 14 天。",
        "product_type": "SERIAL_CODE",
        "image": None,
        "specs": [],
        "skus": [
            {"sku_id": "sku_familymart_egg_3", "attributes": {}, "unit_price": 30, "unit_points": 3},
        ],
    },
    {
        "id": "prod_mos_fries",
        "store_id": "store_mos_burger",
        "category_id": "cat_food",
        "name": "薯條兌換券（小）",
        "description": "全台摩斯漢堡門市可兌換小薯一份，效期 14 天。",
        "product_type": "SERIAL_CODE",
        "image": None,
        "specs": [],
        "skus": [
            {"sku_id": "sku_mos_fries_s", "attributes": {}, "unit_price": 40, "unit_points": 4},
        ],
    },
    {
        "id": "prod_daiso_storage_box",
        "store_id": "store_daiso",
        "category_id": "cat_daily",
        "name": "多功能收納盒",
        "description": "可堆疊收納盒，適合衣物、雜物分類收納。",
        "product_type": "PHYSICAL",
        "image": None,
        "specs": [{"name": "顏色", "options": ["白", "灰"]}],
        "skus": [
            {"sku_id": "sku_daiso_box_white", "attributes": {"顏色": "白"}, "unit_price": 99, "unit_points": 10},
            {"sku_id": "sku_daiso_box_gray", "attributes": {"顏色": "灰"}, "unit_price": 99, "unit_points": 10},
        ],
    },
    {
        "id": "prod_clean_spray",
        "store_id": "store_shujie",
        "category_id": "cat_cleaning",
        "compare_group_id": "cmp_clean_spray",
        "name": "多功能清潔噴霧 500ml",
        "description": "廚房、浴室皆可使用，天然配方溫和不傷手。",
        "product_type": "PHYSICAL",
        "image": None,
        "specs": [{"name": "香味", "options": ["檸檬", "茶樹"]}],
        "skus": [
            {"sku_id": "sku_clean_spray_lemon", "attributes": {"香味": "檸檬"}, "unit_price": 129, "unit_points": 13},
            {"sku_id": "sku_clean_spray_tea", "attributes": {"香味": "茶樹"}, "unit_price": 129, "unit_points": 13},
        ],
    },
    {
        "id": "prod_kitchen_wipes",
        "store_id": "store_miaojie",
        "category_id": "cat_cleaning",
        "name": "廚房紙巾抽取包（80抽）",
        "description": "厚實吸水，廚房清潔必備。",
        "product_type": "PHYSICAL",
        "image": None,
        "specs": [],
        "skus": [
            {"sku_id": "sku_kitchen_wipes_80", "attributes": {}, "unit_price": 79, "unit_points": 8},
        ],
    },
    {
        "id": "prod_vitamin_c",
        "store_id": "store_health_mart",
        "category_id": "cat_health",
        "compare_group_id": "cmp_vitamin_c",
        "name": "維他命C發泡錠",
        "description": "每錠含維他命C 1000mg，檸檬口味。",
        "product_type": "PHYSICAL",
        "image": None,
        "specs": [],
        "skus": [
            {"sku_id": "sku_vitamin_c_effervescent", "attributes": {}, "unit_price": 259, "unit_points": 26},
        ],
    },
    {
        "id": "prod_fish_oil",
        "store_id": "store_lohas_health",
        "category_id": "cat_health",
        "name": "魚油軟膠囊（60粒）",
        "description": "高濃度 Omega-3，每日一粒維持健康。",
        "product_type": "PHYSICAL",
        "image": None,
        "specs": [],
        "skus": [
            {"sku_id": "sku_fish_oil_60", "attributes": {}, "unit_price": 399, "unit_points": 40},
        ],
    },
    {
        "id": "prod_vitamin_c_lohas",
        "store_id": "store_lohas_health",
        "category_id": "cat_health",
        "compare_group_id": "cmp_vitamin_c",
        "name": "維他命C發泡錠",
        "description": "每錠含維他命C 1000mg，檸檬口味。",
        "product_type": "PHYSICAL",
        "image": None,
        "specs": [],
        "skus": [
            {"sku_id": "sku_vitamin_c_lohas", "attributes": {}, "unit_price": 239, "unit_points": 24},
        ],
    },
    {
        "id": "prod_vitamin_c_watsons",
        "store_id": "store_watsons",
        "category_id": "cat_health",
        "compare_group_id": "cmp_vitamin_c",
        "name": "維他命C發泡錠",
        "description": "每錠含維他命C 1000mg，檸檬口味。",
        "product_type": "PHYSICAL",
        "image": None,
        "specs": [],
        "skus": [
            {"sku_id": "sku_vitamin_c_watsons", "attributes": {}, "unit_price": 249, "unit_points": 25},
        ],
    },
    {
        "id": "prod_clean_spray_miaojie",
        "store_id": "store_miaojie",
        "category_id": "cat_cleaning",
        "compare_group_id": "cmp_clean_spray",
        "name": "多功能清潔噴霧 500ml",
        "description": "廚房、浴室皆可使用，天然配方溫和不傷手。",
        "product_type": "PHYSICAL",
        "image": None,
        "specs": [{"name": "香味", "options": ["檸檬", "茶樹"]}],
        "skus": [
            {"sku_id": "sku_clean_spray_miaojie_lemon", "attributes": {"香味": "檸檬"}, "unit_price": 119, "unit_points": 12},
            {"sku_id": "sku_clean_spray_miaojie_tea", "attributes": {"香味": "茶樹"}, "unit_price": 119, "unit_points": 12},
        ],
    },
    {
        "id": "prod_clean_spray_carrefour",
        "store_id": "store_carrefour",
        "category_id": "cat_cleaning",
        "compare_group_id": "cmp_clean_spray",
        "name": "多功能清潔噴霧 500ml",
        "description": "廚房、浴室皆可使用，天然配方溫和不傷手。",
        "product_type": "PHYSICAL",
        "image": None,
        "specs": [{"name": "香味", "options": ["檸檬", "茶樹"]}],
        "skus": [
            {"sku_id": "sku_clean_spray_carrefour_lemon", "attributes": {"香味": "檸檬"}, "unit_price": 109, "unit_points": 11},
            {"sku_id": "sku_clean_spray_carrefour_tea", "attributes": {"香味": "茶樹"}, "unit_price": 109, "unit_points": 11},
        ],
    },
    {
        "id": "prod_tumbler_daiso",
        "store_id": "store_daiso",
        "category_id": "cat_daily",
        "compare_group_id": "cmp_tumbler",
        "name": "不鏽鋼保溫杯 500ml",
        "description": "12 小時保冷、6 小時保溫，附背帶。",
        "product_type": "PHYSICAL",
        "image": None,
        "specs": [{"name": "顏色", "options": ["粉", "藍"]}],
        "skus": [
            {"sku_id": "sku_tumbler_daiso_pink", "attributes": {"顏色": "粉"}, "unit_price": 490, "unit_points": 49},
            {"sku_id": "sku_tumbler_daiso_blue", "attributes": {"顏色": "藍"}, "unit_price": 490, "unit_points": 49},
        ],
    },
    {
        "id": "prod_tumbler_watsons",
        "store_id": "store_watsons",
        "category_id": "cat_daily",
        "compare_group_id": "cmp_tumbler",
        "name": "不鏽鋼保溫杯 500ml",
        "description": "12 小時保冷、6 小時保溫，附背帶。",
        "product_type": "PHYSICAL",
        "image": None,
        "specs": [{"name": "顏色", "options": ["粉", "藍"]}],
        "skus": [
            {"sku_id": "sku_tumbler_watsons_pink", "attributes": {"顏色": "粉"}, "unit_price": 550, "unit_points": 55},
            {"sku_id": "sku_tumbler_watsons_blue", "attributes": {"顏色": "藍"}, "unit_price": 550, "unit_points": 55},
        ],
    },
    {
        "id": "prod_mic_fifine_k669b",
        "store_id": "store_fifine_official",
        "category_id": "cat_electronics",
        "name": "FIFINE K669B USB 電容式麥克風",
        "description": "入門首選 USB 麥克風，即插即用，適合新手錄音、線上會議、簡易 podcast。",
        "product_type": "PHYSICAL",
        "image": None,
        "specs": [],
        "skus": [{"sku_id": "sku_mic_fifine_k669b", "attributes": {}, "unit_price": 990, "unit_points": 99}],
        "tags": ["麥克風", "USB麥克風", "入門", "podcast", "直播", "預算有限"],
    },
    {
        "id": "prod_mic_blue_yeti_x",
        "store_id": "store_blue_mic_tw",
        "category_id": "cat_electronics",
        "name": "Blue Yeti X USB 電容式麥克風",
        "description": "業界經典 podcast 麥克風，四種指向模式切換，含即時混音耳機孔，音質細膩。",
        "product_type": "PHYSICAL",
        "image": None,
        "specs": [],
        "skus": [{"sku_id": "sku_mic_blue_yeti_x", "attributes": {}, "unit_price": 4590, "unit_points": 459}],
        "tags": ["麥克風", "USB麥克風", "podcast", "直播", "電容式", "多指向模式", "高音質"],
    },
    {
        "id": "prod_mic_rode_nt_usb_mini",
        "store_id": "store_rode_tw",
        "category_id": "cat_electronics",
        "name": "Rode NT-USB Mini 電容式麥克風",
        "description": "體積小巧、磁吸防震架設計，適合空間有限的錄音桌，聲音乾淨自然。",
        "product_type": "PHYSICAL",
        "image": None,
        "specs": [],
        "skus": [{"sku_id": "sku_mic_rode_nt_usb_mini", "attributes": {}, "unit_price": 2690, "unit_points": 269}],
        "tags": ["麥克風", "USB麥克風", "podcast", "輕便", "磁吸防震架", "乾淨收音"],
    },
    {
        "id": "prod_mic_hyperx_quadcast_s",
        "store_id": "store_hyperx_tw",
        "category_id": "cat_electronics",
        "name": "HyperX QuadCast S USB 麥克風",
        "description": "RGB 燈效電競麥克風，四指向模式，內建防震架與防噴罩，直播/podcast 兩相宜。",
        "product_type": "PHYSICAL",
        "image": None,
        "specs": [],
        "skus": [{"sku_id": "sku_mic_hyperx_quadcast_s", "attributes": {}, "unit_price": 5980, "unit_points": 598}],
        "tags": ["麥克風", "USB麥克風", "直播", "電競", "RGB", "podcast", "防噴罩"],
    },
    {
        "id": "prod_mic_atr2100x_usb",
        "store_id": "store_audio_technica_tw",
        "category_id": "cat_electronics",
        "name": "Audio-Technica ATR2100x-USB 動圈式麥克風",
        "description": "USB／XLR 雙介面動圈式麥克風，抗環境噪音佳，適合雙人訪談型 podcast 或戶外收音。",
        "product_type": "PHYSICAL",
        "image": None,
        "specs": [],
        "skus": [{"sku_id": "sku_mic_atr2100x_usb", "attributes": {}, "unit_price": 3280, "unit_points": 328}],
        "tags": ["麥克風", "動圈式", "USB", "XLR", "雙訪談", "podcast", "抗噪"],
    },
    {
        "id": "prod_webcam_logitech_c920",
        "store_id": "store_logitech_tw",
        "category_id": "cat_electronics",
        "name": "羅技 C920 HD Pro 視訊鏡頭",
        "description": "1080p 全高清視訊鏡頭，適合視訊會議、直播與 podcast 錄影搭配使用。",
        "product_type": "PHYSICAL",
        "image": None,
        "specs": [],
        "skus": [{"sku_id": "sku_webcam_logitech_c920", "attributes": {}, "unit_price": 2190, "unit_points": 219}],
        "tags": ["視訊鏡頭", "webcam", "直播", "視訊會議", "1080p"],
    },
    {
        "id": "prod_audio_interface_scarlett_solo",
        "store_id": "store_pro_audio_tw",
        "category_id": "cat_electronics",
        "name": "Focusrite Scarlett Solo (Gen 4) 錄音介面",
        "description": "入門錄音介面，可接 XLR 麥克風做專業錄音，適合想升級成雙軌訪談 podcast 的使用者。",
        "product_type": "PHYSICAL",
        "image": None,
        "specs": [],
        "skus": [{"sku_id": "sku_audio_interface_scarlett_solo", "attributes": {}, "unit_price": 3480, "unit_points": 348}],
        "tags": ["錄音介面", "audio interface", "XLR", "podcast", "專業錄音"],
    },
]


def list_categories() -> list[dict]:
    return SHOP_CATEGORIES


def list_stores() -> list[dict]:
    return SHOP_STORES


def get_store(store_id: str) -> dict | None:
    return next((s for s in SHOP_STORES if s["id"] == store_id), None)


def list_products(*, category_id: str | None = None, store_id: str | None = None) -> list[dict]:
    products = SHOP_PRODUCTS
    if category_id is not None:
        products = [p for p in products if p["category_id"] == category_id]
    if store_id is not None:
        products = [p for p in products if p["store_id"] == store_id]
    return [
        {
            **p,
            "store_name": (get_store(p["store_id"]) or {}).get("name", ""),
            "compare_group_id": p.get("compare_group_id"),
            **shop_reviews.get_rating_summary(p["id"]),
        }
        for p in products
    ]


def get_product(product_id: str) -> dict | None:
    product = next((p for p in SHOP_PRODUCTS if p["id"] == product_id), None)
    if product is None:
        return None
    return {**product, **shop_reviews.get_rating_summary(product_id)}


def get_sku(sku_id: str) -> tuple[dict, dict] | None:
    for product in SHOP_PRODUCTS:
        for sku in product["skus"]:
            if sku["sku_id"] == sku_id:
                return product, sku
    return None


def list_compare_offers(group_id: str) -> list[dict]:
    offers = [
        {
            **p,
            "store_name": (get_store(p["store_id"]) or {}).get("name", ""),
            "min_unit_price": min(sku["unit_price"] for sku in p["skus"]),
        }
        for p in SHOP_PRODUCTS
        if p.get("compare_group_id") == group_id
    ]
    return sorted(offers, key=lambda o: o["min_unit_price"])


def find_compare_group_id_by_query(query: str) -> str | None:
    for p in SHOP_PRODUCTS:
        group_id = p.get("compare_group_id")
        if not group_id:
            continue
        name = p["name"]
        if name in query or query in name:
            return group_id
        # Users often shorten a product name to its leading noun (e.g. "維他命C"
        # for "維他命C發泡錠") and embed it mid-sentence ("我想比較維他命C的
        # 價格"); search for the name's leading core anywhere in the query
        # instead of requiring the full name or a query-start match.
        core_len = min(len(name), 4)
        core = name[:core_len]
        if core_len >= 3 and core in query:
            return group_id
    return None
