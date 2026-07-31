# 商城購物：品類優先瀏覽 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把「商城購物」（`shop_purchase`）的瀏覽方式從「先選店家、再看該店商品」改成「先選商品品類、再看跨廠商同類商品」，購物車依廠商分組顯示。

**Architecture:** 後端 `shop_catalog.py` 新增品類靜態資料與 `category_id` 篩選，`list_products` 回傳附帶 `store_name`；新增 `GET /api/shop/categories`。前端 `ShopFlowPage.tsx` 的第一步從「選店家」改為「選品類」，第二步商品卡片顯示廠商名稱，購物車依廠商分組。訂單/庫存/點數服務層（`shop.py`/`store.py`）完全不變。`lambda_tools/shared_lambda/shop_catalog.py` 這份鏡射資料檔同步更新以維持既有慣例（兩份 catalog 檔案內容一致）。

**Tech Stack:** Python/FastAPI（backend）、TypeScript/React/Vite + Vitest + Testing Library（frontend）、pytest（backend tests）。

## Global Constraints

- 既有 4 樣商品的 `id`／`store_id`／`skus`（含所有 `sku_id`）完全不變，只新增 `category_id` 欄位 — 不可更動既有 `sku_id`，`test_shop_service.py` 依賴這些值。
- 運費維持「整張訂單只要有實體商品就加一次 60 元」，不依廠商分開計算。
- Lambda tool `get_shop_products`／`list_shop_stores` 的 handler 與 `tool_schemas/*.json` 不需要新增 `category_id` 篩選能力，只需同步 catalog 資料內容。
- 店家既有的 `category` 欄位（如「超商」「百貨選物」）保留不動。
- 每個新增步驟都要先寫失敗的測試，再寫最小實作讓測試通過（TDD）。

---

### Task 1: 後端 catalog 新增品類資料與 `category_id` 篩選

**Files:**
- Modify: `backend/app/services/shop_catalog.py`
- Test: `backend/tests/test_shop_catalog.py`

**Interfaces:**
- Produces: `shop_catalog.SHOP_CATEGORIES: list[dict]`（每筆 `{"id": str, "name": str}`）、`shop_catalog.list_categories() -> list[dict]`、`shop_catalog.list_products(category_id: str | None = None, store_id: str | None = None) -> list[dict]`（每筆商品字典新增 `store_name: str` 欄位）
- Consumes: 無（本任務是最底層資料層，其餘任務都依賴這裡的輸出）

- [ ] **Step 1: 寫失敗的測試**

在 `backend/tests/test_shop_catalog.py` 檔案最後面新增：

```python
def test_list_categories_returns_all_categories():
    categories = shop_catalog.list_categories()
    assert len(categories) >= 5
    assert all({"id", "name"} <= set(c.keys()) for c in categories)


def test_every_product_has_a_valid_category_id():
    category_ids = {c["id"] for c in shop_catalog.list_categories()}
    for product in shop_catalog.list_products():
        assert product["category_id"] in category_ids


def test_each_category_has_at_least_two_distinct_vendors():
    products = shop_catalog.list_products()
    for category in shop_catalog.list_categories():
        store_ids = {p["store_id"] for p in products if p["category_id"] == category["id"]}
        assert len(store_ids) >= 2, f"{category['id']} 底下廠商不足兩家"


def test_list_products_filtered_by_category():
    all_products = shop_catalog.list_products()
    category_id = all_products[0]["category_id"]
    filtered = shop_catalog.list_products(category_id=category_id)
    assert filtered
    assert all(p["category_id"] == category_id for p in filtered)


def test_list_products_includes_store_name():
    product = shop_catalog.list_products()[0]
    store = shop_catalog.get_store(product["store_id"])
    assert product["store_name"] == store["name"]
```

- [ ] **Step 2: 執行測試，確認失敗**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_shop_catalog.py -v`
Expected: 新增的 5 個測試 FAIL（`AttributeError: module has no attribute 'list_categories'` 或 `KeyError: 'category_id'`），其餘既有測試維持 PASS。

- [ ] **Step 3: 實作 — 改寫 `backend/app/services/shop_catalog.py`**

完整取代整個檔案內容為：

```python
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
```

**注意：** `list_products()` 現在回傳的字典每筆都多了 `store_name` 欄位（用 `{**p, "store_name": ...}` 產生新字典，不會改到 `SHOP_PRODUCTS` 原始資料）。`get_product()`／`get_sku()` 刻意不加這個欄位，維持原樣，因為呼叫端（`shop.py` 訂單邏輯、`get_shop_product` 單品 API）不需要它。

- [ ] **Step 4: 執行測試，確認全部通過**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_shop_catalog.py -v`
Expected: 全部 PASS（含既有的 `test_list_stores_returns_all_stores`、`test_every_product_belongs_to_a_real_store`、`test_sku_ids_are_globally_unique`、`test_physical_products_have_specs_matching_sku_attribute_keys` 等）。

