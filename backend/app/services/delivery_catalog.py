"""Static delivery store directory for the food delivery feature."""

DELIVERY_STORES: list[dict] = [
    {
        "id": "store-001",
        "name": "好味道便當",
        "address": "台北市大安區忠孝東路四段100號",
        "cuisine": "便當",
        "image": None,
        "url": "",
        "menu": [
            {"id": "item-001", "title": "招牌雞腿便當", "price": 110, "modifier_group": [
                {"name": "加購", "options": [{"label": "加蛋", "price": 15}, {"label": "加滷肉", "price": 20}]}
            ]},
            {"id": "item-002", "title": "排骨便當", "price": 100, "modifier_group": [
                {"name": "加購", "options": [{"label": "加蛋", "price": 15}]}
            ]},
            {"id": "item-003", "title": "素食便當", "price": 90, "modifier_group": []},
        ],
    },
    {
        "id": "store-002",
        "name": "鮮茶道",
        "address": "台北市信義區松仁路28號",
        "cuisine": "飲料",
        "image": None,
        "url": "",
        "menu": [
            {"id": "item-010", "title": "珍珠奶茶（大）", "price": 65, "modifier_group": [
                {"name": "甜度", "options": [{"label": "全糖", "price": 0}, {"label": "半糖", "price": 0}, {"label": "無糖", "price": 0}]},
                {"name": "冰量", "options": [{"label": "正常冰", "price": 0}, {"label": "少冰", "price": 0}, {"label": "去冰", "price": 0}]},
            ]},
            {"id": "item-011", "title": "四季春茶（大）", "price": 40, "modifier_group": [
                {"name": "甜度", "options": [{"label": "全糖", "price": 0}, {"label": "半糖", "price": 0}, {"label": "無糖", "price": 0}]},
            ]},
            {"id": "item-012", "title": "冬瓜檸檬", "price": 55, "modifier_group": []},
        ],
    },
    {
        "id": "store-003",
        "name": "義式小館",
        "address": "台北市中山區南京東路二段50號",
        "cuisine": "義式料理",
        "image": None,
        "url": "",
        "menu": [
            {"id": "item-020", "title": "奶油培根義大利麵", "price": 180, "modifier_group": [
                {"name": "加購", "options": [{"label": "升級套餐（含湯＋飲料）", "price": 69}]}
            ]},
            {"id": "item-021", "title": "瑪格麗特披薩", "price": 220, "modifier_group": []},
            {"id": "item-022", "title": "凱薩沙拉", "price": 120, "modifier_group": []},
        ],
    },
]


def list_stores() -> list[dict]:
    return DELIVERY_STORES


def get_store(store_id: str) -> dict | None:
    return next((s for s in DELIVERY_STORES if s["id"] == store_id), None)
