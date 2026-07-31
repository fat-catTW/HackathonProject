# 商城購物：同商品跨店比價 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the shop (`shop_purchase`) sell the same physical product through multiple vendors at different prices, let users compare those prices in the shop UI, and let the AI butler answer "compare prices for X" in chat with a deep link into that comparison.

**Architecture:** Tag existing shop-catalog product records with a shared `compare_group_id` when they represent the same item sold by different vendors. No new entity layer — the order/cart/stock/points logic keeps operating on `sku_id` exactly as today. Add one read-only backend endpoint to fetch a comparison group, one embedded (mock-only) agent tool to answer chat price-compare queries, and frontend logic that collapses same-group product cards into one comparison entry point.

**Tech Stack:** Python 3.12 / FastAPI (backend), React + TypeScript + Vite + Tailwind (frontend), pytest (backend tests), vitest + @testing-library/react (frontend tests).

## Global Constraints

- Design source of truth: `docs/superpowers/specs/2026-07-31-shop-cross-vendor-price-comparison-design.md` — every task below implements one section of it.
- Do not touch order/cart/stock/points logic in `backend/app/services/shop.py` or `backend/app/services/store.py` — these only key off `sku_id` and are explicitly out of scope.
- `compare_product_prices` is a **mock-only** tool: it must be added to `_EMBEDDED_TOOLS` in `backend/app/agent/tools.py` only, never to the Lambda/MCP name-lookup tables (`_invoke_lambda`, `_gateway_tool_name`) and no lambda handler is created for it — this mirrors the existing `shop_purchase` precedent of not touching that pipeline.
- `backend/app/services/shop_catalog.py` and `lambda_tools/shared_lambda/shop_catalog.py` are two independently-maintained copies of the same static data and must stay byte-for-byte identical in their `SHOP_CATEGORIES` / `SHOP_STORES` / `SHOP_PRODUCTS` contents (existing project convention).
- Every new product's `unit_points` follows the existing convention of ~10% of `unit_price`, rounded to the nearest integer.
- Chinese UI copy must match existing tone (no English strings introduced in the shop or chat UI).

---

## File Structure Overview

| File | Responsibility |
|---|---|
| `backend/app/services/shop_catalog.py` | Static catalog data + `list_compare_offers` / `find_compare_group_id_by_query` |
| `lambda_tools/shared_lambda/shop_catalog.py` | Mirror of the above |
| `lambda_tools/tests/test_get_shop_products_handler.py` | Existing hardcoded product-count assertion, needs updating |
| `backend/scripts/seed_shop_points.py` | Unchanged code, re-run once to seed stock for new SKUs |
| `backend/app/api/shop.py` | New `GET /api/shop/compare/{group_id}` endpoint |
| `backend/tests/test_shop_api.py` | Endpoint tests |
| `backend/tests/test_shop_catalog.py` | Catalog data + helper-function tests |
| `backend/app/services/catalog.py` | New `shop_price_compare` service entry |
| `backend/app/agent/tools.py` | New embedded tool `compare_product_prices` |
| `backend/app/agent/agent.py` | New interception branch + `_answer_price_compare` |
| `backend/tests/test_shop_price_compare.py` | New: service registration, tool, agent-interception tests |
| `frontend/src/types/shop.ts` | `ShopProduct.compare_group_id`, new `ShopCompareOffer` / `ShopCompareGroup` |
| `frontend/src/api/shop.ts` | New `getShopCompareGroup` |
| `frontend/src/pages/ShopFlowPage.tsx` | Grouped product cards, comparison offer list, deep-link handling |
| `frontend/src/pages/ShopFlowPage.test.tsx` | New comparison + deep-link tests, existing fixtures updated |

---

### Task 1: Backend catalog data — new stores, comparison groups, helper functions

**Files:**
- Modify: `backend/app/services/shop_catalog.py`
- Test: `backend/tests/test_shop_catalog.py`

**Interfaces:**
- Produces: `shop_catalog.list_compare_offers(group_id: str) -> list[dict]` (each dict is a product dict plus `store_name: str` and `min_unit_price: int`, sorted ascending by `min_unit_price`; empty list if `group_id` matches nothing)
- Produces: `shop_catalog.find_compare_group_id_by_query(query: str) -> str | None`
- Produces: `SHOP_PRODUCTS` entries gain an optional `compare_group_id: str` key; `list_products()` output always includes a `compare_group_id` key (`None` when absent)

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_shop_catalog.py`:

```python
def test_list_compare_offers_sorted_by_price_ascending():
    offers = shop_catalog.list_compare_offers("cmp_vitamin_c")
    assert len(offers) == 3
    prices = [o["min_unit_price"] for o in offers]
    assert prices == sorted(prices)
    assert prices[0] == 239


def test_list_compare_offers_unknown_group_returns_empty_list():
    assert shop_catalog.list_compare_offers("does_not_exist") == []


def test_list_compare_offers_includes_store_name():
    offers = shop_catalog.list_compare_offers("cmp_clean_spray")
    assert all(o["store_name"] for o in offers)