- [ ] **Step 5: 確認訂單服務測試沒有被牽連**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_shop_service.py -v`
Expected: 全部 PASS（這支測試依賴的 `sku_id` 未變動，`list_products()` 回傳形狀新增欄位不影響 `get_sku()`）。

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/shop_catalog.py backend/tests/test_shop_catalog.py
git commit -m "feat(shop): add product categories and cross-vendor catalog data"
```

---

### Task 2: 後端 API — 新增品類端點、商品端點改用 `category_id`

**Files:**
- Modify: `backend/app/api/shop.py`
- Create: `backend/tests/test_shop_api.py`

**Interfaces:**
- Consumes: `shop_catalog.list_categories()`、`shop_catalog.list_products(category_id, store_id)`（Task 1 產出）
- Produces: `GET /api/shop/categories` → `{"categories": [...]}`；`GET /api/shop/products?category_id=...` → `{"products": [...]}`（`store_id` 參數仍保留可用）

- [ ] **Step 1: 寫失敗的測試**

建立 `backend/tests/test_shop_api.py`：

```python
from fastapi.testclient import TestClient

from backend.app.main import app


def test_list_shop_categories_returns_all_categories():
    client = TestClient(app)
    response = client.get("/api/shop/categories")
    assert response.status_code == 200
    categories = response.json()["categories"]
    assert len(categories) >= 5
    assert all({"id", "name"} <= set(c.keys()) for c in categories)


def test_list_shop_products_filtered_by_category_id():
    client = TestClient(app)
    all_products = client.get("/api/shop/products").json()["products"]
    category_id = all_products[0]["category_id"]

    response = client.get(f"/api/shop/products?category_id={category_id}")
    assert response.status_code == 200
    filtered = response.json()["products"]
    assert filtered
    assert all(p["category_id"] == category_id for p in filtered)
    assert all("store_name" in p for p in filtered)


def test_list_shop_products_filtered_by_store_id_still_works():
    client = TestClient(app)
    all_products = client.get("/api/shop/products").json()["products"]
    store_id = all_products[0]["store_id"]

    response = client.get(f"/api/shop/products?store_id={store_id}")
    assert response.status_code == 200
    filtered = response.json()["products"]
    assert filtered
    assert all(p["store_id"] == store_id for p in filtered)
```

- [ ] **Step 2: 執行測試，確認失敗**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_shop_api.py -v`
Expected: `test_list_shop_categories_returns_all_categories` FAIL（404，路由不存在）；其餘兩個 PASS（既有 `store_id` 篩選已經可用）— 確認新增的 categories 端點測試會先掛掉。

- [ ] **Step 3: 實作 — 修改 `backend/app/api/shop.py`**

在 `list_shop_stores` 之後（第 19 行後）新增一個路由：

```python
@router.get("/api/shop/categories")
def list_shop_categories() -> dict:
    return {"categories": shop_catalog.list_categories()}
```

把原本的 `list_shop_products` 函式：

```python
@router.get("/api/shop/products")
def list_shop_products(store_id: str | None = None) -> dict:
    return {"products": shop_catalog.list_products(store_id)}
```

改為：

```python
@router.get("/api/shop/products")
def list_shop_products(category_id: str | None = None, store_id: str | None = None) -> dict:
    return {"products": shop_catalog.list_products(category_id=category_id, store_id=store_id)}
```

- [ ] **Step 4: 執行測試，確認全部通過**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_shop_api.py -v`
Expected: 全部 PASS。

- [ ] **Step 5: 跑整個 backend 測試套件確認沒有回歸**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests -v`
Expected: 全部 PASS。

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/shop.py backend/tests/test_shop_api.py
git commit -m "feat(shop): add categories endpoint and category_id product filter"
```

---

### Task 3: 同步 `lambda_tools/shared_lambda/shop_catalog.py` 鏡射資料

**Files:**
- Modify: `lambda_tools/shared_lambda/shop_catalog.py`

**Interfaces:**
- Consumes: 無（純資料同步，鏡射 Task 1 寫入 `backend/app/services/shop_catalog.py` 的相同內容）
- Produces: 無新介面 — 這份檔案既有的 `list_stores()`／`list_products(store_id=None)`／`get_store()`／`get_product()`／`get_sku()` 簽章維持不變（見 Global Constraints：這裡不新增 `category_id` 篩選能力）

**背景：** 這份檔案是給 Lambda gateway tools（`list_shop_stores`／`get_shop_products` handler）用的獨立副本，跟 `backend/app/services/shop_catalog.py` 沒有 import 關係，是既有的「兩份分開維護」慣例（見 `docs/superpowers/specs/2026-07-30-shop-purchase-request-design.md`）。這裡沒有自動化測試涵蓋，用「跟 Task 1 的檔案逐行比對」的方式手動核對。

