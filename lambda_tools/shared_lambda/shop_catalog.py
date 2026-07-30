"""Static shop catalog: stores, dual-spec products, and their SKUs.

SKU stock is intentionally NOT part of this module — it is dynamic runtime
state (see store.py's get_sku_stock/decrement_sku_stock/restock_sku), because
this module's data is plain Python source and cannot be written to at
request time.
"""
from __future__ import annotations

SHOP_STORES: list[dict] = [
    {"id": "store_711_taipei", "name": "7-11 台北車站店", "category": "超商", "image": None},
    {"id": "store_uni_style", "name": "統一時代生活選物", "category": "百貨選物", "image": None},
]

SHOP_PRODUCTS: list[dict] = [
    {
        "id": "prod_tshirt_basic",
        "store_id": "store_uni_style",
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
        "name": "御飯糰任選兌換券",
        "description": "全台 7-11 門市御飯糰系列任選一顆，效期 14 天。",
        "product_type": "SERIAL_CODE",
        "image": None,
        "specs": [],
        "skus": [
            {"sku_id": "sku_onigiri_any", "attributes": {}, "unit_price": 35, "unit_points": 3},
        ],
    },
]


def list_stores() -> list[dict]:
    return SHOP_STORES


def get_store(store_id: str) -> dict | None:
    return next((s for s in SHOP_STORES if s["id"] == store_id), None)


def list_products(store_id: str | None = None) -> list[dict]:
    if store_id is None:
        return SHOP_PRODUCTS
    return [p for p in SHOP_PRODUCTS if p["store_id"] == store_id]


def get_product(product_id: str) -> dict | None:
    return next((p for p in SHOP_PRODUCTS if p["id"] == product_id), None)


def get_sku(sku_id: str) -> tuple[dict, dict] | None:
    for product in SHOP_PRODUCTS:
        for sku in product["skus"]:
            if sku["sku_id"] == sku_id:
                return product, sku
    return None
