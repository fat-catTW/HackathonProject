"""Seed demo users' shop points balance.

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

DEMO_USER_STARTING_POINTS = {
    "user-vincent": 5000,
    "user-mei": 5000,
}


def main() -> None:
    for actor_id, points in DEMO_USER_STARTING_POINTS.items():
        current = STORE.get_user_points(actor_id)
        if current > 0:
            print(f"Skipped {actor_id}: already has {current} points.")
            continue
        STORE.refund_user_points(actor_id, points)
        print(f"Seeded {actor_id} with {points} points.")


if __name__ == "__main__":
    main()