- [ ] **Step 1: 把 Task 1 完成後的 `backend/app/services/shop_catalog.py` 內容複製過來**

用 Task 1 Step 3 寫入 `backend/app/services/shop_catalog.py` 的完整內容，原封不動覆寫到 `lambda_tools/shared_lambda/shop_catalog.py`（兩個檔案內容應該逐字相同，包含 `SHOP_CATEGORIES`／`SHOP_STORES`／`SHOP_PRODUCTS`／所有函式）。

- [ ] **Step 2: 核對兩份檔案內容一致**

Run: `diff backend/app/services/shop_catalog.py lambda_tools/shared_lambda/shop_catalog.py`
Expected: 沒有輸出（兩份檔案完全相同）。

- [ ] **Step 3: 確認 lambda_tools 現有 handler 不會因為新增的 `SHOP_CATEGORIES`／`category_id` 而壞掉**

Run: `cd lambda_tools && python -c "from shared_lambda.shop_catalog import list_stores, list_products; print(len(list_stores())); print(len(list_products()))"`
Expected: 印出 `10` 與 `13`（10 家店、13 樣商品），不噴例外。

- [ ] **Step 4: Commit**

```bash
git add lambda_tools/shared_lambda/shop_catalog.py
git commit -m "chore(shop): sync lambda_tools shop catalog mirror with new categories"
```

---

### Task 4: 前端型別與 API client 更新

**Files:**
- Modify: `frontend/src/types/shop.ts`
- Modify: `frontend/src/api/shop.ts`

**Interfaces:**
- Consumes: Task 2 產出的 `GET /api/shop/categories`、`GET /api/shop/products?category_id=`
- Produces: `ShopCategory` 型別、`ShopProduct.category_id`／`ShopProduct.store_name`、`listShopCategories(): Promise<{ categories: ShopCategory[] }>`、`listShopProducts(categoryId?: string): Promise<{ products: ShopProduct[] }>`（後續 Task 5-7 的 `ShopFlowPage.tsx` 依賴這些型別與函式）

這個任務是純型別／API client 修改，沒有獨立的單元測試檔（型別正確性由 Task 7 的元件測試與 TypeScript 編譯把關），照既有專案慣例直接修改＋跑 typecheck 驗證。

- [ ] **Step 1: 修改 `frontend/src/types/shop.ts`**

在 `ShopStore` 介面之後新增：

```ts
export interface ShopCategory {
  id: string;
  name: string;
}
```

把 `ShopProduct` 介面：

```ts
export interface ShopProduct {
  id: string;
  store_id: string;
  name: string;
  description: string;
  product_type: "PHYSICAL" | "SERIAL_CODE";
  image: string | null;
  specs: ShopSpec[];
  skus: ShopSku[];
}
```

改為：

```ts
export interface ShopProduct {
  id: string;
  store_id: string;
  store_name: string;
  category_id: string;
  name: string;
  description: string;
  product_type: "PHYSICAL" | "SERIAL_CODE";
  image: string | null;
  specs: ShopSpec[];
  skus: ShopSku[];
}
```

- [ ] **Step 2: 修改 `frontend/src/api/shop.ts`**

在 `listShopStores` 之後新增：

```ts
export function listShopCategories(): Promise<{ categories: ShopCategory[] }> {
  return api("/api/shop/categories");
}
```

並記得在檔案頂端的 import 補上 `ShopCategory`：

```ts
import type {
  ShopCategory,
  ShopOrder,
  ShopPointsBalance,
  ShopProduct,
  ShopStore,
  ShopSubmitPayload,
  ShopSubmitResult,
} from "../types/shop";
```

把 `listShopProducts`：

```ts
export function listShopProducts(storeId?: string): Promise<{ products: ShopProduct[] }> {
  const query = storeId ? `?store_id=${encodeURIComponent(storeId)}` : "";
  return api(`/api/shop/products${query}`);
}
```

改為：

```ts
export function listShopProducts(categoryId?: string): Promise<{ products: ShopProduct[] }> {
  const query = categoryId ? `?category_id=${encodeURIComponent(categoryId)}` : "";
  return api(`/api/shop/products${query}`);
}
```

- [ ] **Step 3: 跑 TypeScript 編譯確認沒有型別錯誤（此時 `ShopFlowPage.tsx` 尚未更新，預期會有型別錯誤，這是正常的，先記錄下來供 Task 5-7 修正）**

Run: `cd frontend && npx tsc --noEmit`
Expected: `src/pages/ShopFlowPage.tsx` 出現型別錯誤（例如 `selectedStoreId` 相關或 `listShopProducts` 參數用法），這些會在 Task 5-7 修正。**不要**在這個任務嘗試修 `ShopFlowPage.tsx`，那是後面任務的範圍。

