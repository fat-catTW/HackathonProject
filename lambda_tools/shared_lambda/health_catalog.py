"""Shared health product catalog and DynamoDB helpers for Lambda tool handlers.

Mirrors backend/app/services/health_catalog.py — duplicated here because
lambda_tools is packaged and deployed separately from backend (see
docs/mcp-gateway-lambda-setup.md), same convention as RESTAURANTS /
DELIVERY_STORES in shared_lambda/catalog.py.
"""
from __future__ import annotations

from .catalog import dynamodb_table

PRODUCTS: list[dict] = [
    {"id": "P001", "name": "雞胸沙拉", "category": "鮮食", "price": 89, "calories": 210, "protein_g": 25, "carbs_g": 8, "fat_g": 9, "sodium_mg": 320, "tags": ["高蛋白", "低碳", "減脂"], "allergens": ["蛋"]},
    {"id": "P002", "name": "舒肥雞胸便當", "category": "鮮食", "price": 99, "calories": 380, "protein_g": 35, "carbs_g": 40, "fat_g": 6, "sodium_mg": 480, "tags": ["高蛋白", "增肌", "均衡"], "allergens": []},
    {"id": "P003", "name": "溏心蛋", "category": "鮮食", "price": 25, "calories": 78, "protein_g": 6, "carbs_g": 1, "fat_g": 5, "sodium_mg": 190, "tags": ["高蛋白", "低碳", "生酮友善"], "allergens": ["蛋"]},
    {"id": "P004", "name": "涼拌豆腐", "category": "鮮食", "price": 45, "calories": 120, "protein_g": 10, "carbs_g": 6, "fat_g": 6, "sodium_mg": 380, "tags": ["素食", "高蛋白", "低碳"], "allergens": ["大豆"]},
    {"id": "P005", "name": "地瓜", "category": "鮮食", "price": 35, "calories": 130, "protein_g": 2, "carbs_g": 30, "fat_g": 0.2, "sodium_mg": 10, "tags": ["低脂", "高纖", "原型食物"], "allergens": []},
    {"id": "P006", "name": "無糖豆漿", "category": "飲品", "price": 25, "calories": 90, "protein_g": 7, "carbs_g": 6, "fat_g": 3, "sodium_mg": 15, "tags": ["素食", "低糖", "高蛋白"], "allergens": ["大豆"]},
    {"id": "P007", "name": "拿鐵咖啡", "category": "飲品", "price": 55, "calories": 150, "protein_g": 6, "carbs_g": 12, "fat_g": 8, "sodium_mg": 90, "tags": ["一般"], "allergens": ["奶"]},
    {"id": "P008", "name": "全糖珍珠奶茶", "category": "飲品", "price": 65, "calories": 520, "protein_g": 4, "carbs_g": 95, "fat_g": 12, "sodium_mg": 180, "tags": ["高糖", "高熱量"], "allergens": ["奶", "大豆"]},
    {"id": "P009", "name": "香蕉燕麥棒", "category": "零食", "price": 35, "calories": 180, "protein_g": 4, "carbs_g": 32, "fat_g": 5, "sodium_mg": 60, "tags": ["高纖", "素食"], "allergens": ["麩質", "堅果"]},
    {"id": "P010", "name": "巧克力可頌", "category": "麵包", "price": 45, "calories": 320, "protein_g": 6, "carbs_g": 34, "fat_g": 18, "sodium_mg": 280, "tags": ["高糖", "高脂"], "allergens": ["麩質", "奶", "蛋"]},
    {"id": "P011", "name": "全麥吐司", "category": "麵包", "price": 40, "calories": 210, "protein_g": 8, "carbs_g": 38, "fat_g": 3, "sodium_mg": 320, "tags": ["高纖", "低脂"], "allergens": ["麩質"]},
    {"id": "P012", "name": "關東煮蘿蔔+蛋", "category": "鮮食", "price": 40, "calories": 140, "protein_g": 8, "carbs_g": 10, "fat_g": 6, "sodium_mg": 520, "tags": ["低脂", "高鈉"], "allergens": ["蛋"]},
    {"id": "P013", "name": "鹽酥雞", "category": "熱食", "price": 79, "calories": 480, "protein_g": 22, "carbs_g": 30, "fat_g": 30, "sodium_mg": 890, "tags": ["高鈉", "高脂", "高熱量"], "allergens": []},
    {"id": "P014", "name": "御飯糰(鮭魚)", "category": "鮮食", "price": 35, "calories": 180, "protein_g": 6, "carbs_g": 35, "fat_g": 2, "sodium_mg": 380, "tags": ["低脂", "均衡"], "allergens": ["魚"]},
    {"id": "P015", "name": "毛豆", "category": "鮮食", "price": 30, "calories": 140, "protein_g": 12, "carbs_g": 10, "fat_g": 6, "sodium_mg": 320, "tags": ["素食", "高蛋白", "高纖"], "allergens": ["大豆"]},
    {"id": "P016", "name": "洋芋片", "category": "零食", "price": 45, "calories": 340, "protein_g": 4, "carbs_g": 34, "fat_g": 22, "sodium_mg": 420, "tags": ["高鈉", "高脂"], "allergens": []},
    {"id": "P017", "name": "無糖優格", "category": "鮮食", "price": 55, "calories": 100, "protein_g": 10, "carbs_g": 8, "fat_g": 3, "sodium_mg": 60, "tags": ["高蛋白", "低糖", "益生菌"], "allergens": ["奶"]},
    {"id": "P018", "name": "生菜沙拉(和風醬)", "category": "鮮食", "price": 69, "calories": 90, "protein_g": 3, "carbs_g": 12, "fat_g": 4, "sodium_mg": 480, "tags": ["低卡", "低脂", "高鈉"], "allergens": []},
    {"id": "P019", "name": "茶葉蛋", "category": "鮮食", "price": 15, "calories": 78, "protein_g": 6, "carbs_g": 1, "fat_g": 5, "sodium_mg": 250, "tags": ["高蛋白", "低碳"], "allergens": ["蛋"]},
    {"id": "P020", "name": "溫泉蛋", "category": "鮮食", "price": 15, "calories": 70, "protein_g": 6, "carbs_g": 0.5, "fat_g": 5, "sodium_mg": 65, "tags": ["高蛋白", "低碳", "生酮友善"], "allergens": ["蛋"]},
    {"id": "P021", "name": "五穀飯糰", "category": "鮮食", "price": 35, "calories": 220, "protein_g": 5, "carbs_g": 42, "fat_g": 3, "sodium_mg": 290, "tags": ["高纖", "原型食物"], "allergens": ["麩質"]},
    {"id": "P022", "name": "藜麥雞胸沙拉", "category": "鮮食", "price": 109, "calories": 260, "protein_g": 28, "carbs_g": 18, "fat_g": 7, "sodium_mg": 350, "tags": ["高蛋白", "低碳", "減脂", "高纖"], "allergens": []},
    {"id": "P023", "name": "咖哩雞肉便當", "category": "鮮食", "price": 99, "calories": 520, "protein_g": 26, "carbs_g": 68, "fat_g": 15, "sodium_mg": 780, "tags": ["均衡", "高鈉"], "allergens": ["麩質"]},
    {"id": "P024", "name": "義大利肉醬麵", "category": "鮮食", "price": 89, "calories": 480, "protein_g": 18, "carbs_g": 62, "fat_g": 16, "sodium_mg": 820, "tags": ["高鈉", "均衡"], "allergens": ["麩質", "蛋"]},
    {"id": "P025", "name": "關東煮昆布卷", "category": "鮮食", "price": 20, "calories": 60, "protein_g": 2, "carbs_g": 8, "fat_g": 1, "sodium_mg": 380, "tags": ["低脂", "低卡"], "allergens": ["大豆"]},
    {"id": "P026", "name": "鮪魚御飯糰", "category": "鮮食", "price": 30, "calories": 190, "protein_g": 7, "carbs_g": 34, "fat_g": 3, "sodium_mg": 400, "tags": ["低脂", "均衡"], "allergens": ["魚", "蛋"]},
    {"id": "P027", "name": "雙拼便當(雞腿+滷蛋)", "category": "鮮食", "price": 89, "calories": 650, "protein_g": 32, "carbs_g": 70, "fat_g": 24, "sodium_mg": 920, "tags": ["高鈉", "高熱量", "均衡"], "allergens": ["蛋", "麩質"]},
    {"id": "P028", "name": "可爾必思", "category": "飲品", "price": 30, "calories": 140, "protein_g": 2, "carbs_g": 32, "fat_g": 0, "sodium_mg": 40, "tags": ["高糖"], "allergens": ["奶"]},
    {"id": "P029", "name": "舒跑", "category": "飲品", "price": 25, "calories": 90, "protein_g": 0, "carbs_g": 22, "fat_g": 0, "sodium_mg": 230, "tags": ["高糖", "電解質"], "allergens": []},
    {"id": "P030", "name": "無糖綠茶", "category": "飲品", "price": 20, "calories": 0, "protein_g": 0, "carbs_g": 0, "fat_g": 0, "sodium_mg": 10, "tags": ["低糖", "無糖"], "allergens": []},
    {"id": "P031", "name": "CITY CAFE美式咖啡", "category": "飲品", "price": 35, "calories": 5, "protein_g": 0, "carbs_g": 1, "fat_g": 0, "sodium_mg": 5, "tags": ["低卡", "無糖"], "allergens": []},
    {"id": "P032", "name": "生乳卷", "category": "甜點", "price": 65, "calories": 310, "protein_g": 5, "carbs_g": 32, "fat_g": 18, "sodium_mg": 85, "tags": ["高糖", "高脂"], "allergens": ["奶", "蛋", "麩質"]},
    {"id": "P033", "name": "布丁", "category": "甜點", "price": 30, "calories": 160, "protein_g": 4, "carbs_g": 22, "fat_g": 6, "sodium_mg": 90, "tags": ["高糖"], "allergens": ["奶", "蛋"]},
    {"id": "P034", "name": "起司蛋糕", "category": "甜點", "price": 75, "calories": 350, "protein_g": 6, "carbs_g": 28, "fat_g": 24, "sodium_mg": 220, "tags": ["高糖", "高脂"], "allergens": ["奶", "蛋", "麩質"]},
    {"id": "P035", "name": "堅果棒", "category": "零食", "price": 40, "calories": 190, "protein_g": 5, "carbs_g": 20, "fat_g": 10, "sodium_mg": 70, "tags": ["高纖", "素食"], "allergens": ["堅果"]},
    {"id": "P036", "name": "烤地瓜球", "category": "零食", "price": 35, "calories": 160, "protein_g": 2, "carbs_g": 34, "fat_g": 1, "sodium_mg": 30, "tags": ["高纖", "低脂", "原型食物"], "allergens": []},
    {"id": "P037", "name": "大亨堡熱狗", "category": "熱食", "price": 55, "calories": 280, "protein_g": 12, "carbs_g": 22, "fat_g": 16, "sodium_mg": 680, "tags": ["高鈉", "高脂"], "allergens": ["麩質"]},
    {"id": "P038", "name": "玉米濃湯", "category": "熱食", "price": 35, "calories": 140, "protein_g": 4, "carbs_g": 20, "fat_g": 5, "sodium_mg": 580, "tags": ["高鈉"], "allergens": ["奶", "麩質"]},
]