def test_find_compare_group_id_by_query_matches_partial_name():
    assert shop_catalog.find_compare_group_id_by_query("維他命C") == "cmp_vitamin_c"
    assert shop_catalog.find_compare_group_id_by_query("我想比較維他命C發泡錠的價格") == "cmp_vitamin_c"


def test_find_compare_group_id_by_query_no_match_returns_none():
    assert shop_catalog.find_compare_group_id_by_query("完全不相關的字串xyz") is None


def test_find_compare_group_id_by_query_ignores_products_without_a_group():
    assert shop_catalog.find_compare_group_id_by_query("御飯糰任選兌換券") is None


def test_products_without_compare_group_id_report_none():
    products = shop_catalog.list_products()
    ungrouped = next(p for p in products if p["id"] == "prod_daiso_storage_box")
    assert ungrouped["compare_group_id"] is None


def test_three_categories_each_have_one_comparison_group_of_three_vendors():
    for group_id, category_id in (
        ("cmp_vitamin_c", "cat_health"),
        ("cmp_clean_spray", "cat_cleaning"),
        ("cmp_tumbler", "cat_daily"),
    ):
        offers = shop_catalog.list_compare_offers(group_id)
        assert len(offers) == 3
        assert all(o["category_id"] == category_id for o in offers)
        assert len({o["store_id"] for o in offers}) == 3
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_shop_catalog.py -v`
Expected: the 8 new tests FAIL (`AttributeError: module 'shop_catalog' has no attribute 'list_compare_offers'` or similar; `test_products_without_compare_group_id_report_none` fails with `KeyError`).

- [ ] **Step 3: Add the two new stores**

In `backend/app/services/shop_catalog.py`, modify the `SHOP_STORES` list (currently lines 18-29) by adding two entries before the closing `]`:

```python
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
]
```

- [ ] **Step 4: Tag the 3 existing products with `compare_group_id`**

Modify the `prod_tumbler` entry (add one key, everything else unchanged):

```python
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
```

Modify the `prod_clean_spray` entry:

```python
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
```

Modify the `prod_vitamin_c` entry:

```python
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
```

- [ ] **Step 5: Add the 6 new comparison-group product entries**

Add these 6 dicts at the end of `SHOP_PRODUCTS`, right before its closing `]` (after `prod_fish_oil`):

```python
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
```

- [ ] **Step 6: Make `list_products()` always report `compare_group_id`**

Modify `list_products()` (currently lines 225-234):

```python
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
        }
        for p in products
    ]
```

- [ ] **Step 7: Add the two new helper functions**

Append at the end of `backend/app/services/shop_catalog.py` (after `get_sku`):

```python
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
        if p["name"] in query or query in p["name"]:
            return group_id
    return None
```

- [ ] **Step 8: Run the tests to verify they pass**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_shop_catalog.py -v`
Expected: all tests PASS (existing + 8 new).

- [ ] **Step 9: Commit**

```bash
git add backend/app/services/shop_catalog.py backend/tests/test_shop_catalog.py
git commit -m "feat(shop): add cross-vendor comparison groups to catalog data"
```

---

### Task 2: Sync the lambda_tools catalog mirror

**Files:**
- Modify: `lambda_tools/shared_lambda/shop_catalog.py`
- Modify: `lambda_tools/tests/test_get_shop_products_handler.py`

