"""Seed demo users' shop points balance and initial SKU stock.

Unlike seed_food_delivery_catalog.py (which writes straight to DynamoDB via
get_aws_resource, meant to run once against a deployed table), this script
uses the STORE singleton from backend/app/services/store.py, which
auto-selects MemoryStore (mock/local) or DynamoDBStore based on USE_MOCK —
so this script works in both local dev and against a real deployment.

Run from repo root: backend\\.venv\\Scripts\\python.exe backend\\scripts\\seed_shop_points.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.app.services.store import STORE
from backend.app.services import shop_catalog

DEMO_USER_STARTING_POINTS = {
    "user-vincent": 5000,
    "user-mei": 5000,
}

DEMO_SKU_STARTING_STOCK = 20


def seed_points() -> None:
    for actor_id, points in DEMO_USER_STARTING_POINTS.items():
        current = STORE.get_user_points(actor_id)
        if current > 0:
            print(f"Skipped {actor_id}: already has {current} points.")
            continue
        STORE.refund_user_points(actor_id, points)
        print(f"Seeded {actor_id} with {points} points.")


def seed_stock() -> None:
    for product in shop_catalog.SHOP_PRODUCTS:
        for sku in product["skus"]:
            sku_id = sku["sku_id"]
            current = STORE.get_sku_stock(sku_id)
            if current > 0:
                print(f"Skipped {sku_id}: already has {current} in stock.")
                continue
            STORE.restock_sku(sku_id, DEMO_SKU_STARTING_STOCK)
            print(f"Seeded {sku_id} with {DEMO_SKU_STARTING_STOCK} in stock.")


def main() -> None:
    seed_points()
    seed_stock()


if __name__ == "__main__":
    main()