def _product_from_item(item: dict) -> dict:
    return {
        "id": item["id"],
        "name": item["name"],
        "category": item["category"],
        "price": int(item["price"]),
        "calories": int(item["calories"]),
        "protein_g": float(item["protein_g"]),
        "carbs_g": float(item["carbs_g"]),
        "fat_g": float(item["fat_g"]),
        "sodium_mg": int(item["sodium_mg"]),
        "tags": list(item.get("tags", [])),
        "allergens": list(item.get("allergens", [])),
    }


def list_products() -> list[dict]:
    from boto3.dynamodb.conditions import Attr

    try:
        table = dynamodb_table()
        items: list[dict] = []
        start_key = None
        while True:
            kwargs = {"FilterExpression": Attr("entity_type").eq("PRODUCT")}
            if start_key:
                kwargs["ExclusiveStartKey"] = start_key
            response = table.scan(**kwargs)
            items.extend(response.get("Items", []))
            start_key = response.get("LastEvaluatedKey")
            if not start_key:
                break
        if items:
            return [_product_from_item(item) for item in items]
    except Exception:
        pass
    return [dict(product) for product in PRODUCTS]


def get_product(product_id: str) -> dict | None:
    try:
        item = dynamodb_table().get_item(Key={"PK": f"PRODUCT#{product_id}", "SK": "METADATA"}).get("Item")
    except Exception:
        item = None
    if item:
        return _product_from_item(item)
    return next((dict(product) for product in PRODUCTS if product["id"] == product_id), None)