- [ ] **Step 4: Commit**

```bash
git add frontend/src/types/shop.ts frontend/src/api/shop.ts
git commit -m "feat(shop): add ShopCategory type and category-based product API client"
```

---

### Task 5: `ShopFlowPage.tsx` — 第一步改為「選品類」

**Files:**
- Modify: `frontend/src/pages/ShopFlowPage.tsx`
- Create: `frontend/src/pages/ShopFlowPage.test.tsx`

**Interfaces:**
- Consumes: `listShopCategories`／`listShopProducts(categoryId)`（Task 4 產出）、`ShopCategory`／`ShopProduct`（Task 4 產出）
- Produces: `ShopFlowPage` 元件的 `Step` 型別第一步改名為 `"category"`；內部 state `selectedCategoryId: string | null`（後續 Task 6、7 會沿用這個 state 名稱與 `stores`／`products` 的載入時機）

這個任務先把 Step 1 UI 與資料載入改掉，Step 2 的「顯示廠商名稱」與 Step 3 的「購物車分組」留給 Task 6、7，避免一次改動範圍太大。為了让 Task 5 的測試在 Step 2 仍是舊版 UI 的情況下也能通過，這裡先寫一個只涵蓋 Step 1 行為的測試。

- [ ] **Step 1: 寫失敗的測試**

建立 `frontend/src/pages/ShopFlowPage.test.tsx`：

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { ShopFlowPage } from "./ShopFlowPage";
import * as shopApi from "../api/shop";

vi.mock("../api/shop");

const categories = [
  { id: "cat_beverage", name: "飲品兌換" },
  { id: "cat_daily", name: "生活日用品" },
];

const products = [
  {
    id: "prod_a",
    store_id: "store_a",
    store_name: "A 店家",
    category_id: "cat_beverage",
    name: "商品 A",
    description: "描述 A",
    product_type: "SERIAL_CODE" as const,
    image: null,
    specs: [],
    skus: [{ sku_id: "sku_a", attributes: {}, unit_price: 50, unit_points: 5 }],
  },
];

function renderPage() {
  return render(
    <MemoryRouter>
      <ShopFlowPage />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.mocked(shopApi.listShopCategories).mockResolvedValue({ categories });
  vi.mocked(shopApi.listShopProducts).mockResolvedValue({ products });
  vi.mocked(shopApi.getShopPoints).mockResolvedValue({ balance: 0 });
});

describe("ShopFlowPage", () => {
  it("shows categories first, then fetches products for the selected category", async () => {
    const user = userEvent.setup();
    renderPage();

    expect(await screen.findByText("飲品兌換")).toBeInTheDocument();
    expect(screen.getByText("生活日用品")).toBeInTheDocument();
    expect(shopApi.listShopProducts).not.toHaveBeenCalled();

    await user.click(screen.getByText("飲品兌換"));

    expect(await screen.findByText("商品 A")).toBeInTheDocument();
    expect(shopApi.listShopProducts).toHaveBeenCalledWith("cat_beverage");
  });
});
```

- [ ] **Step 2: 執行測試，確認失敗**

Run: `cd frontend && npx vitest run src/pages/ShopFlowPage.test.tsx`
Expected: FAIL（目前頁面顯示的是店家清單「請選擇店家」而不是品類，`listShopCategories` 沒被呼叫）。

- [ ] **Step 3: 實作 — 修改 `frontend/src/pages/ShopFlowPage.tsx`**

把 import 區塊（第 6-15 行）：

```tsx
import {
  cancelShopOrder,
  getShopOrder,
  getShopPoints,
  listShopProducts,
  listShopStores,
  simulateShopOrderProgress,
  submitShopOrder,
} from "../api/shop";
import type { ShopCartLine, ShopOrder, ShopProduct, ShopStore, ShopSubmitResult } from "../types/shop";
```

改為：

```tsx
import {
  cancelShopOrder,
  getShopOrder,
  getShopPoints,
  listShopCategories,
  listShopProducts,
  simulateShopOrderProgress,
  submitShopOrder,
} from "../api/shop";
import type { ShopCartLine, ShopCategory, ShopOrder, ShopProduct, ShopSubmitResult } from "../types/shop";
```

把 `Step` 型別與 `STEP_ORDER`（第 17-18 行）：

```tsx
type Step = "store" | "product" | "cart" | "checkout" | "result";
const STEP_ORDER: Step[] = ["store", "product", "cart", "checkout", "result"];
```

改為：

```tsx
type Step = "category" | "product" | "cart" | "checkout" | "result";
const STEP_ORDER: Step[] = ["category", "product", "cart", "checkout", "result"];
```

把 state 區塊（第 34-38 行）：

```tsx
  const [stores, setStores] = useState<ShopStore[]>([]);
  const [selectedStoreId, setSelectedStoreId] = useState<string | null>(null);
  const [products, setProducts] = useState<ShopProduct[]>([]);
  const [activeProduct, setActiveProduct] = useState<ShopProduct | null>(null);
  const [selectedSpecs, setSelectedSpecs] = useState<Record<string, string>>({});