**Interfaces:**
- Consumes: nothing new (mirrors Task 1's data verbatim)
- Produces: `lambda_tools/shared_lambda/shop_catalog.py` byte-identical `SHOP_CATEGORIES` / `SHOP_STORES` / `SHOP_PRODUCTS` content to `backend/app/services/shop_catalog.py`

- [ ] **Step 1: Add the two new stores**

`lambda_tools/shared_lambda/shop_catalog.py` has the identical file structure to `backend/app/services/shop_catalog.py`. Modify its `SHOP_STORES` list (currently lines 18-29) the same way:

```python
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
]
```

- [ ] **Step 2: Tag the 3 existing products with `compare_group_id`**

Modify the `prod_tumbler` entry:

```python
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
```

Modify the `prod_clean_spray` entry:

```python
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
```

Modify the `prod_vitamin_c` entry:

```python
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
```

- [ ] **Step 3: Add the 6 new comparison-group product entries**

Add these 6 dicts at the end of `SHOP_PRODUCTS`, right before its closing `]` (after `prod_fish_oil`):

```python
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
```

- [ ] **Step 4: Make `list_products()` always report `compare_group_id`**

Modify `list_products()` (currently lines 225-234):

```python
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
        }
        for p in products
    ]
```

- [ ] **Step 5: Add the two new helper functions**

Append at the end of `lambda_tools/shared_lambda/shop_catalog.py` (after `get_sku`):

```python
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
        if p["name"] in query or query in p["name"]:
            return group_id
    return None
```

- [ ] **Step 6: Update the hardcoded product-count assertion**

In `lambda_tools/tests/test_get_shop_products_handler.py`, the total product count grows from 13 to 19 (6 new comparison-group products added):

```python
def test_lambda_handler_returns_all_products_without_filter():
    result = lambda_handler({}, None)
    assert result["success"] is True
    assert len(result["products"]) == 19
```

- [ ] **Step 7: Run the lambda_tools tests**

Run: `backend\.venv\Scripts\python.exe -m pytest lambda_tools/tests/test_get_shop_products_handler.py -v`
Expected: both tests PASS.

- [ ] **Step 8: Re-seed local stock for the new SKUs**

Run: `backend\.venv\Scripts\python.exe backend\scripts\seed_shop_points.py`
Expected: output includes lines like `Seeded sku_vitamin_c_lohas with 20 in stock.`, `Seeded sku_vitamin_c_watsons with 20 in stock.`, `Seeded sku_clean_spray_miaojie_lemon with 20 in stock.`, etc. for all 10 new SKUs (2 per new product × 3 products with 2 specs, + 2 single-sku products = 2+2+2+2+1+1 = 10 new SKUs), and `Skipped ...` for the pre-existing ones.

- [ ] **Step 9: Commit**

```bash
git add lambda_tools/shared_lambda/shop_catalog.py lambda_tools/tests/test_get_shop_products_handler.py
git commit -m "chore(shop): sync lambda_tools catalog mirror with comparison groups"
```

---

### Task 3: Backend comparison API endpoint

**Files:**
- Modify: `backend/app/api/shop.py`
- Test: `backend/tests/test_shop_api.py`

**Interfaces:**
- Consumes: `shop_catalog.list_compare_offers(group_id: str) -> list[dict]` (Task 1)
- Produces: `GET /api/shop/compare/{group_id}` → `200 {"group_id": str, "category_id": str, "offers": list[dict]}` or `404 {"success": false, "error": {"code": "COMPARE_GROUP_NOT_FOUND", "message": str}}`

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_shop_api.py`:

```python
def test_get_shop_compare_group_returns_offers_sorted_by_price():
    client = TestClient(app)
    response = client.get("/api/shop/compare/cmp_vitamin_c")
    assert response.status_code == 200
    body = response.json()
    assert body["group_id"] == "cmp_vitamin_c"
    assert body["category_id"] == "cat_health"
    offers = body["offers"]
    assert len(offers) == 3
    prices = [o["min_unit_price"] for o in offers]
    assert prices == sorted(prices)


def test_get_shop_compare_group_unknown_id_returns_404():
    client = TestClient(app)
    response = client.get("/api/shop/compare/does_not_exist")
    assert response.status_code == 404
    assert response.json()["detail"]["error"]["code"] == "COMPARE_GROUP_NOT_FOUND"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_shop_api.py -v`
Expected: both new tests FAIL with 404 Not Found (route doesn't exist yet).

- [ ] **Step 3: Add the endpoint**

In `backend/app/api/shop.py`, add after `get_shop_product` (currently ends at line 37, before `get_my_shop_points`):

```python
@router.get("/api/shop/compare/{group_id}")
def get_shop_compare_group(group_id: str) -> dict:
    offers = shop_catalog.list_compare_offers(group_id)
    if not offers:
        _raise_api_error(404, "COMPARE_GROUP_NOT_FOUND", "找不到這組比價商品")
    return {"group_id": group_id, "category_id": offers[0]["category_id"], "offers": offers}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_shop_api.py -v`
Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/shop.py backend/tests/test_shop_api.py
git commit -m "feat(shop): add GET /api/shop/compare/{group_id} endpoint"
```

---

### Task 4: Chat price-compare service (catalog entry, embedded tool, agent interception)

**Files:**
- Modify: `backend/app/services/catalog.py`
- Modify: `backend/app/agent/tools.py`
- Modify: `backend/app/agent/agent.py`
- Test: `backend/tests/test_shop_price_compare.py` (new file)

**Interfaces:**
- Consumes: `shop_catalog.find_compare_group_id_by_query` / `shop_catalog.list_compare_offers` (Task 1)
- Produces: `tools.call("compare_product_prices", {"query": str})` → `{"success": True, "group_id": str, "product_name": str, "offers": [{"store_name": str, "unit_price": int}, ...]}` (ascending by price) or `{"success": False, "error": {"code": str, "message": str}}`
- Produces: `agent.handle_message(...)` replies with a price-comparison summary and `redirect_path == f"/services/shop_purchase?compare={group_id}"` when the user's message is detected as `shop_price_compare` intent

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_shop_price_compare.py`:

```python
"""Tests for cross-vendor price comparison: service registration, the embedded
compare_product_prices tool, and the agent's chat interception."""
from unittest.mock import patch

from backend.app.agent import agent, tools
from backend.app.services import catalog


def test_shop_price_compare_registered_in_service_list():
    services = catalog.list_services()
    ids = [s["id"] for s in services]
    assert "shop_price_compare" in ids


def test_shop_price_compare_schema_has_single_query_field():
    schema = catalog.get_service_schema("shop_price_compare")
    field_ids = [f["id"] for f in schema["fields"]]
    assert field_ids == ["query"]


def test_embedded_compare_tool_requires_query():
    result = tools.call("compare_product_prices", {"query": ""})
    assert result["success"] is False
    assert result["error"]["code"] == "INVALID_QUERY"


def test_embedded_compare_tool_returns_offers_sorted_ascending():
    result = tools.call("compare_product_prices", {"query": "維他命C發泡錠"})
    assert result["success"] is True
    assert result["group_id"] == "cmp_vitamin_c"
    assert result["product_name"] == "維他命C發泡錠"
    prices = [o["unit_price"] for o in result["offers"]]
    assert prices == sorted(prices)
    assert prices[0] == 239


def test_embedded_compare_tool_not_found():
    result = tools.call("compare_product_prices", {"query": "完全不相關的字串xyz"})
    assert result["success"] is False
    assert result["error"]["code"] == "PRODUCT_NOT_FOUND"


def test_agent_detects_price_compare_and_replies_with_redirect():
    state = agent.new_state()

    with patch(
        "backend.app.agent.agent._available_services",
        return_value=[
            {
                "id": "shop_price_compare",
                "name": "商品比價",
                "description": "說出想比價的商品名稱，馬上看到各店家價格",
            }
        ],
    ):
        result = agent.handle_message("user-1", "sess-1", state, "我想比價維他命C發泡錠")

    assert result["state"]["service_id"] is None
    assert result["state"]["request_id"] is None
    assert result["redirect_path"] == "/services/shop_purchase?compare=cmp_vitamin_c"
    assert "健康藥妝" in result["reply"] or "樂活保健" in result["reply"]
    assert "最便宜" in result["reply"]


def test_agent_price_compare_not_found_has_no_redirect():
    state = agent.new_state()

    with patch(
        "backend.app.agent.agent._available_services",
        return_value=[
            {
                "id": "shop_price_compare",
                "name": "商品比價",
                "description": "說出想比價的商品名稱，馬上看到各店家價格",
            }
        ],
    ):
        result = agent.handle_message("user-1", "sess-1", state, "我想比價完全不相關的字串xyz")

    assert result["redirect_path"] is None
    assert result["state"]["service_id"] is None
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_shop_price_compare.py -v`
Expected: all 7 tests FAIL (service not registered, tool unknown, agent doesn't recognize the intent).

- [ ] **Step 3: Register the `shop_price_compare` service**

In `backend/app/services/catalog.py`, add a new entry to the `SERVICES` list, right after the `shop_purchase` entry (currently ending at line 358, before `restaurant_reservation`):

```python
    {
        "id": "shop_price_compare",
        "name": "商品比價",
        "description": "說出想比價的商品名稱，馬上看到各店家價格",
        "service_vendor_id": None,
        "cms_type": None,
        "enabled": True,
        "keywords": ["比價", "比較價格", "哪裡最便宜", "哪家最便宜", "最便宜", "價格比較"],
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
```

- [ ] **Step 4: Add the embedded tool**

In `backend/app/agent/tools.py`, add the import (modify the existing import line near the top):

```python
from ..services import catalog, health_catalog, health_recommendation, shop_catalog
```

Add the handler function after `_embedded_get_product_nutrition` (currently ending at line 134, before `_embedded_get_page_context`):

```python
def _embedded_compare_product_prices(params: dict) -> dict:
    query = str(params.get("query") or "").strip()
    if not query:
        return {
            "success": False,
            "error": {"code": "INVALID_QUERY", "message": "query is required."},
        }
    group_id = shop_catalog.find_compare_group_id_by_query(query)
    if not group_id:
        return {
            "success": False,
            "error": {"code": "PRODUCT_NOT_FOUND", "message": f"找不到「{query}」的比價商品"},
        }
    offers = shop_catalog.list_compare_offers(group_id)
    return {
        "success": True,
        "group_id": group_id,
        "product_name": offers[0]["name"],
        "offers": [
            {"store_name": o["store_name"], "unit_price": o["min_unit_price"]}
            for o in offers
        ],
    }
```

Register it in `_EMBEDDED_TOOLS` (currently lines 505-513):

```python
_EMBEDDED_TOOLS = {
    "list_services": _embedded_list_services,
    "get_service_schema": _embedded_get_service_schema,
    "submit_service_request": _embedded_submit_service_request,
    "get_page_context": _embedded_get_page_context,
    "search_pages": _embedded_search_pages,
    "recommend_products_by_health_need": _embedded_recommend_products_by_health_need,
    "get_product_nutrition": _embedded_get_product_nutrition,
    "compare_product_prices": _embedded_compare_product_prices,
}
```

Do **not** add `"compare_product_prices"` to `_invoke_lambda`'s `function_names` dict or to `_gateway_tool_name`'s `names` dict (Global Constraints).

- [ ] **Step 5: Add the agent interception**

In `backend/app/agent/agent.py`, add the helper function after `_answer_health_recommendation` (currently ending at line 1358, before `_format_health_nutrition_reply`):

```python
def _answer_price_compare(query: str, auth_token: str | None) -> tuple[str, str | None]:
    result = tools.call("compare_product_prices", {"query": query}, auth_token=auth_token)
    if not result.get("success"):
        return f"抱歉，沒有找到「{query}」的比價資訊，要不要換個商品名稱再試一次？", None
    offers = result["offers"]
    lines = [f"「{result['product_name']}」目前有 {len(offers)} 家店販售："]
    for index, offer in enumerate(offers):
        tag = "（最便宜）" if index == 0 else ""
        lines.append(f"　{offer['store_name']} NT${offer['unit_price']}{tag}")
    lines.append("我幫你打開比價頁面，可以直接選店家下單。")
    return "\n".join(lines), f"/services/shop_purchase?compare={result['group_id']}"
```

Modify `handle_message`'s existing `shop_purchase` interception block (currently lines 979-992) to add the new branch right after it:

```python
        if service_id == "shop_purchase":
            # shop_purchase is a dedicated multi-step flow (store -> product/spec
            # -> cart -> checkout/points) built for the ShopFlowPage UI, not
            # conversational field collection — redirect instead of collecting fields.
            state["service_id"] = None
            state["service_name"] = None
            state["service_schema"] = None
            state["collected_fields"] = {}
            state["missing_fields"] = []
            return _reply(
                state,
                "商城購物需要挑選商品類型、規格和購物車，這部分請到「商城購物」頁面操作會更方便，我幫你導過去囉！",
                redirect_path="/services/shop_purchase",
            )

        if service_id == "shop_price_compare":
            # One-shot query-and-answer service (like health_product_recommendation):
            # answer directly with a price summary instead of collecting form fields.
            reply, redirect_path = _answer_price_compare(text, auth_token)
            state["service_id"] = None
            state["service_name"] = None
            state["service_schema"] = None
            state["collected_fields"] = {}
            state["missing_fields"] = []
            return _reply(state, reply, redirect_path=redirect_path)
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_shop_price_compare.py -v`
Expected: all 7 tests PASS.

- [ ] **Step 7: Run the full backend test suite to check for regressions**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests -v`
Expected: all tests PASS (no regressions in `test_shop_catalog.py`, `test_shop_service.py`, `test_shop_api.py`, `test_health_recommendation.py`, or agent submit tests).

- [ ] **Step 8: Commit**

```bash
git add backend/app/services/catalog.py backend/app/agent/tools.py backend/app/agent/agent.py backend/tests/test_shop_price_compare.py
git commit -m "feat(shop): add chat price-compare intent with deep-link redirect"
```

---

### Task 5: Frontend — grouped product cards and comparison offer list

**Files:**
- Modify: `frontend/src/types/shop.ts`
- Modify: `frontend/src/api/shop.ts`
- Modify: `frontend/src/pages/ShopFlowPage.tsx`
- Modify: `frontend/src/pages/ShopFlowPage.test.tsx`

**Interfaces:**
- Consumes: `GET /api/shop/compare/{group_id}` (Task 3)
- Produces: `ShopProduct.compare_group_id: string | null`; `ShopCompareOffer` (= `ShopProduct` + `min_unit_price: number`); `ShopCompareGroup { group_id: string; category_id: string; offers: ShopCompareOffer[] }`; `getShopCompareGroup(groupId: string): Promise<ShopCompareGroup>`

- [ ] **Step 1: Update types**

In `frontend/src/types/shop.ts`, modify `ShopProduct` to add the new field:

```ts
export interface ShopProduct {
  id: string;
  store_id: string;
  store_name: string;
  category_id: string;
  compare_group_id: string | null;
  name: string;
  description: string;
  product_type: "PHYSICAL" | "SERIAL_CODE";
  image: string | null;
  specs: ShopSpec[];
  skus: ShopSku[];
}
```

Add after `ShopCategory`:

```ts
export interface ShopCompareOffer extends ShopProduct {
  min_unit_price: number;
}

export interface ShopCompareGroup {
  group_id: string;
  category_id: string;
  offers: ShopCompareOffer[];
}
```

- [ ] **Step 2: Add the API client function**

In `frontend/src/api/shop.ts`, add after `listShopProducts`:

```ts
export function getShopCompareGroup(groupId: string): Promise<ShopCompareGroup> {
  return api(`/api/shop/compare/${encodeURIComponent(groupId)}`);
}
```

Add `ShopCompareGroup` to the existing type import at the top of the file:

```ts
import type {
  ShopCategory,
  ShopCompareGroup,
  ShopOrder,
  ShopPointsBalance,
  ShopProduct,
  ShopStore,
  ShopSubmitPayload,
  ShopSubmitResult,
} from "../types/shop";
```

- [ ] **Step 3: Update existing test fixtures for the new required field**

In `frontend/src/pages/ShopFlowPage.test.tsx`, add `compare_group_id: null` to all three existing mock product objects (`prod_a`, `prod_b`, `prod_c`):

```ts
const products = [
  {
    id: "prod_a",
    store_id: "store_a",
    store_name: "A 店家",
    category_id: "cat_beverage",
    compare_group_id: null,
    name: "商品 A",
    description: "描述 A",
    product_type: "SERIAL_CODE" as const,
    image: null,
    specs: [],
    skus: [{ sku_id: "sku_a", attributes: {}, unit_price: 50, unit_points: 5 }],
  },
  {
    id: "prod_b",
    store_id: "store_b",
    store_name: "B 店家",
    category_id: "cat_beverage",
    compare_group_id: null,
    name: "商品 B",
    description: "描述 B",
    product_type: "SERIAL_CODE" as const,
    image: null,
    specs: [],
    skus: [{ sku_id: "sku_b", attributes: {}, unit_price: 80, unit_points: 8 }],
  },
];

const dailyProducts = [
  {
    id: "prod_c",
    store_id: "store_c",
    store_name: "C 店家",
    category_id: "cat_daily",
    compare_group_id: null,
    name: "商品 C",
    description: "描述 C",
    product_type: "PHYSICAL" as const,
    image: null,
    specs: [],
    skus: [{ sku_id: "sku_c", attributes: {}, unit_price: 100, unit_points: 10 }],
  },
];
```

- [ ] **Step 4: Write the failing comparison tests**

Add to `frontend/src/pages/ShopFlowPage.test.tsx`, inside the existing `describe("ShopFlowPage", ...)` block:

```ts
const comparableProducts = [
  {
    id: "prod_x1",
    store_id: "store_x1",
    store_name: "X1 店家",
    category_id: "cat_daily",
    compare_group_id: "cmp_x",
    name: "比價商品",
    description: "描述 X",
    product_type: "PHYSICAL" as const,
    image: null,
    specs: [],
    skus: [{ sku_id: "sku_x1", attributes: {}, unit_price: 100, unit_points: 10 }],
  },
  {
    id: "prod_x2",
    store_id: "store_x2",
    store_name: "X2 店家",
    category_id: "cat_daily",
    compare_group_id: "cmp_x",
    name: "比價商品",
    description: "描述 X",
    product_type: "PHYSICAL" as const,
    image: null,
    specs: [],
    skus: [{ sku_id: "sku_x2", attributes: {}, unit_price: 80, unit_points: 8 }],
  },
];

it("combines identical products from different vendors into one comparison card", async () => {
  const user = userEvent.setup();
  vi.mocked(shopApi.listShopProducts).mockResolvedValue({ products: comparableProducts });
  renderPage();

  await user.click(await screen.findByText("飲品兌換"));

  expect(await screen.findByText("比價商品")).toBeInTheDocument();
  expect(screen.getByText("NT$80~100")).toBeInTheDocument();
  expect(screen.getByText("共 2 家店販售")).toBeInTheDocument();
  expect(screen.queryByText("X1 店家")).not.toBeInTheDocument();
});

it("opens a per-vendor price list when a comparison card is clicked, cheapest offer first", async () => {
  const user = userEvent.setup();
  vi.mocked(shopApi.listShopProducts).mockResolvedValue({ products: comparableProducts });
  renderPage();

  await user.click(await screen.findByText("飲品兌換"));
  await user.click(await screen.findByText("比價商品"));

  const offerRows = await screen.findAllByText(/店家/);
  expect(offerRows.length).toBeGreaterThanOrEqual(2);
  expect(screen.getByText("X2 店家")).toBeInTheDocument();
  expect(screen.getByText("X1 店家")).toBeInTheDocument();
  expect(screen.getByText("最便宜")).toBeInTheDocument();
});

it("selecting a vendor from the comparison list opens the normal add-to-cart panel", async () => {
  const user = userEvent.setup();
  vi.mocked(shopApi.listShopProducts).mockResolvedValue({ products: comparableProducts });
  renderPage();

  await user.click(await screen.findByText("飲品兌換"));
  await user.click(await screen.findByText("比價商品"));

  const selectButtons = await screen.findAllByText("選這家");
  await user.click(selectButtons[0]);

  expect(await screen.findByText("加入購物車（NT$80）")).toBeInTheDocument();
});
```

- [ ] **Step 5: Run the tests to verify they fail**

Run: `cd frontend && npm test -- ShopFlowPage.test.tsx`
Expected: the 3 new tests FAIL (cards render one-per-product today, no grouping, no "選這家").

- [ ] **Step 6: Add `comparingGroupId` state**

In `frontend/src/pages/ShopFlowPage.tsx`, modify the state declarations block (currently lines 39-41):

```ts
  const [products, setProducts] = useState<ShopProduct[]>([]);
  const [activeProduct, setActiveProduct] = useState<ShopProduct | null>(null);
  const [comparingGroupId, setComparingGroupId] = useState<string | null>(null);
  const [selectedSpecs, setSelectedSpecs] = useState<Record<string, string>>({});
```

- [ ] **Step 7: Add the grouping logic**

Add this interface at module level, next to the existing `CartEntry` interface (currently lines 21-30, before `export function ShopFlowPage()`):

```ts
interface ProductGroup {
  groupKey: string;
  offers: (ShopProduct & { min_unit_price: number })[];
}
```

Add these two hooks inside the component, right after the existing `matchedSku` useMemo (currently ending at line 89, before `const [pendingQuantity, setPendingQuantity] = useState(1);`):

```ts
  const productGroups = useMemo<ProductGroup[]>(() => {
    const groups = new Map<string, (ShopProduct & { min_unit_price: number })[]>();
    for (const product of products) {
      const withPrice = { ...product, min_unit_price: Math.min(...product.skus.map((s) => s.unit_price)) };
      const key = product.compare_group_id ?? product.id;
      const existing = groups.get(key);
      if (existing) existing.push(withPrice);
      else groups.set(key, [withPrice]);
    }
    return Array.from(groups.entries()).map(([groupKey, offers]) => ({
      groupKey,
      offers: offers.sort((a, b) => a.min_unit_price - b.min_unit_price),
    }));
  }, [products]);

  const comparingOffers = useMemo(() => {
    if (!comparingGroupId) return [];
    return productGroups.find((g) => g.groupKey === comparingGroupId)?.offers ?? [];
  }, [productGroups, comparingGroupId]);
```

- [ ] **Step 8: Clear `comparingGroupId` when leaving the product step**

Modify the Step 1 category card `onClick` (currently lines 223-226):

```tsx
                  onClick={() => {
                    setSelectedCategoryId(category.id);
                    setComparingGroupId(null);
                    goNext();
                  }}
```

- [ ] **Step 9: Replace the Step 2 product list rendering**

Replace the product-list `<div>` inside the `step === "product"` section (currently lines 240-261):

```tsx
            <div className="flex flex-col gap-3">
              {productGroups.map((group) => {
                if (group.offers.length > 1) {
                  const prices = group.offers.map((o) => o.min_unit_price);
                  return (
                    <button
                      key={group.groupKey}
                      type="button"
                      onClick={() => {
                        setComparingGroupId(group.groupKey);
                        setActiveProduct(null);
                        setSelectedSpecs({});
                        setPendingQuantity(1);
                      }}
                      className="rounded-2xl border-2 border-[var(--color-border)] p-4 text-left transition hover:border-[var(--color-primary)]"
                    >
                      <p className="text-base font-bold text-[var(--color-foreground)]">{group.offers[0].name}</p>
                      <p className="text-sm text-[var(--color-muted-foreground)]">
                        NT${Math.min(...prices)}~{Math.max(...prices)}
                      </p>
                      <p className="text-xs text-[var(--color-muted-foreground)]">共 {group.offers.length} 家店販售</p>
                    </button>
                  );
                }
                const product = group.offers[0];
                return (
                  <button
                    key={group.groupKey}
                    type="button"
                    onClick={() => {
                      setActiveProduct(product);
                      setComparingGroupId(null);
                      setSelectedSpecs({});
                      setPendingQuantity(1);
                    }}
                    className={`rounded-2xl border-2 p-4 text-left transition ${
                      activeProduct?.id === product.id
                        ? "border-brand bg-brand/5"
                        : "border-[var(--color-border)] hover:border-[var(--color-primary)]"
                    }`}
                  >
                    <p className="text-base font-bold text-[var(--color-foreground)]">{product.name}</p>
                    <p className="text-sm text-[var(--color-muted-foreground)]">NT${product.skus[0]?.unit_price}</p>
                    <p className="text-xs text-[var(--color-muted-foreground)]">{product.store_name}</p>
                  </button>
                );
              })}
            </div>

            {comparingGroupId && (
              <div className="flex flex-col gap-3 rounded-xl border border-[var(--color-border)] p-4">
                <p className="text-base font-bold text-[var(--color-foreground)]">
                  {comparingOffers[0]?.name} 比價
                </p>
                {comparingOffers.map((offer, index) => (
                  <div
                    key={offer.id}
                    className="flex items-center justify-between rounded-xl border border-[var(--color-border)] px-4 py-3"
                  >
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-[var(--color-foreground)]">{offer.store_name}</span>
                      {index === 0 && (
                        <span className="rounded-full bg-[var(--color-success-soft)] px-2 py-0.5 text-xs font-bold text-[var(--color-success)]">
                          最便宜
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-sm font-bold text-[var(--color-foreground)]">NT${offer.min_unit_price}</span>
                      <button
                        type="button"
                        onClick={() => {
                          setActiveProduct(offer);
                          setComparingGroupId(null);
                          setSelectedSpecs({});
                          setPendingQuantity(1);
                        }}
                        className="min-h-[44px] rounded-full bg-brand px-4 py-2 text-sm font-bold text-[var(--color-on-primary)]"
                      >
                        選這家
                      </button>
                    </div>
                  </div>
                ))}
                <button
                  type="button"
                  onClick={() => setComparingGroupId(null)}
                  className="text-sm text-[var(--color-muted-foreground)] underline"
                >
                  返回商品列表
                </button>
              </div>
            )}
```

- [ ] **Step 10: Clear `comparingGroupId` on the "返回選品類" button**

Modify the back button in the Step 2 footer (currently lines 322-329):

```tsx
              <button
                type="button"
                onClick={() => {
                  goBack();
                  setComparingGroupId(null);
                }}
                className="min-h-[44px] flex-1 rounded-2xl border-2 border-brand px-6 py-4 text-base font-bold text-brand"
              >
                返回選品類
              </button>
```

- [ ] **Step 11: Run the tests to verify they pass**

Run: `cd frontend && npm test -- ShopFlowPage.test.tsx`
Expected: all tests PASS (existing 4 + new 3).

- [ ] **Step 12: Commit**

```bash
git add frontend/src/types/shop.ts frontend/src/api/shop.ts frontend/src/pages/ShopFlowPage.tsx frontend/src/pages/ShopFlowPage.test.tsx
git commit -m "feat(shop): group cross-vendor products into a comparison offer list"
```

---

### Task 6: Frontend — `?compare=` deep link

**Files:**
- Modify: `frontend/src/pages/ShopFlowPage.tsx`
- Modify: `frontend/src/pages/ShopFlowPage.test.tsx`

**Interfaces:**
- Consumes: `getShopCompareGroup(groupId: string): Promise<ShopCompareGroup>` (Task 5); `comparingGroupId` state and `productGroups` (Task 5)
- Produces: visiting `/services/shop_purchase?compare=<group_id>` opens directly to Step 2 with that group's comparison list expanded

- [ ] **Step 1: Write the failing test**

Add to `frontend/src/pages/ShopFlowPage.test.tsx`. This test needs a custom render helper because it requires a non-default route, so add it near the top of the file (after `renderPage`):

```ts
function renderPageAtRoute(route: string) {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <ShopFlowPage />
    </MemoryRouter>,
  );
}
```

Add the test itself inside the `describe` block:

```ts
it("opens directly to the comparison list when the URL has a compare param", async () => {
  vi.mocked(shopApi.getShopCompareGroup).mockResolvedValue({
    group_id: "cmp_x",
    category_id: "cat_daily",
    offers: comparableProducts.map((p) => ({ ...p, min_unit_price: p.skus[0].unit_price })),
  });
  vi.mocked(shopApi.listShopProducts).mockResolvedValue({ products: comparableProducts });

  renderPageAtRoute("/services/shop_purchase?compare=cmp_x");

  expect(await screen.findByText("X2 店家")).toBeInTheDocument();
  expect(screen.getByText("X1 店家")).toBeInTheDocument();
  expect(screen.getByText("最便宜")).toBeInTheDocument();
  expect(screen.queryByText("請選擇商品類型")).not.toBeInTheDocument();
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd frontend && npm test -- ShopFlowPage.test.tsx`
Expected: the new test FAILS (`shopApi.getShopCompareGroup` is not called; page stays on Step 1 category selection since `?compare=` is ignored today).

- [ ] **Step 3: Import `useSearchParams` and `getShopCompareGroup`**

Modify the react-router-dom import in `frontend/src/pages/ShopFlowPage.tsx` (currently line 2):

```ts
import { useNavigate, useSearchParams } from "react-router-dom";
```

Modify the `shop` API import (currently lines 7-15) to add `getShopCompareGroup`:

```ts
import {
  cancelShopOrder,
  getShopCompareGroup,
  getShopOrder,
  getShopPoints,
  listShopCategories,
  listShopProducts,
  simulateShopOrderProgress,
  submitShopOrder,
} from "../api/shop";
```

- [ ] **Step 4: Add the deep-link effect**

Add inside the `ShopFlowPage` component, right after the `navigate` declaration (currently line 33):

```ts
  const [searchParams] = useSearchParams();
```

Add a new `useEffect` right after the existing categories/points-loading effect (currently ending at line 58, before the `selectedCategoryId` effect):

```ts
  useEffect(() => {
    const groupId = searchParams.get("compare");
    if (!groupId) return;
    getShopCompareGroup(groupId)
      .then((group) => {
        setSelectedCategoryId(group.category_id);
        setComparingGroupId(group.group_id);
        setStepIndex(STEP_ORDER.indexOf("product"));
      })
      .catch(() => setToastText("比價資料載入失敗"));
    // Runs once on mount to consume the initial URL; the compare param
    // isn't re-read on subsequent in-app navigation.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `cd frontend && npm test -- ShopFlowPage.test.tsx`
Expected: all tests PASS (existing 7 + new 1).

- [ ] **Step 6: Run the full frontend test suite to check for regressions**

Run: `cd frontend && npm test`
Expected: all tests PASS.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/pages/ShopFlowPage.tsx frontend/src/pages/ShopFlowPage.test.tsx
git commit -m "feat(shop): open comparison list directly via ?compare= deep link"
```

---

## Final Verification

- [ ] Run the full backend suite: `backend\.venv\Scripts\python.exe -m pytest backend/tests lambda_tools/tests -v` — all PASS
- [ ] Run the full frontend suite: `cd frontend && npm test` — all PASS
- [ ] Manually smoke-test: start backend (`uvicorn app.main:app --reload` from `backend/`) and frontend (`npm run dev` from `frontend/`), log in, open 商城購物 → 保健營養品 → confirm "維他命C發泡錠" shows as one card with a price range and "共 3 家店販售", clicking it shows 3 vendors sorted by price with "最便宜" on the cheapest, and selecting one leads to the normal add-to-cart flow
- [ ] Manually smoke-test chat: open the AI 管家 panel, type "我想比價維他命C發泡錠", confirm the reply lists 3 vendor prices with the cheapest flagged, and that following the redirect opens the shop directly on that comparison list
