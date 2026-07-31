"""Static shop catalog: categories, stores, dual-spec products, and their SKUs.

SKU stock is intentionally NOT part of this module — it is dynamic runtime
state (see store.py's get_sku_stock/decrement_sku_stock/restock_sku), because
this module's data is plain Python source and cannot be written to at
request time.
"""
from __future__ import annotations

SHOP_CATEGORIES: list[dict] = [
    {"id": "cat_beverage", "name": "飲品兌換"},
    {"id": "cat_food", "name": "美食兌換"},
    {"id": "cat_daily", "name": "生活日用品"},
    {"id": "cat_cleaning", "name": "居家清潔用品"},
    {"id": "cat_health", "name": "保健營養品"},
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
]


def list_categories() -> list[dict]:
    return SHOP_CATEGORIES


def list_stores() -> list[dict]:
    return SHOP_STORES


def get_store(store_id: str) -> dict | None:
    return next((s for s in SHOP_STORES if s["id"] == store_id), None)


def list_products(category_id: str | None = None, store_id: str | None = None) -> list[dict]:
    products = SHOP_PRODUCTS
    if category_id is not None:
        products = [p for p in products if p["category_id"] == category_id]
    if store_id is not None:
        products = [p for p in products if p["store_id"] == store_id]
    return [
        {**p, "store_name": (get_store(p["store_id"]) or {}).get("name", "")}
        for p in products
    ]


def get_product(product_id: str) -> dict | None:
    return next((p for p in SHOP_PRODUCTS if p["id"] == product_id), None)


def get_sku(sku_id: str) -> tuple[dict, dict] | None:
    for product in SHOP_PRODUCTS:
        for sku in product["skus"]:
            if sku["sku_id"] == sku_id:
                return product, sku
    return None