```

改為：

```tsx
  const [categories, setCategories] = useState<ShopCategory[]>([]);
  const [selectedCategoryId, setSelectedCategoryId] = useState<string | null>(null);
  const [products, setProducts] = useState<ShopProduct[]>([]);
  const [activeProduct, setActiveProduct] = useState<ShopProduct | null>(null);
  const [selectedSpecs, setSelectedSpecs] = useState<Record<string, string>>({});
```

把資料載入的 `useEffect`（第 52-60 行）：

```tsx
  useEffect(() => {
    listShopStores().then((res) => setStores(res.stores)).catch(() => setToastText("店家清單載入失敗"));
    getShopPoints().then((res) => setPointsBalance(res.balance)).catch(() => {});
  }, []);

  useEffect(() => {
    if (!selectedStoreId) return;
    listShopProducts(selectedStoreId).then((res) => setProducts(res.products)).catch(() => setToastText("商品清單載入失敗"));
  }, [selectedStoreId]);
```

改為：

```tsx
  useEffect(() => {
    listShopCategories().then((res) => setCategories(res.categories)).catch(() => setToastText("商品類型載入失敗"));
    getShopPoints().then((res) => setPointsBalance(res.balance)).catch(() => {});
  }, []);

  useEffect(() => {
    if (!selectedCategoryId) return;
    listShopProducts(selectedCategoryId).then((res) => setProducts(res.products)).catch(() => setToastText("商品清單載入失敗"));
  }, [selectedCategoryId]);
```

把 Step 1 的 JSX（第 193-214 行）：

```tsx
        {/* ====== Step 1: Store Selection ====== */}
        {step === "store" && (
          <section className="flex flex-col gap-4">
            <p className="text-base font-bold leading-relaxed text-slate-900">請選擇店家</p>
            <div className="flex flex-col gap-3">
              {stores.map((store) => (
                <button
                  key={store.id}
                  type="button"
                  onClick={() => {
                    setSelectedStoreId(store.id);
                    goNext();
                  }}
                  className="rounded-2xl border-2 border-slate-200 p-4 text-left transition hover:border-slate-300"
                >
                  <p className="text-base font-bold text-slate-900">{store.name}</p>
                  <p className="text-sm text-slate-500">{store.category}</p>
                </button>
              ))}
            </div>
          </section>
        )}
```

改為：

```tsx
        {/* ====== Step 1: Category Selection ====== */}
        {step === "category" && (
          <section className="flex flex-col gap-4">
            <p className="text-base font-bold leading-relaxed text-slate-900">請選擇商品類型</p>
            <div className="flex flex-col gap-3">
              {categories.map((category) => (
                <button
                  key={category.id}
                  type="button"
                  onClick={() => {
                    setSelectedCategoryId(category.id);
                    goNext();
                  }}
                  className="rounded-2xl border-2 border-slate-200 p-4 text-left transition hover:border-slate-300"
                >
                  <p className="text-base font-bold text-slate-900">{category.name}</p>
                </button>
              ))}
            </div>
          </section>
        )}
```

最後，Step 2 區塊的返回按鈕文案（第 301-308 行附近）「返回選店家」先改成「返回選品類」（其餘 Step 2 內容留給 Task 6）：

```tsx
              <button
                type="button"
                onClick={goBack}
                className="min-h-[44px] flex-1 rounded-2xl border-2 border-brand px-6 py-4 text-base font-bold text-brand"
              >
                返回選品類
              </button>
```

- [ ] **Step 4: 執行測試，確認通過**

Run: `cd frontend && npx vitest run src/pages/ShopFlowPage.test.tsx`
Expected: PASS。

- [ ] **Step 5: 跑 TypeScript 編譯確認沒有殘留的型別錯誤（`ShopStore`／`selectedStoreId`／`stores` 相關的殘留引用都應該已經清乾淨）**

Run: `cd frontend && npx tsc --noEmit`
Expected: 沒有錯誤（如果還有 `stores`／`selectedStoreId` 相關錯誤，代表 Step 3 有殘留沒改乾淨，回頭檢查）。

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/ShopFlowPage.tsx frontend/src/pages/ShopFlowPage.test.tsx
git commit -m "feat(shop): replace store-first browsing with category-first step 1"
```

---

### Task 6: `ShopFlowPage.tsx` — Step 2 商品卡片顯示廠商名稱

**Files:**
- Modify: `frontend/src/pages/ShopFlowPage.tsx`
- Modify: `frontend/src/pages/ShopFlowPage.test.tsx`

**Interfaces:**
- Consumes: `ShopProduct.store_name`（Task 4 產出）
- Produces: 無新介面，純 UI 顯示調整

- [ ] **Step 1: 在既有測試檔新增一個測試案例**

在 `frontend/src/pages/ShopFlowPage.test.tsx` 的 `describe("ShopFlowPage", ...)` 區塊內，既有的 `it(...)` 之後新增：

```tsx
  it("shows the vendor name on each product card", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(await screen.findByText("飲品兌換"));

    expect(await screen.findByText("商品 A")).toBeInTheDocument();
    expect(screen.getByText("A 店家")).toBeInTheDocument();
  });
```

- [ ] **Step 2: 執行測試，確認失敗**

Run: `cd frontend && npx vitest run src/pages/ShopFlowPage.test.tsx`
Expected: 新的測試 FAIL（畫面上目前沒有顯示 `store_name`）。

- [ ] **Step 3: 實作 — 修改 Step 2 的商品卡片 JSX**

把 Step 2 商品清單卡片（原本第 220-239 行附近）：

```tsx
              {products.map((product) => (
                <button
                  key={product.id}
                  type="button"
                  onClick={() => {
                    setActiveProduct(product);
                    setSelectedSpecs({});
                    setPendingQuantity(1);
                  }}
                  className={`rounded-2xl border-2 p-4 text-left transition ${
                    activeProduct?.id === product.id
                      ? "border-brand bg-brand/5"
                      : "border-slate-200 hover:border-slate-300"
                  }`}
                >
                  <p className="text-base font-bold text-slate-900">{product.name}</p>
                  <p className="text-sm text-slate-500">NT${product.skus[0]?.unit_price}</p>
                </button>
              ))}
```

改為：

```tsx
              {products.map((product) => (
                <button
                  key={product.id}
                  type="button"
                  onClick={() => {
                    setActiveProduct(product);
                    setSelectedSpecs({});
                    setPendingQuantity(1);
                  }}
                  className={`rounded-2xl border-2 p-4 text-left transition ${
                    activeProduct?.id === product.id
                      ? "border-brand bg-brand/5"
                      : "border-slate-200 hover:border-slate-300"
                  }`}
                >
                  <p className="text-base font-bold text-slate-900">{product.name}</p>
                  <p className="text-sm text-slate-500">NT${product.skus[0]?.unit_price}</p>
                  <p className="text-xs text-slate-400">{product.store_name}</p>
                </button>
              ))}
```

- [ ] **Step 4: 執行測試，確認通過**

Run: `cd frontend && npx vitest run src/pages/ShopFlowPage.test.tsx`
Expected: 全部 PASS。

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/ShopFlowPage.tsx frontend/src/pages/ShopFlowPage.test.tsx
git commit -m "feat(shop): show vendor name on each product card"
```

---

### Task 7: `ShopFlowPage.tsx` — 購物車依廠商分組顯示

**Files:**
- Modify: `frontend/src/pages/ShopFlowPage.tsx`
- Modify: `frontend/src/pages/ShopFlowPage.test.tsx`

**Interfaces:**
- Consumes: `CartEntry`（本任務擴充其欄位）、`ShopProduct.store_id`／`store_name`（Task 4 產出）
- Produces: `CartEntry` 新增 `storeId: string`／`storeName: string` 欄位（供本任務自身的分組渲染使用，後續任務無依賴）

- [ ] **Step 1: 新增測試案例，驗證購物車分組顯示**

在 `frontend/src/pages/ShopFlowPage.test.tsx`，先把 mock 商品資料擴充成跨兩家廠商（修改檔案頂端的 `products` 常數）：

```tsx
const products = [
  {
    id: "prod_a",
    store_id: "store_a",
    store_name: "A 店家",
    category_id: "cat_beverage",
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
    name: "商品 B",
    description: "描述 B",
    product_type: "SERIAL_CODE" as const,
    image: null,
    specs: [],
    skus: [{ sku_id: "sku_b", attributes: {}, unit_price: 80, unit_points: 8 }],
  },
];
```

然後在 `describe` 區塊新增測試：

```tsx
  it("groups cart items by vendor", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(await screen.findByText("飲品兌換"));

    await user.click(await screen.findByText("商品 A"));
    await user.click(screen.getByText("加入購物車（NT$50）"));

    await user.click(screen.getByText("商品 B"));
    await user.click(screen.getByText("加入購物車（NT$80）"));

    await user.click(screen.getByText(/前往購物車/));

    expect(await screen.findByText("A 店家")).toBeInTheDocument();
    expect(screen.getByText("B 店家")).toBeInTheDocument();
  });
```

- [ ] **Step 2: 執行測試，確認失敗**

Run: `cd frontend && npx vitest run src/pages/ShopFlowPage.test.tsx`
Expected: 新測試 FAIL（購物車畫面目前沒有顯示店家名稱分組標題）。

- [ ] **Step 3: 實作 — 修改 `CartEntry` 型別、`addToCart`、Step 3 JSX**

把 `CartEntry` 介面（第 20-27 行）：

```tsx
interface CartEntry {
  sku_id: string;
  productName: string;
  attributesLabel: string;
  unitPrice: number;
  quantity: number;
  productType: "PHYSICAL" | "SERIAL_CODE";
}
```

改為：

```tsx
interface CartEntry {
  sku_id: string;
  storeId: string;
  storeName: string;
  productName: string;
  attributesLabel: string;
  unitPrice: number;
  quantity: number;
  productType: "PHYSICAL" | "SERIAL_CODE";
}
```

把 `addToCart` 函式裡建立新 cart line 的物件（原本）：

```tsx
      return [
        ...prev,
        {
          sku_id: matchedSku.sku_id,
          productName: activeProduct.name,
          attributesLabel,
          unitPrice: matchedSku.unit_price,
          quantity: quantityToAdd,
          productType: activeProduct.product_type,
        },
      ];
```

改為：

```tsx
      return [
        ...prev,
        {
          sku_id: matchedSku.sku_id,
          storeId: activeProduct.store_id,
          storeName: activeProduct.store_name,
          productName: activeProduct.name,
          attributesLabel,
          unitPrice: matchedSku.unit_price,
          quantity: quantityToAdd,
          productType: activeProduct.product_type,
        },
      ];
```

在 `ShopFlowPage` 函式內、`cartTotal` 定義之前（約第 126 行之前），新增一個依廠商分組的 memo：

```tsx
  const cartGroups = useMemo(() => {
    const groups = new Map<string, { storeName: string; lines: CartEntry[] }>();
    for (const line of cart) {
      const existing = groups.get(line.storeId);
      if (existing) {
        existing.lines.push(line);
      } else {
        groups.set(line.storeId, { storeName: line.storeName, lines: [line] });
      }
    }
    return Array.from(groups.values());
  }, [cart]);
```

把 Step 3 購物車清單的 JSX：

```tsx
            <div className="flex flex-col gap-2">
              {cart.map((line) => (
                <div
                  key={line.sku_id}
                  className="flex items-center justify-between rounded-xl border border-slate-200 px-4 py-3"
                >
                  <div>
                    <p className="text-sm text-slate-600">
                      {line.productName}（{line.attributesLabel || "單一規格"}）
                    </p>
                    <p className="text-sm text-slate-500">NT${line.unitPrice * line.quantity}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => updateCartQuantity(line.sku_id, line.quantity - 1)}
                      className="flex h-8 w-8 items-center justify-center rounded-full border border-slate-300 text-slate-600"
                      aria-label="減少數量"
                    >
                      −
                    </button>
                    <span className="w-6 text-center text-base font-bold">{line.quantity}</span>
                    <button
                      type="button"
                      onClick={() => updateCartQuantity(line.sku_id, line.quantity + 1)}
                      className="flex h-8 w-8 items-center justify-center rounded-full bg-brand text-white"
                      aria-label="增加數量"
                    >
                      +
                    </button>
                    <button
                      type="button"
                      onClick={() => removeFromCart(line.sku_id)}
                      className="ml-1 text-xs text-slate-400 underline"
                      aria-label="移除"
                    >
                      移除
                    </button>
                  </div>
                </div>
              ))}
            </div>
```

改為：

```tsx
            <div className="flex flex-col gap-4">
              {cartGroups.map((group) => (
                <div key={group.storeName} className="flex flex-col gap-2">
                  <p className="text-sm font-bold text-slate-500">{group.storeName}</p>
                  {group.lines.map((line) => (
                    <div
                      key={line.sku_id}
                      className="flex items-center justify-between rounded-xl border border-slate-200 px-4 py-3"
                    >
                      <div>
                        <p className="text-sm text-slate-600">
                          {line.productName}（{line.attributesLabel || "單一規格"}）
                        </p>
                        <p className="text-sm text-slate-500">NT${line.unitPrice * line.quantity}</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={() => updateCartQuantity(line.sku_id, line.quantity - 1)}
                          className="flex h-8 w-8 items-center justify-center rounded-full border border-slate-300 text-slate-600"
                          aria-label="減少數量"
                        >
                          −
                        </button>
                        <span className="w-6 text-center text-base font-bold">{line.quantity}</span>
                        <button
                          type="button"
                          onClick={() => updateCartQuantity(line.sku_id, line.quantity + 1)}
                          className="flex h-8 w-8 items-center justify-center rounded-full bg-brand text-white"
                          aria-label="增加數量"
                        >
                          +
                        </button>
                        <button
                          type="button"
                          onClick={() => removeFromCart(line.sku_id)}
                          className="ml-1 text-xs text-slate-400 underline"
                          aria-label="移除"
                        >
                          移除
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              ))}
            </div>
```

- [ ] **Step 4: 執行測試，確認通過**

Run: `cd frontend && npx vitest run src/pages/ShopFlowPage.test.tsx`
Expected: 全部 PASS。

- [ ] **Step 5: 跑 TypeScript 編譯確認整個檔案沒有型別錯誤**

Run: `cd frontend && npx tsc --noEmit`
Expected: 沒有錯誤。

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/ShopFlowPage.tsx frontend/src/pages/ShopFlowPage.test.tsx
git commit -m "feat(shop): group cart items by vendor"
```

---

### Task 8: 重新 seed 商品庫存、跑完整測試套件與手動驗證

**Files:**
- 無程式碼修改（執行既有腳本 `backend/scripts/seed_shop_points.py`）

**Interfaces:**
- Consumes: Task 1 新增的 9 個新 SKU（`sku_familymart_latte_m`／`sku_louisa_iced_americano`／`sku_familymart_egg_3`／`sku_mos_fries_s`／`sku_daiso_box_white`／`sku_daiso_box_gray`／`sku_clean_spray_lemon`／`sku_clean_spray_tea`／`sku_kitchen_wipes_80`／`sku_vitamin_c_effervescent`／`sku_fish_oil_60`，共 11 個新 SKU，因為 `prod_daiso_storage_box`／`prod_clean_spray` 各有 2 個 SKU）
- Produces: 無

- [ ] **Step 1: 執行 seed 腳本，補上新 SKU 的初始庫存**

Run: `backend\.venv\Scripts\python.exe backend\scripts\seed_shop_points.py`
Expected: 對於新增的 11 個 SKU 印出 `Seeded sku_xxx with 20 in stock.`；既有 SKU（`sku_tshirt_white_s` 等）因為已有庫存會印出 `Skipped sku_xxx: already has N in stock.`。

- [ ] **Step 2: 跑完整 backend 測試套件**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests -v`
Expected: 全部 PASS。

- [ ] **Step 3: 跑完整 frontend 測試套件**

Run: `cd frontend && npx vitest run`
Expected: 全部 PASS。

- [ ] **Step 4: 手動啟動前後端，走一次完整購物流程**

啟動 backend（依專案既有方式，例如 `backend\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload`）與 frontend（`cd frontend && npm run dev`），在瀏覽器打開商城購物頁面（首頁 → 商城購物卡片），手動確認：
- 進頁面先看到 5 個品類卡片，而不是店家清單
- 點「飲品兌換」後，商品清單同時出現「City Café 中杯美式兌換券（7-11 台北車站店）」「現萃拿鐵兌換券（全家便利商店 台北忠孝店）」「冰美式兌換券（路易莎咖啡 信義店）」三家不同廠商的商品
- 從兩個不同品類個別加入一項商品到購物車（例如飲品兌換一項 + 生活日用品一項），進入購物車頁面後,兩項商品分別出現在對應的廠商分組標題下
- 完整走完結帳流程，確認訂單送出成功（沿用既有 UI，行為不變）

Expected: 以上四點皆符合，沒有主控台錯誤。

- [ ] **Step 5: Commit（若手動驗證中有調整資料/文案，一併提交；若無變動則跳過此步驟）**

```bash
git status --short
```

若有變動：

```bash
git add -A
git commit -m "chore(shop): manual verification fixes for category-first browsing"
```

---

## Self-Review Notes

- **Spec 覆蓋檢查：** 資料模型變更（Task 1、3）、後端 API 變更（Task 2）、前端型別/API client（Task 4）、前端三步流程調整（Task 5-7）、測試計畫（每個 Task 內建 TDD 測試 + Task 8 整體回歸）、資料同步注意事項（Task 3、8）— spec 各節都有對應任務。
- **Placeholder 掃描：** 無 TBD/TODO，所有程式碼區塊皆為完整可執行內容。
- **型別一致性檢查：** `ShopCategory`（Task 4 定義）在 Task 5 的 import 與 state 型別一致；`ShopProduct.store_name`／`category_id`（Task 4 定義）在 Task 6（顯示）、Task 1（後端回傳）、測試 mock 資料中的欄位名稱一致；`CartEntry.storeId`／`storeName`（Task 7 定義）在 `addToCart` 與 `cartGroups`／JSX 渲染中使用一致；`listShopCategories`／`listShopProducts(categoryId)` 函式簽章在 Task 4 定義、Task 5 呼叫、測試 mock 中一致。
