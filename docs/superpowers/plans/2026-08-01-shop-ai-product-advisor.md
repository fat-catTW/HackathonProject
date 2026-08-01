# Shop AI Product Advisor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let users describe a need or usage scenario in the chat (e.g. "我想要錄 podcast 用的麥克風") and have the AI shopping assistant compare products across brands/stores in the mall, using ratings and written reviews, and return a reasoned recommendation with a deep link into the mall.

**Architecture:** Add a `cat_electronics` category with 7 new brand storefronts/products to the existing static `shop_catalog.py`. Add a new `shop_reviews.py` module holding hand-written reviews for every product in the catalog (existing + new), with a `get_rating_summary()` helper merged into `shop_catalog.list_products()`/`get_product()`. Add a Bedrock-backed recommendation function to the existing `app/agent/llm.py` (same `_converse_json` helper already used for service routing/form-filling), wrapped by a new `shop_recommendation.py` service with a keyword/tag/rating fallback. Wire it into the chat agent as a new one-shot service `shop_product_advisor`, following the exact pattern already used by `health_product_recommendation` and `shop_price_compare`. On the frontend, `ShopFlowPage.tsx` gains a rating badge on product cards, a client-side "sort by rating" toggle, an expandable review list, and a `?category_id=` deep link.

**Tech Stack:** FastAPI + Python 3.12 (backend), React + TypeScript + Vite (frontend), boto3 `bedrock-runtime` `converse` API, pytest, vitest + React Testing Library.

## Global Constraints

- Follow the existing one-shot service pattern exactly: `health_product_recommendation` and `shop_price_compare` in `backend/app/services/catalog.py` / `backend/app/agent/agent.py` are the reference implementations.
- New shop electronics products must NOT set `compare_group_id` (that field belongs to the separate, already-merged cross-vendor price-compare feature) — they only get the new optional `tags: list[str]` field.
- Every product in `shop_catalog.SHOP_PRODUCTS` (existing 19 + new 7 = 26) must have at least one review in `shop_reviews.SHOP_REVIEWS` — no product may end up with `rating_count == 0`.
- The new recommendation tool (`recommend_shop_products_by_need`) is `embedded`-mode only — do NOT add it to `_invoke_lambda`'s or `_gateway_tool_name`'s function-name tables, and do NOT create a Lambda handler for it (matches the existing `compare_product_prices` precedent).
- `lambda_tools/shared_lambda/shop_catalog.py` must stay byte-for-byte identical to `backend/app/services/shop_catalog.py` for the catalog data sections (existing project convention, verified today via `diff` — the two files are currently identical).
- All new backend code follows `from __future__ import annotations` + existing import grouping conventions already present in the files being edited.
- Spec reference: `docs/superpowers/specs/2026-08-01-shop-ai-product-advisor-design.md`.

---

### Task 1: Fix the pre-existing `_answer_price_compare` NameError

**Context:** Running the existing test suite in this worktree today revealed a real bug in already-merged code: `backend/app/agent/agent.py` calls `_answer_price_compare(text, auth_token)` at line 1278 (inside the `shop_price_compare` interception block) but that function is never defined anywhere in the file — a `NameError` at runtime. Confirmed with:
```
python -m pytest backend/tests/test_shop_price_compare.py -x -q
```
which fails with `NameError: name '_answer_price_compare' is not defined`. This must be fixed first so later tasks build on a green baseline, and so the existing `shop_price_compare` tests (which Task 9 needs to keep passing) actually pass.

**Files:**
- Modify: `backend/app/agent/agent.py`
- Test: `backend/tests/test_shop_price_compare.py` (already exists, currently failing — no new test needed)

**Interfaces:**
- Produces: `_answer_price_compare(query: str, auth_token: str | None) -> tuple[str, str | None]` (reply text, redirect_path or None), used by the existing call site at `agent.py:1278`.

- [ ] **Step 1: Run the existing test to confirm the failure**

Run: `python -m pytest backend/tests/test_shop_price_compare.py -x -q`
Expected: FAIL — `NameError: name '_answer_price_compare' is not defined`

- [ ] **Step 2: Add the missing function**

In `backend/app/agent/agent.py`, insert this function right after `_answer_health_recommendation` (which ends around line 1679, just before `def _format_health_nutrition_reply`):

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

- [ ] **Step 3: Run the test again to verify it passes**

Run: `python -m pytest backend/tests/test_shop_price_compare.py -q`
Expected: PASS — `6 passed`

- [ ] **Step 4: Run the full backend suite to confirm nothing else broke**

Run: `python -m pytest backend -q`
Expected: all tests pass (this is your clean baseline — note the total pass count for comparison after later tasks)

- [ ] **Step 5: Commit**

```bash
git add backend/app/agent/agent.py
git commit -m "fix: define missing _answer_price_compare (NameError regression)"
```

---

### Task 2: Add the electronics category, stores, and products to `shop_catalog.py`

**Files:**
- Modify: `backend/app/services/shop_catalog.py`
- Test: `backend/tests/test_shop_catalog.py`

**Interfaces:**
- Produces: category `cat_electronics`; 7 new `SHOP_STORES` entries; 7 new `SHOP_PRODUCTS` entries, each with an optional `tags: list[str]` field. No changes to `list_products()`/`get_product()` signatures in this task (rating merge happens in Task 5).

- [ ] **Step 1: Write the failing tests**

Add to `backend/tests/test_shop_catalog.py`:

```python
def test_electronics_category_registered():
    category_ids = {c["id"] for c in shop_catalog.list_categories()}
    assert "cat_electronics" in category_ids


def test_electronics_category_has_seven_distinct_vendors():
    products = shop_catalog.list_products(category_id="cat_electronics")
    assert len(products) == 7
    assert len({p["store_id"] for p in products}) == 7


def test_electronics_products_have_descriptive_tags():
    mic = next(p for p in shop_catalog.SHOP_PRODUCTS if p["id"] == "prod_mic_fifine_k669b")
    assert "麥克風" in mic["tags"]
    assert "podcast" in mic["tags"]


def test_electronics_products_have_no_compare_group_id():
    products = shop_catalog.list_products(category_id="cat_electronics")
    assert all(p["compare_group_id"] is None for p in products)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest backend/tests/test_shop_catalog.py -k electronics -v`
Expected: FAIL — `cat_electronics` not found / 0 products

- [ ] **Step 3: Add the category**

In `backend/app/services/shop_catalog.py`, append to `SHOP_CATEGORIES` (after the `cat_health` entry):

```python
    {"id": "cat_electronics", "name": "3C 影音周邊"},
```

- [ ] **Step 4: Add the 7 new stores**

Append to `SHOP_STORES` (after `store_carrefour`):

```python
    {"id": "store_fifine_official", "name": "FIFINE 官方旗艦店", "category": "3C影音", "image": None},
    {"id": "store_blue_mic_tw", "name": "Blue 麥克風台灣旗艦店", "category": "3C影音", "image": None},
    {"id": "store_rode_tw", "name": "Rode 台灣官方旗艦店", "category": "3C影音", "image": None},
    {"id": "store_hyperx_tw", "name": "HyperX 官方旗艦店", "category": "3C影音", "image": None},
    {"id": "store_audio_technica_tw", "name": "Audio-Technica 台灣總代理", "category": "3C影音", "image": None},
    {"id": "store_logitech_tw", "name": "羅技官方旗艦店", "category": "3C影音", "image": None},
    {"id": "store_pro_audio_tw", "name": "音響數位樂器行", "category": "3C影音", "image": None},
```

- [ ] **Step 5: Add the 7 new products**

Append to `SHOP_PRODUCTS` (after `prod_tumbler_watsons`, before the closing `]`):

```python
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
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `python -m pytest backend/tests/test_shop_catalog.py -v`
Expected: PASS — all tests including the 4 new ones and every pre-existing invariant test (`test_each_category_has_at_least_two_distinct_vendors`, `test_sku_ids_are_globally_unique`, `test_physical_products_have_specs_matching_sku_attribute_keys`, the compare-group tests, etc.)

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/shop_catalog.py backend/tests/test_shop_catalog.py
git commit -m "feat: add cat_electronics category with 7 brand storefronts and products"
```

---

### Task 3: Sync `lambda_tools/shared_lambda/shop_catalog.py`

**Files:**
- Modify: `lambda_tools/shared_lambda/shop_catalog.py`
- Test: `lambda_tools/tests/test_get_shop_products_handler.py` (existing — should still pass unmodified)

**Interfaces:**
- Produces: identical `SHOP_CATEGORIES`/`SHOP_STORES`/`SHOP_PRODUCTS` content to `backend/app/services/shop_catalog.py` after Task 2.

- [ ] **Step 1: Verify the files are still identical before editing**

Run: `diff backend/app/services/shop_catalog.py lambda_tools/shared_lambda/shop_catalog.py`
Expected: large diff (backend now has the 8 new lines in `SHOP_CATEGORIES`/`SHOP_STORES` and the 7 new product blocks that `lambda_tools` doesn't have yet)

- [ ] **Step 2: Copy the backend file over the lambda_tools copy**

```bash
cp backend/app/services/shop_catalog.py lambda_tools/shared_lambda/shop_catalog.py
```

- [ ] **Step 3: Verify they're identical again**

Run: `diff backend/app/services/shop_catalog.py lambda_tools/shared_lambda/shop_catalog.py`
Expected: no output (files identical)

- [ ] **Step 4: Run the lambda_tools test suite**

Run: `python -m pytest lambda_tools/tests -q`
Expected: PASS — no regressions (this handler only reads `list_products`/`list_stores`, both unchanged in signature)

- [ ] **Step 5: Commit**

```bash
git add lambda_tools/shared_lambda/shop_catalog.py
git commit -m "chore: sync lambda_tools shop_catalog copy with backend catalog"
```

---

### Task 4: Create `shop_reviews.py` with review data for every product

**Files:**
- Create: `backend/app/services/shop_reviews.py`
- Test: `backend/tests/test_shop_reviews.py`

**Interfaces:**
- Produces: `list_reviews(product_id: str) -> list[dict]`, `get_rating_summary(product_id: str) -> dict` (returns `{"rating_avg": float, "rating_count": int}`). Consumed by Task 5 (`shop_catalog`) and Task 6 (API endpoint).

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_shop_reviews.py`:

```python
from backend.app.services import shop_catalog, shop_reviews


def test_every_catalog_product_has_at_least_one_review():
    for product in shop_catalog.SHOP_PRODUCTS:
        reviews = shop_reviews.list_reviews(product["id"])
        assert len(reviews) >= 1, f"{product['id']} has no reviews"


def test_list_reviews_returns_expected_shape():
    reviews = shop_reviews.list_reviews("prod_mic_fifine_k669b")
    assert len(reviews) >= 3
    for review in reviews:
        assert {"review_id", "author", "rating", "comment", "created_at", "verified_purchase"} <= set(review.keys())
        assert 1 <= review["rating"] <= 5


def test_list_reviews_unknown_product_returns_empty_list():
    assert shop_reviews.list_reviews("does_not_exist") == []


def test_get_rating_summary_computes_average_and_count():
    summary = shop_reviews.get_rating_summary("prod_mic_fifine_k669b")
    reviews = shop_reviews.list_reviews("prod_mic_fifine_k669b")
    expected_avg = round(sum(r["rating"] for r in reviews) / len(reviews), 1)
    assert summary == {"rating_avg": expected_avg, "rating_count": len(reviews)}


def test_get_rating_summary_unknown_product_returns_zero():
    assert shop_reviews.get_rating_summary("does_not_exist") == {"rating_avg": 0.0, "rating_count": 0}


def test_review_ids_are_globally_unique():
    all_ids = [
        review["review_id"]
        for reviews in shop_reviews.SHOP_REVIEWS.values()
        for review in reviews
    ]
    assert len(all_ids) == len(set(all_ids))
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest backend/tests/test_shop_reviews.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'backend.app.services.shop_reviews'`

- [ ] **Step 3: Create `backend/app/services/shop_reviews.py`**

```python
"""Static per-product review data and rating aggregation for the shop catalog.

Every product in shop_catalog.SHOP_PRODUCTS must have at least one entry here,
keyed by its own product_id — including the separate per-store product_ids for
the same physical item (e.g. prod_vitamin_c / prod_vitamin_c_lohas /
prod_vitamin_c_watsons), since a review reflects the experience of buying from
that specific store, not just the product itself.
"""
from __future__ import annotations

SHOP_REVIEWS: dict[str, list[dict]] = {
    "prod_tshirt_basic": [
        {"review_id": "rev_tshirt_basic_01", "author": "佳玲", "rating": 5, "comment": "布料摸起來很舒服，洗過幾次也沒變形，白色跟黑色我都買了。", "created_at": "2026-03-02", "verified_purchase": True},
        {"review_id": "rev_tshirt_basic_02", "author": "阿德", "rating": 4, "comment": "版型偏合身，怕熱的話買大一號比較好。", "created_at": "2026-04-18", "verified_purchase": True},
        {"review_id": "rev_tshirt_basic_03", "author": "小雨", "rating": 3, "comment": "顏色跟照片有點色差，但穿起來還算舒適。", "created_at": "2026-05-27", "verified_purchase": False},
    ],
    "prod_tumbler": [
        {"review_id": "rev_tumbler_01", "author": "Vincent", "rating": 5, "comment": "保冷真的有12小時，帶去爬山冰塊都還在。", "created_at": "2026-02-14", "verified_purchase": True},
        {"review_id": "rev_tumbler_02", "author": "美惠", "rating": 5, "comment": "粉色很好看，背帶設計外出很方便。", "created_at": "2026-03-09", "verified_purchase": True},
        {"review_id": "rev_tumbler_03", "author": "建宏", "rating": 4, "comment": "容量對男生來說偏小，但保溫效果不錯。", "created_at": "2026-06-01", "verified_purchase": True},
    ],
    "prod_coffee_coupon": [
        {"review_id": "rev_coffee_coupon_01", "author": "阿翔", "rating": 5, "comment": "全台門市都能兌換，出差在外地也用得到。", "created_at": "2026-03-20", "verified_purchase": True},
        {"review_id": "rev_coffee_coupon_02", "author": "淑芬", "rating": 4, "comment": "咖啡味道跟平常買的一樣，效期30天算夠用。", "created_at": "2026-04-05", "verified_purchase": True},
        {"review_id": "rev_coffee_coupon_03", "author": "阿哲", "rating": 3, "comment": "偶爾遇到門市咖啡機故障不能兌換，要換一家有點麻煩。", "created_at": "2026-05-11", "verified_purchase": False},
    ],
    "prod_onigiri_coupon": [
        {"review_id": "rev_onigiri_coupon_01", "author": "怡君", "rating": 5, "comment": "口味選擇多，鮭魚跟鮪魚都兌換過，很划算。", "created_at": "2026-02-22", "verified_purchase": True},
        {"review_id": "rev_onigiri_coupon_02", "author": "家豪", "rating": 4, "comment": "早餐救星，效期14天要記得快點用掉。", "created_at": "2026-03-30", "verified_purchase": True},
        {"review_id": "rev_onigiri_coupon_03", "author": "雅婷", "rating": 4, "comment": "門市庫存偶爾會缺貨，建議提早兌換。", "created_at": "2026-06-15", "verified_purchase": True},
    ],
    "prod_familymart_latte": [
        {"review_id": "rev_familymart_latte_01", "author": "俊傑", "rating": 5, "comment": "現萃口感比想像中濃郁，價格也划算。", "created_at": "2026-03-11", "verified_purchase": True},
        {"review_id": "rev_familymart_latte_02", "author": "詩涵", "rating": 4, "comment": "奶泡綿密，冰的熱的都好喝。", "created_at": "2026-04-25", "verified_purchase": True},
        {"review_id": "rev_familymart_latte_03", "author": "冠廷", "rating": 3, "comment": "早上尖峰時間排隊比較久。", "created_at": "2026-05-30", "verified_purchase": False},
    ],
    "prod_louisa_iced_americano": [
        {"review_id": "rev_louisa_iced_americano_01", "author": "品妤", "rating": 5, "comment": "路易莎的冰美式一直是我的最愛，兌換超方便。", "created_at": "2026-02-28", "verified_purchase": True},
        {"review_id": "rev_louisa_iced_americano_02", "author": "惠敏", "rating": 4, "comment": "咖啡因濃度夠，提神效果好。", "created_at": "2026-04-02", "verified_purchase": True},
        {"review_id": "rev_louisa_iced_americano_03", "author": "靜怡", "rating": 4, "comment": "門市不算多，要先查好離家近的分店。", "created_at": "2026-06-20", "verified_purchase": True},
    ],
    "prod_familymart_egg": [
        {"review_id": "rev_familymart_egg_01", "author": "阿宗", "rating": 5, "comment": "茶葉蛋滷得很入味，3顆份量剛好當點心。", "created_at": "2026-03-05", "verified_purchase": True},
        {"review_id": "rev_familymart_egg_02", "author": "佳玲", "rating": 4, "comment": "CP值高，效期14天記得盡快用掉。", "created_at": "2026-04-14", "verified_purchase": True},
        {"review_id": "rev_familymart_egg_03", "author": "阿德", "rating": 3, "comment": "蛋的大小不太一致，但味道沒問題。", "created_at": "2026-05-19", "verified_purchase": False},
    ],
    "prod_mos_fries": [
        {"review_id": "rev_mos_fries_01", "author": "小雨", "rating": 5, "comment": "薯條現炸的很酥脆，小份量剛好不會有罪惡感。", "created_at": "2026-02-18", "verified_purchase": True},
        {"review_id": "rev_mos_fries_02", "author": "Vincent", "rating": 4, "comment": "偶爾中午人多要等現炸，但值得等。", "created_at": "2026-04-08", "verified_purchase": True},
        {"review_id": "rev_mos_fries_03", "author": "美惠", "rating": 4, "comment": "配合套餐一起用更划算。", "created_at": "2026-06-03", "verified_purchase": True},
    ],
    "prod_daiso_storage_box": [
        {"review_id": "rev_daiso_storage_box_01", "author": "建宏", "rating": 5, "comment": "可堆疊設計很省空間，衣櫃整理一次到位。", "created_at": "2026-03-15", "verified_purchase": True},
        {"review_id": "rev_daiso_storage_box_02", "author": "阿翔", "rating": 4, "comment": "白色跟灰色都耐看，價格便宜可以多買幾個。", "created_at": "2026-04-21", "verified_purchase": True},
        {"review_id": "rev_daiso_storage_box_03", "author": "淑芬", "rating": 3, "comment": "塑膠材質偏薄，重物疊上去要小心。", "created_at": "2026-05-25", "verified_purchase": False},
    ],
    "prod_clean_spray": [
        {"review_id": "rev_clean_spray_01", "author": "阿哲", "rating": 5, "comment": "檸檬香味清爽，廚房油污噴一下就能擦掉。", "created_at": "2026-02-25", "verified_purchase": True},
        {"review_id": "rev_clean_spray_02", "author": "怡君", "rating": 4, "comment": "天然配方對敏感肌膚比較安心。", "created_at": "2026-03-28", "verified_purchase": True},
        {"review_id": "rev_clean_spray_03", "author": "家豪", "rating": 4, "comment": "浴室水垢要多噴幾次才有效。", "created_at": "2026-06-10", "verified_purchase": True},
    ],
    "prod_kitchen_wipes": [
        {"review_id": "rev_kitchen_wipes_01", "author": "雅婷", "rating": 5, "comment": "吸水力很好，廚房必備款，一次買好幾包。", "created_at": "2026-03-01", "verified_purchase": True},
        {"review_id": "rev_kitchen_wipes_02", "author": "俊傑", "rating": 4, "comment": "厚度夠，不容易破。", "created_at": "2026-04-11", "verified_purchase": True},
        {"review_id": "rev_kitchen_wipes_03", "author": "詩涵", "rating": 3, "comment": "抽取口設計偶爾會卡紙。", "created_at": "2026-05-16", "verified_purchase": False},
    ],
    "prod_vitamin_c": [
        {"review_id": "rev_vitamin_c_01", "author": "冠廷", "rating": 5, "comment": "檸檬口味不會太酸，泡完氣泡感十足。", "created_at": "2026-02-19", "verified_purchase": True},
        {"review_id": "rev_vitamin_c_02", "author": "品妤", "rating": 4, "comment": "感冒季節每天一錠，感覺比較不容易累。", "created_at": "2026-03-24", "verified_purchase": True},
        {"review_id": "rev_vitamin_c_03", "author": "惠敏", "rating": 4, "comment": "價格稍高但品牌信賴度夠。", "created_at": "2026-06-05", "verified_purchase": True},
    ],
    "prod_fish_oil": [
        {"review_id": "rev_fish_oil_01", "author": "靜怡", "rating": 5, "comment": "無腥味好吞嚥，吃了一個月精神狀況變好。", "created_at": "2026-03-08", "verified_purchase": True},
        {"review_id": "rev_fish_oil_02", "author": "阿宗", "rating": 4, "comment": "Omega-3濃度夠高，長輩也適合吃。", "created_at": "2026-04-17", "verified_purchase": True},
        {"review_id": "rev_fish_oil_03", "author": "佳玲", "rating": 3, "comment": "膠囊偏大，剛開始吞有點卡。", "created_at": "2026-05-22", "verified_purchase": False},
    ],
    "prod_vitamin_c_lohas": [
        {"review_id": "rev_vitamin_c_lohas_01", "author": "阿德", "rating": 5, "comment": "同款維他命C比健康藥妝便宜20元，直接改買這家。", "created_at": "2026-03-12", "verified_purchase": True},
        {"review_id": "rev_vitamin_c_lohas_02", "author": "小雨", "rating": 4, "comment": "出貨速度快，包裝完整。", "created_at": "2026-04-26", "verified_purchase": True},
        {"review_id": "rev_vitamin_c_lohas_03", "author": "Vincent", "rating": 4, "comment": "口味跟其他家一樣，價格是最大優勢。", "created_at": "2026-06-08", "verified_purchase": True},
    ],
    "prod_vitamin_c_watsons": [
        {"review_id": "rev_vitamin_c_watsons_01", "author": "美惠", "rating": 5, "comment": "屈臣氏買維他命C很方便，門市多好取貨。", "created_at": "2026-02-27", "verified_purchase": True},
        {"review_id": "rev_vitamin_c_watsons_02", "author": "建宏", "rating": 4, "comment": "價格中規中矩，服務態度不錯。", "created_at": "2026-04-06", "verified_purchase": True},
        {"review_id": "rev_vitamin_c_watsons_03", "author": "阿翔", "rating": 3, "comment": "常常缺貨要多跑幾家分店。", "created_at": "2026-05-14", "verified_purchase": False},
    ],
    "prod_clean_spray_miaojie": [
        {"review_id": "rev_clean_spray_miaojie_01", "author": "淑芬", "rating": 5, "comment": "跟舒潔那款一樣好用，價格更划算。", "created_at": "2026-03-18", "verified_purchase": True},
        {"review_id": "rev_clean_spray_miaojie_02", "author": "阿哲", "rating": 4, "comment": "茶樹味道清新，廚房浴室都能用。", "created_at": "2026-04-29", "verified_purchase": True},
        {"review_id": "rev_clean_spray_miaojie_03", "author": "怡君", "rating": 4, "comment": "瓶身噴頭設計順手。", "created_at": "2026-06-12", "verified_purchase": True},
    ],
    "prod_clean_spray_carrefour": [
        {"review_id": "rev_clean_spray_carrefour_01", "author": "家豪", "rating": 5, "comment": "家樂福這款最便宜，效果跟其他家沒差。", "created_at": "2026-02-21", "verified_purchase": True},
        {"review_id": "rev_clean_spray_carrefour_02", "author": "雅婷", "rating": 4, "comment": "大罐屯貨划算，量販店買一次夠用很久。", "created_at": "2026-04-03", "verified_purchase": True},
        {"review_id": "rev_clean_spray_carrefour_03", "author": "俊傑", "rating": 3, "comment": "噴頭偶爾會卡住，要搖一搖才順。", "created_at": "2026-05-28", "verified_purchase": False},
    ],
    "prod_tumbler_daiso": [
        {"review_id": "rev_tumbler_daiso_01", "author": "詩涵", "rating": 5, "comment": "跟統一時代同款但便宜100元，划算。", "created_at": "2026-03-06", "verified_purchase": True},
        {"review_id": "rev_tumbler_daiso_02", "author": "冠廷", "rating": 4, "comment": "保冷效果不錯，藍色顏色很好看。", "created_at": "2026-04-19", "verified_purchase": True},
        {"review_id": "rev_tumbler_daiso_03", "author": "品妤", "rating": 4, "comment": "背帶稍微陽春，但功能沒問題。", "created_at": "2026-06-17", "verified_purchase": True},
    ],
    "prod_tumbler_watsons": [
        {"review_id": "rev_tumbler_watsons_01", "author": "惠敏", "rating": 4, "comment": "屈臣氏買比較方便，價格中等。", "created_at": "2026-03-23", "verified_purchase": True},
        {"review_id": "rev_tumbler_watsons_02", "author": "靜怡", "rating": 4, "comment": "顏色選擇跟其他家一樣，取貨快。", "created_at": "2026-05-02", "verified_purchase": True},
        {"review_id": "rev_tumbler_watsons_03", "author": "阿宗", "rating": 3, "comment": "價格比大創貴一些，但門市多是加分。", "created_at": "2026-06-22", "verified_purchase": False},
    ],
    "prod_mic_fifine_k669b": [
        {"review_id": "rev_fifine_k669b_01", "author": "阿凱", "rating": 5, "comment": "第一次錄 podcast 就用這支，收音乾淨、價格親民，新手很夠用。", "created_at": "2026-05-12", "verified_purchase": True},
        {"review_id": "rev_fifine_k669b_02", "author": "小美", "rating": 4, "comment": "USB接上就能用，完全不用調設定，很適合入門。", "created_at": "2026-06-03", "verified_purchase": True},
        {"review_id": "rev_fifine_k669b_03", "author": "志明", "rating": 3, "comment": "拿來玩遊戲語音沒問題，但錄音室等級的細節還是差一截。", "created_at": "2026-06-25", "verified_purchase": True},
    ],
    "prod_mic_blue_yeti_x": [
        {"review_id": "rev_blue_yeti_x_01", "author": "春嬌", "rating": 5, "comment": "業界經典不是叫假的，四種指向模式錄訪談很方便切換。", "created_at": "2026-04-20", "verified_purchase": True},
        {"review_id": "rev_blue_yeti_x_02", "author": "阿豪", "rating": 5, "comment": "耳機孔即時監聽超實用，聲音細膩，podcast用起來很專業。", "created_at": "2026-05-15", "verified_purchase": True},
        {"review_id": "rev_blue_yeti_x_03", "author": "雨萱", "rating": 4, "comment": "體積比想像中大，桌面空間要留意，但音質真的沒話說。", "created_at": "2026-06-30", "verified_purchase": True},
    ],
    "prod_mic_rode_nt_usb_mini": [
        {"review_id": "rev_rode_nt_usb_mini_01", "author": "承翰", "rating": 5, "comment": "體積小巧放在小桌子剛剛好，磁吸架很穩不會震動收音。", "created_at": "2026-05-02", "verified_purchase": True},
        {"review_id": "rev_rode_nt_usb_mini_02", "author": "怡君", "rating": 5, "comment": "收音真的很乾淨，背景雜音壓得很好，適合在家錄音。", "created_at": "2026-05-24", "verified_purchase": True},
        {"review_id": "rev_rode_nt_usb_mini_03", "author": "家豪", "rating": 4, "comment": "外型簡約好看，就是配件比較陽春。", "created_at": "2026-06-14", "verified_purchase": False},
    ],
    "prod_mic_hyperx_quadcast_s": [
        {"review_id": "rev_hyperx_quadcast_s_01", "author": "俊傑", "rating": 5, "comment": "RGB燈效直播畫面加分，音質對電競實況來說很夠用。", "created_at": "2026-04-28", "verified_purchase": True},
        {"review_id": "rev_hyperx_quadcast_s_02", "author": "詩涵", "rating": 4, "comment": "內建防震架跟防噴罩省了額外採購，開箱就能用。", "created_at": "2026-05-19", "verified_purchase": True},
        {"review_id": "rev_hyperx_quadcast_s_03", "author": "冠廷", "rating": 3, "comment": "價格偏高，如果不需要RGB其實有更划算的選擇。", "created_at": "2026-06-27", "verified_purchase": True},
    ],
    "prod_mic_atr2100x_usb": [
        {"review_id": "rev_atr2100x_usb_01", "author": "品妤", "rating": 5, "comment": "雙人訪談用USB接兩支剛剛好，動圈式對環境噪音抑制很有感。", "created_at": "2026-05-08", "verified_purchase": True},
        {"review_id": "rev_atr2100x_usb_02", "author": "惠敏", "rating": 5, "comment": "XLR/USB雙介面很彈性，之後要升級混音器也能直接接。", "created_at": "2026-05-30", "verified_purchase": True},
        {"review_id": "rev_atr2100x_usb_03", "author": "靜怡", "rating": 4, "comment": "戶外收音也試過，抗噪表現不錯，就是機身偏重。", "created_at": "2026-06-18", "verified_purchase": False},
    ],
    "prod_webcam_logitech_c920": [
        {"review_id": "rev_webcam_logitech_c920_01", "author": "阿宗", "rating": 5, "comment": "1080p畫質視訊會議很夠用，自動對焦反應快。", "created_at": "2026-04-15", "verified_purchase": True},
        {"review_id": "rev_webcam_logitech_c920_02", "author": "佳玲", "rating": 4, "comment": "搭配麥克風錄podcast影片版剛剛好，色彩還原不錯。", "created_at": "2026-05-21", "verified_purchase": True},
        {"review_id": "rev_webcam_logitech_c920_03", "author": "阿德", "rating": 4, "comment": "夾式支架穩固，就是低光源環境畫質會偏暗。", "created_at": "2026-06-09", "verified_purchase": True},
    ],
    "prod_audio_interface_scarlett_solo": [
        {"review_id": "rev_scarlett_solo_01", "author": "小雨", "rating": 5, "comment": "入門錄音介面首選，接上XLR麥克風音質提升很明顯。", "created_at": "2026-05-04", "verified_purchase": True},
        {"review_id": "rev_scarlett_solo_02", "author": "Vincent", "rating": 4, "comment": "操作介面直覺，第一次用類比介面也很快上手。", "created_at": "2026-05-26", "verified_purchase": True},
        {"review_id": "rev_scarlett_solo_03", "author": "美惠", "rating": 4, "comment": "想從純USB麥克風升級雙軌訪談的話這台很適合，但要另外買麥克風線。", "created_at": "2026-06-19", "verified_purchase": False},
    ],
}


def list_reviews(product_id: str) -> list[dict]:
    return list(SHOP_REVIEWS.get(product_id, []))


def get_rating_summary(product_id: str) -> dict:
    reviews = SHOP_REVIEWS.get(product_id, [])
    if not reviews:
        return {"rating_avg": 0.0, "rating_count": 0}
    avg = sum(r["rating"] for r in reviews) / len(reviews)
    return {"rating_avg": round(avg, 1), "rating_count": len(reviews)}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest backend/tests/test_shop_reviews.py -v`
Expected: PASS — all 6 tests, including `test_every_catalog_product_has_at_least_one_review` (this is what proves all 26 products, old and new, are covered)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/shop_reviews.py backend/tests/test_shop_reviews.py
git commit -m "feat: add shop_reviews.py with ratings/reviews for every catalog product"
```

---

### Task 5: Merge rating summary into `shop_catalog.list_products()` / `get_product()`

**Files:**
- Modify: `backend/app/services/shop_catalog.py`
- Test: `backend/tests/test_shop_catalog.py`

**Interfaces:**
- Consumes: `shop_reviews.get_rating_summary(product_id: str) -> dict` (Task 4).
- Produces: `list_products()` and `get_product()` return dicts that now include `rating_avg: float` and `rating_count: int`.

- [ ] **Step 1: Write the failing tests**

Add to `backend/tests/test_shop_catalog.py`:

```python
def test_list_products_includes_rating_fields():
    for product in shop_catalog.list_products():
        assert isinstance(product["rating_avg"], float)
        assert isinstance(product["rating_count"], int)
        assert product["rating_count"] >= 1


def test_get_product_includes_rating_fields():
    product = shop_catalog.get_product("prod_mic_blue_yeti_x")
    assert product["rating_count"] >= 1
    assert 1.0 <= product["rating_avg"] <= 5.0
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest backend/tests/test_shop_catalog.py -k rating_fields -v`
Expected: FAIL — `KeyError: 'rating_avg'`

- [ ] **Step 3: Update `shop_catalog.py`**

Add the import at the top of the file (after the module docstring, before `SHOP_CATEGORIES`):

```python
from . import shop_reviews
```

Replace the existing `list_products` function body's return statement:

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
            **shop_reviews.get_rating_summary(p["id"]),
        }
        for p in products
    ]
```

Replace the existing `get_product` function:

```python
def get_product(product_id: str) -> dict | None:
    product = next((p for p in SHOP_PRODUCTS if p["id"] == product_id), None)
    if product is None:
        return None
    return {**product, **shop_reviews.get_rating_summary(product_id)}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest backend/tests/test_shop_catalog.py -v`
Expected: PASS — all tests, including the 2 new ones and every pre-existing test (the `get_product` return value changed shape — check there is no existing test asserting `get_product()` returns exactly the raw dict with no extra keys; if one exists and fails, update it to allow extra keys via subset comparison rather than deleting the assertion)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/shop_catalog.py backend/tests/test_shop_catalog.py
git commit -m "feat: merge rating_avg/rating_count into shop_catalog product responses"
```

---

### Task 6: Add the product reviews API endpoint

**Files:**
- Modify: `backend/app/api/shop.py`
- Test: `backend/tests/test_shop_api.py`

**Interfaces:**
- Consumes: `shop_reviews.list_reviews(product_id: str) -> list[dict]` (Task 4), `shop_catalog.get_product(product_id: str) -> dict | None` (existing).
- Produces: `GET /api/shop/products/{product_id}/reviews` → `{"reviews": [...]}`.

- [ ] **Step 1: Write the failing tests**

Add to `backend/tests/test_shop_api.py`:

```python
def test_get_shop_product_reviews_returns_reviews():
    client = TestClient(app)
    response = client.get("/api/shop/products/prod_mic_blue_yeti_x/reviews")
    assert response.status_code == 200
    reviews = response.json()["reviews"]
    assert len(reviews) >= 1
    assert all({"review_id", "author", "rating", "comment", "created_at", "verified_purchase"} <= set(r.keys()) for r in reviews)


def test_get_shop_product_reviews_unknown_product_returns_404():
    client = TestClient(app)
    response = client.get("/api/shop/products/does_not_exist/reviews")
    assert response.status_code == 404
    assert response.json()["detail"]["error"]["code"] == "PRODUCT_NOT_FOUND"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest backend/tests/test_shop_api.py -k reviews -v`
Expected: FAIL — `404 Not Found` (route doesn't exist) for the first test

- [ ] **Step 3: Add the endpoint**

In `backend/app/api/shop.py`, add the import:

```python
from ..services import shop, shop_catalog, shop_reviews
```

(replacing the existing `from ..services import shop, shop_catalog` line)

Add the new route right after `get_shop_compare_group`:

```python
@router.get("/api/shop/products/{product_id}/reviews")
def get_shop_product_reviews(product_id: str) -> dict:
    product = shop_catalog.get_product(product_id)
    if not product:
        _raise_api_error(404, "PRODUCT_NOT_FOUND", "找不到這項商品")
    return {"reviews": shop_reviews.list_reviews(product_id)}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest backend/tests/test_shop_api.py -v`
Expected: PASS — all tests

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/shop.py backend/tests/test_shop_api.py
git commit -m "feat: add GET /api/shop/products/{id}/reviews endpoint"
```

---

### Task 7: Add `llm.recommend_shop_products` (Bedrock)

**Files:**
- Modify: `backend/app/agent/llm.py`
- Test: `backend/tests/test_shop_recommendation.py` (created in this task, extended in Task 8)

**Interfaces:**
- Produces: `recommend_shop_products(query: str, products: list[dict]) -> list[dict] | None`. Returns `None` when the Bedrock client is unavailable or the call fails (mirrors every other `llm.py` function's fallback contract).

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_shop_recommendation.py`:

```python
from unittest.mock import patch

from backend.app.agent import llm


def test_recommend_shop_products_returns_none_without_bedrock_credentials():
    """No AWS credentials are configured in the test env (see backend/.env.example
    defaults), so llm._get_client() returns None and this must return None,
    exactly like every other llm.py function's no-client fallback."""
    products = [
        {"id": "prod_mic_fifine_k669b", "name": "FIFINE K669B USB 電容式麥克風", "tags": ["麥克風", "podcast"]},
    ]
    assert llm.recommend_shop_products("我想要錄podcast用的麥克風", products) is None


def test_recommend_shop_products_maps_llm_recommendations_to_full_product_dicts():
    products = [
        {"id": "prod_a", "name": "A 商品", "tags": []},
        {"id": "prod_b", "name": "B 商品", "tags": []},
    ]
    with patch(
        "backend.app.agent.llm._converse_json",
        return_value={"recommendations": [{"product_id": "prod_b", "reason": "比較適合"}]},
    ):
        result = llm.recommend_shop_products("隨便問問", products)
    assert result == [{"id": "prod_b", "name": "B 商品", "tags": [], "reason": "比較適合"}]


def test_recommend_shop_products_ignores_unknown_product_ids_from_llm():
    products = [{"id": "prod_a", "name": "A 商品", "tags": []}]
    with patch(
        "backend.app.agent.llm._converse_json",
        return_value={"recommendations": [{"product_id": "does_not_exist", "reason": "x"}]},
    ):
        result = llm.recommend_shop_products("隨便問問", products)
    assert result is None
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest backend/tests/test_shop_recommendation.py -v`
Expected: FAIL — `AttributeError: module 'backend.app.agent.llm' has no attribute 'recommend_shop_products'`

- [ ] **Step 3: Add the function**

In `backend/app/agent/llm.py`, add the system prompt constant near the other `_..._SYSTEM` constants (after `_PAGE_HELP_SYSTEM`):

```python
_SHOP_RECOMMEND_SYSTEM = (
    "You are a Taiwanese shopping assistant speaking Traditional Chinese. "
    "Given the user's need or usage scenario, pick up to 5 best-matching products "
    "from the provided catalog (each item includes brand/store, price, average rating, "
    "review count, and tags). Prefer higher-rated products when several fit equally well. "
    "Justify each pick in one Traditional Chinese sentence referencing price, rating, or fit "
    "for the user's scenario. Only choose product_id values that exist in the catalog; never invent one. "
    "Return JSON only in the format {\"recommendations\": [{\"product_id\": string, \"reason\": string}]}."
)
```

Add the function at the end of the file (after `compose_page_help_reply`):

```python
def recommend_shop_products(query: str, products: list[dict]) -> list[dict] | None:
    prompt = json.dumps({"query": query, "products": products}, ensure_ascii=False)
    payload = _converse_json(_SHOP_RECOMMEND_SYSTEM, prompt, max_tokens=512)
    if not payload or not isinstance(payload.get("recommendations"), list):
        return None
    by_id = {p["id"]: p for p in products}
    items = []
    for rec in payload["recommendations"]:
        product = by_id.get(rec.get("product_id"))
        if not product:
            continue
        items.append({**product, "reason": rec.get("reason", "")})
    return items or None
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest backend/tests/test_shop_recommendation.py -v`
Expected: PASS — all 3 tests

- [ ] **Step 5: Commit**

```bash
git add backend/app/agent/llm.py backend/tests/test_shop_recommendation.py
git commit -m "feat: add llm.recommend_shop_products using the existing Bedrock converse client"
```

---

### Task 8: Add `shop_recommendation.py` (fallback + orchestration)

**Files:**
- Create: `backend/app/services/shop_recommendation.py`
- Test: `backend/tests/test_shop_recommendation.py` (extended)

**Interfaces:**
- Consumes: `llm.recommend_shop_products(query, products) -> list[dict] | None` (Task 7).
- Produces: `fallback_recommend(query: str, products: list[dict]) -> list[dict]`, `recommend(query: str, products: list[dict]) -> dict` (returns `{"query", "recommendations", "fallback_used"}`). Consumed by Task 9's embedded tool.

- [ ] **Step 1: Write the failing tests**

Add to `backend/tests/test_shop_recommendation.py`:

```python
from backend.app.services import shop_catalog, shop_recommendation


def _electronics_products():
    return shop_catalog.list_products(category_id="cat_electronics")


def test_fallback_recommend_matches_by_tag_keyword():
    recs = shop_recommendation.fallback_recommend("我想要錄podcast用的麥克風", _electronics_products())
    assert len(recs) > 0
    assert all("麥克風" in rec.get("tags", []) or "podcast" in rec.get("tags", []) for rec in recs)


def test_fallback_recommend_falls_back_to_top_rated_when_no_match():
    products = _electronics_products()
    recs = shop_recommendation.fallback_recommend("完全不相關的字串xyz", products)
    assert len(recs) == min(5, len(products))
    ratings = [rec["rating_avg"] for rec in recs]
    assert ratings == sorted(ratings, reverse=True)


def test_fallback_recommend_includes_a_reason_string():
    recs = shop_recommendation.fallback_recommend("麥克風", _electronics_products())
    assert all(rec["reason"] for rec in recs)


def test_recommend_uses_llm_result_when_available():
    products = [{"id": "prod_a", "name": "A 商品", "tags": [], "rating_avg": 4.5, "rating_count": 10}]
    with patch(
        "backend.app.services.shop_recommendation.llm.recommend_shop_products",
        return_value=[{**products[0], "reason": "LLM 理由"}],
    ):
        result = shop_recommendation.recommend("query", products)
    assert result["fallback_used"] is False
    assert result["recommendations"] == [{**products[0], "reason": "LLM 理由"}]


def test_recommend_falls_back_when_llm_unavailable():
    products = _electronics_products()
    with patch("backend.app.services.shop_recommendation.llm.recommend_shop_products", return_value=None):
        result = shop_recommendation.recommend("我想要錄podcast用的麥克風", products)
    assert result["fallback_used"] is True
    assert len(result["recommendations"]) > 0
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest backend/tests/test_shop_recommendation.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'backend.app.services.shop_recommendation'`

- [ ] **Step 3: Create `backend/app/services/shop_recommendation.py`**

```python
"""Shopping need -> product recommendation engine. Bedrock-backed (see
app/agent/llm.py's recommend_shop_products, which reuses the same
_converse_json client already used for service routing/form-filling),
with a keyword/tag/rating fallback when Bedrock is unavailable. Mirrors the
shape of health_recommendation.py's recommend()/fallback_recommend()."""
from __future__ import annotations

from ..agent import llm


def fallback_recommend(query: str, products: list[dict]) -> list[dict]:
    def match_score(product: dict) -> int:
        tags = product.get("tags", [])
        name_hit = 1 if product["name"] in query or any(keyword in product["name"] for keyword in tags) else 0
        return sum(1 for tag in tags if tag in query) + name_hit

    scored = [(match_score(p), p) for p in products]
    matched = [p for score, p in scored if score > 0]
    pool = matched if matched else products
    ranked = sorted(pool, key=lambda p: (-p.get("rating_avg", 0), -p.get("rating_count", 0)))
    return [
        {
            **p,
            "reason": (
                f"依標籤與評分挑選：{'、'.join(p.get('tags', [])) or p['description']}"
                f"（★{p.get('rating_avg')}，{p.get('rating_count')} 則評價）"
            ),
        }
        for p in ranked[:5]
    ]


def recommend(query: str, products: list[dict]) -> dict:
    """Returns {"query", "recommendations", "fallback_used"}."""
    recommendations = llm.recommend_shop_products(query, products)
    if recommendations is not None:
        return {"query": query, "recommendations": recommendations, "fallback_used": False}
    return {"query": query, "recommendations": fallback_recommend(query, products), "fallback_used": True}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest backend/tests/test_shop_recommendation.py -v`
Expected: PASS — all 8 tests (3 from Task 7 + 5 new)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/shop_recommendation.py backend/tests/test_shop_recommendation.py
git commit -m "feat: add shop_recommendation.py with keyword/rating fallback"
```

---

### Task 9: Wire the recommendation into the chat agent (`shop_product_advisor`)

**Files:**
- Modify: `backend/app/agent/tools.py`
- Modify: `backend/app/services/catalog.py`
- Modify: `backend/app/agent/agent.py`
- Test: `backend/tests/test_shop_product_advisor.py` (new file, mirrors `test_shop_price_compare.py`'s all-in-one-file convention)

**Interfaces:**
- Consumes: `shop_recommendation.recommend(query, products) -> dict` (Task 8), `shop_catalog.list_products() -> list[dict]` (existing), `tools.call(tool_name, params, auth_token=None) -> dict` (existing), `_reply(state, reply, redirect_path=None, redirect_requires_confirmation=False) -> dict` (existing, `agent.py:1756`).
- Produces: embedded tool `recommend_shop_products_by_need`; service `shop_product_advisor` in `catalog.SERVICES`; agent interception that answers directly with a redirect to `/services/shop_purchase?category_id=<id>`.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_shop_product_advisor.py`:

```python
"""Tests for the AI shop product advisor: service registration, the embedded
recommend_shop_products_by_need tool, and the agent's chat interception."""
from unittest.mock import patch

from backend.app.agent import agent, tools
from backend.app.services import catalog


def test_shop_product_advisor_registered_in_service_list():
    services = catalog.list_services()
    ids = [s["id"] for s in services]
    assert "shop_product_advisor" in ids


def test_shop_product_advisor_schema_has_single_query_field():
    schema = catalog.get_service_schema("shop_product_advisor")
    field_ids = [f["id"] for f in schema["fields"]]
    assert field_ids == ["query"]


def test_embedded_shop_advisor_tool_requires_query():
    result = tools.call("recommend_shop_products_by_need", {"query": ""})
    assert result["success"] is False
    assert result["error"]["code"] == "INVALID_QUERY"


def test_embedded_shop_advisor_tool_returns_recommendations_for_mic_query():
    result = tools.call("recommend_shop_products_by_need", {"query": "我想要錄podcast用的麥克風"})
    assert result["success"] is True
    assert isinstance(result["recommendations"], list)
    assert len(result["recommendations"]) > 0
    assert any("麥克風" in rec["name"] for rec in result["recommendations"])


def test_agent_detects_shop_product_advisor_and_replies_with_redirect():
    state = agent.new_state()

    with patch(
        "backend.app.agent.agent._available_services",
        return_value=[
            {
                "id": "shop_product_advisor",
                "name": "AI 選購顧問",
                "description": "說出你的使用情境或想要的商品，AI 幫你比較不同品牌、參考評分與評價推薦",
                "keywords": ["推薦", "選購", "麥克風"],
            }
        ],
    ):
        result = agent.handle_message("user-1", "sess-1", state, "我想要錄podcast用的麥克風，可以推薦一下嗎")

    assert result["state"]["service_id"] is None
    assert result["state"]["request_id"] is None
    assert result["redirect_path"] == "/services/shop_purchase?category_id=cat_electronics"
    assert result["redirect_requires_confirmation"] is True
    assert "★" in result["reply"]


def test_agent_shop_product_advisor_tool_failure_has_no_redirect():
    state = agent.new_state()

    with patch(
        "backend.app.agent.agent._available_services",
        return_value=[
            {
                "id": "shop_product_advisor",
                "name": "AI 選購顧問",
                "description": "說出你的使用情境或想要的商品，AI 幫你比較不同品牌、參考評分與評價推薦",
                "keywords": ["推薦", "選購", "麥克風"],
            }
        ],
    ), patch(
        "backend.app.agent.agent.tools.call",
        return_value={"success": False, "error": {"code": "INVALID_QUERY", "message": "query is required."}},
    ):
        result = agent.handle_message("user-1", "sess-1", state, "我想要錄podcast用的麥克風")

    assert result["redirect_path"] is None
    assert result["redirect_requires_confirmation"] is False
    assert "查詢失敗" in result["reply"] or "沒有成功" in result["reply"]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest backend/tests/test_shop_product_advisor.py -v`
Expected: FAIL — `shop_product_advisor` not in service list / `Unknown tool: recommend_shop_products_by_need`

- [ ] **Step 3: Register the embedded tool in `tools.py`**

In `backend/app/agent/tools.py`, update the services import line:

```python
from ..services import catalog, health_catalog, health_recommendation, shop_catalog, shop_recommendation
```

(replacing the existing `from ..services import catalog, health_catalog, health_recommendation, shop_catalog` line)

Add the handler function after `_embedded_compare_product_prices`:

```python
def _embedded_recommend_shop_products_by_need(params: dict) -> dict:
    query = str(params.get("query") or "").strip()
    if not query:
        return {"success": False, "error": {"code": "INVALID_QUERY", "message": "query is required."}}
    result = shop_recommendation.recommend(query, shop_catalog.list_products())
    return {"success": True, **result}
```

Register it in `_EMBEDDED_TOOLS` (add the line after `"compare_product_prices": _embedded_compare_product_prices,`):

```python
    "recommend_shop_products_by_need": _embedded_recommend_shop_products_by_need,
```

- [ ] **Step 4: Register the service in `catalog.py`**

In `backend/app/services/catalog.py`, add this entry to `SERVICES` right after the `shop_price_compare` entry (before `restaurant_reservation`):

```python
    {
        "id": "shop_product_advisor",
        "name": "AI 選購顧問",
        "description": "說出你的使用情境或想要的商品，AI 幫你比較不同品牌、參考評分與評價推薦",
        "service_vendor_id": None,
        "cms_type": None,
        "enabled": True,
        "keywords": [
            "推薦", "選購", "選購建議", "評價", "評分", "哪款好", "哪個牌子",
            "怎麼選", "幫我選", "AI選購", "麥克風", "耳機", "3C", "電子產品",
        ],
        "schema": {
            "fields": [
                {
                    "id": "query",
                    "label": "想選購的商品或情境",
                    "type": "textarea",
                    "required": True,
                    "question": "請問想要什麼樣的商品？可以描述你的使用情境，例如「我想要錄 podcast 用的麥克風」。",
                },
            ],
        },
    },
```

- [ ] **Step 5: Add the agent interception and helpers in `agent.py`**

Add the interception block right after the existing `shop_price_compare` block (after the `return _reply(...)` that closes it, before `if llm.is_available():` at line 1291):

```python
        if service_id == "shop_product_advisor":
            # One-shot query-and-answer service (like health_product_recommendation
            # and shop_price_compare): answer directly with recommendations instead
            # of collecting form fields.
            reply, redirect_path = _answer_shop_product_advisor(text, auth_token)
            state["service_id"] = None
            state["service_name"] = None
            state["service_schema"] = None
            state["collected_fields"] = {}
            state["missing_fields"] = []
            return _reply(
                state,
                reply,
                redirect_path=redirect_path,
                redirect_requires_confirmation=redirect_path is not None,
            )
```

Add the helper functions right after `_answer_price_compare` (added in Task 1):

```python
def _format_shop_advisor_reply(result: dict) -> str:
    recommendations = result.get("recommendations") or []
    if not recommendations:
        return "很抱歉，目前商城沒有找到符合這個需求的商品，要不要換個方式描述你的需求？"
    lines = ["這是我幫你比較後找到的推薦："]
    for index, rec in enumerate(recommendations, start=1):
        price = rec.get("skus", [{}])[0].get("unit_price", "?")
        lines.append(
            f"{index}. {rec.get('name', '')}（{rec.get('store_name', '')}）NT${price} "
            f"★{rec.get('rating_avg')}（{rec.get('rating_count')} 則評價）\n　{rec.get('reason', '')}"
        )
    if result.get("fallback_used"):
        lines.append("（這次是用關鍵字與評分挑選的，僅供參考）")
    lines.append("我幫你打開商城，可以直接比較選購。")
    return "\n".join(lines)


def _answer_shop_product_advisor(query: str, auth_token: str | None) -> tuple[str, str | None]:
    result = tools.call("recommend_shop_products_by_need", {"query": query}, auth_token=auth_token)
    if not result.get("success"):
        message = result.get("error", {}).get("message", "查詢失敗")
        return f"抱歉，這次查詢沒有成功，原因是：{message}。你可以稍後再試一次。", None
    reply = _format_shop_advisor_reply(result)
    recommendations = result.get("recommendations") or []
    category_id = recommendations[0].get("category_id") if recommendations else None
    redirect_path = f"/services/shop_purchase?category_id={category_id}" if category_id else "/services/shop_purchase"
    return reply, redirect_path
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `python -m pytest backend/tests/test_shop_product_advisor.py -v`
Expected: PASS — all 6 tests

- [ ] **Step 7: Run the full backend suite**

Run: `python -m pytest backend -q`
Expected: all tests pass, total count higher than the Task 1 baseline, zero failures — this also confirms the new "推薦"/"選購" keywords in `shop_product_advisor` didn't break `health_product_recommendation`'s or `shop_price_compare`'s existing routing tests

- [ ] **Step 8: Commit**

```bash
git add backend/app/agent/tools.py backend/app/services/catalog.py backend/app/agent/agent.py backend/tests/test_shop_product_advisor.py
git commit -m "feat: wire shop_product_advisor into the chat agent"
```

---

### Task 10: Frontend types and API client

**Files:**
- Modify: `frontend/src/types/shop.ts`
- Modify: `frontend/src/api/shop.ts`

**Interfaces:**
- Produces: `ShopProduct.rating_avg: number`, `ShopProduct.rating_count: number`, `ShopReview` interface, `getShopProductReviews(productId: string): Promise<{ reviews: ShopReview[] }>`.

- [ ] **Step 1: Update `frontend/src/types/shop.ts`**

In the existing `ShopProduct` interface, add two fields after `compare_group_id: string | null;`:

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
  rating_avg: number;
  rating_count: number;
}
```

Add a new interface after `ShopCompareGroup`:

```ts
export interface ShopReview {
  review_id: string;
  author: string;
  rating: number;
  comment: string;
  created_at: string;
  verified_purchase: boolean;
}
```

- [ ] **Step 2: Update `frontend/src/api/shop.ts`**

Add the import for the new type (update the existing `import type { ... } from "../types/shop";` block to include `ShopReview`):

```ts
import type {
  ShopCategory,
  ShopCompareGroup,
  ShopOrder,
  ShopPointsBalance,
  ShopProduct,
  ShopReview,
  ShopStore,
  ShopSubmitPayload,
  ShopSubmitResult,
} from "../types/shop";
```

Add the new function after `getShopProduct`:

```ts
export function getShopProductReviews(productId: string): Promise<{ reviews: ShopReview[] }> {
  return api(`/api/shop/products/${encodeURIComponent(productId)}/reviews`);
}
```

- [ ] **Step 3: Verify the frontend still typechecks**

Run: `cd frontend && npx tsc --noEmit`
Expected: FAIL at this point — `ShopFlowPage.test.tsx`'s existing product fixtures are missing `rating_avg`/`rating_count`, which are now required fields. This is expected; Task 12 fixes the fixtures. Confirm the *only* new errors are about `rating_avg`/`rating_count` being missing from object literals in `ShopFlowPage.test.tsx`, not anything else.

- [ ] **Step 4: Commit**

```bash
cd frontend && git add src/types/shop.ts src/api/shop.ts
git commit -m "feat: add rating fields and ShopReview type to shop frontend types/api"
```

---

### Task 11: `RatingStars` component

**Files:**
- Create: `frontend/src/components/RatingStars.tsx`
- Test: `frontend/src/components/RatingStars.test.tsx`

**Interfaces:**
- Produces: `RatingStars({ rating: number; count?: number })` — a presentational component. Consumed by Task 12.

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/RatingStars.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { RatingStars } from "./RatingStars";

describe("RatingStars", () => {
  it("renders the numeric rating and review count", () => {
    render(<RatingStars rating={4.6} count={128} />);
    expect(screen.getByText(/4\.6/)).toBeInTheDocument();
    expect(screen.getByText(/128/)).toBeInTheDocument();
  });

  it("renders without a count when count is omitted", () => {
    render(<RatingStars rating={5} />);
    expect(screen.getByText(/5\.0/)).toBeInTheDocument();
    expect(screen.queryByText(/（/)).not.toBeInTheDocument();
  });

  it("renders without a count when count is zero", () => {
    render(<RatingStars rating={0} count={0} />);
    expect(screen.queryByText(/（/)).not.toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd frontend && npx vitest run src/components/RatingStars.test.tsx`
Expected: FAIL — `Failed to resolve import "./RatingStars"`

- [ ] **Step 3: Create `frontend/src/components/RatingStars.tsx`**

```tsx
interface Props {
  rating: number;
  count?: number;
}

/**
 * 星等＋數字＋則數的純展示元件（例："★★★★☆ 4.6（128）"）。
 * 商品卡片、比價清單、評價清單共用。
 */
export function RatingStars({ rating, count }: Props) {
  const filled = Math.max(0, Math.min(5, Math.round(rating)));
  const stars = "★".repeat(filled) + "☆".repeat(5 - filled);

  return (
    <span className="inline-flex items-center gap-1 text-sm text-[var(--color-muted-foreground)]">
      <span className="text-[var(--color-primary-accent)]" aria-hidden="true">
        {stars}
      </span>
      <span>
        {rating.toFixed(1)}
        {typeof count === "number" && count > 0 ? `（${count}）` : ""}
      </span>
    </span>
  );
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd frontend && npx vitest run src/components/RatingStars.test.tsx`
Expected: PASS — all 3 tests

- [ ] **Step 5: Commit**

```bash
cd frontend && git add src/components/RatingStars.tsx src/components/RatingStars.test.tsx
git commit -m "feat: add RatingStars presentational component"
```

---

### Task 12: `ShopFlowPage.tsx` — ratings, sort, reviews panel, deep link

**Files:**
- Modify: `frontend/src/pages/ShopFlowPage.tsx`
- Modify: `frontend/src/pages/ShopFlowPage.test.tsx`

**Interfaces:**
- Consumes: `RatingStars` (Task 11), `getShopProductReviews` (Task 10), `ShopReview` (Task 10).

- [ ] **Step 1: Update the existing test fixtures to include the now-required rating fields**

In `frontend/src/pages/ShopFlowPage.test.tsx`, add `rating_avg` and `rating_count` to all 5 existing product fixture objects (`products[0]`, `products[1]`, `dailyProducts[0]`, `comparableProducts[0]`, `comparableProducts[1]`). For example, `prod_a` becomes:

```ts
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
    rating_avg: 4.5,
    rating_count: 10,
  },
```

Apply the same two-field addition, with these exact values, to the other 4 fixtures:

`prod_b` gets `rating_avg: 4.0, rating_count: 5`:
```ts
    skus: [{ sku_id: "sku_b", attributes: {}, unit_price: 80, unit_points: 8 }],
    rating_avg: 4.0,
    rating_count: 5,
  },
```

`prod_c` (in `dailyProducts`) gets `rating_avg: 4.8, rating_count: 20`:
```ts
    skus: [{ sku_id: "sku_c", attributes: {}, unit_price: 100, unit_points: 10 }],
    rating_avg: 4.8,
    rating_count: 20,
  },
```

`prod_x1` (in `comparableProducts`) gets `rating_avg: 3.5, rating_count: 8`:
```ts
    skus: [{ sku_id: "sku_x1", attributes: {}, unit_price: 100, unit_points: 10 }],
    rating_avg: 3.5,
    rating_count: 8,
  },
```

`prod_x2` (in `comparableProducts`) gets `rating_avg: 4.9, rating_count: 30`:
```ts
    skus: [{ sku_id: "sku_x2", attributes: {}, unit_price: 80, unit_points: 8 }],
    rating_avg: 4.9,
    rating_count: 30,
  },
```

Add a new fixture array for the sort test, right after the `comparableProducts` array declaration (needs two *distinct, ungrouped* products — `comparableProducts` share one `compare_group_id` and would render as a single merged card, which can't demonstrate card reordering):

```ts
  const sortableProducts = [
    {
      id: "prod_low",
      store_id: "store_low",
      store_name: "Low 店家",
      category_id: "cat_daily",
      compare_group_id: null,
      name: "評分較低商品",
      description: "描述 Low",
      product_type: "SERIAL_CODE" as const,
      image: null,
      specs: [],
      skus: [{ sku_id: "sku_low", attributes: {}, unit_price: 50, unit_points: 5 }],
      rating_avg: 3.0,
      rating_count: 4,
    },
    {
      id: "prod_high",
      store_id: "store_high",
      store_name: "High 店家",
      category_id: "cat_daily",
      compare_group_id: null,
      name: "評分較高商品",
      description: "描述 High",
      product_type: "SERIAL_CODE" as const,
      image: null,
      specs: [],
      skus: [{ sku_id: "sku_high", attributes: {}, unit_price: 60, unit_points: 6 }],
      rating_avg: 4.9,
      rating_count: 40,
    },
  ];
```

Also add default mocks for the two new API functions in the `beforeEach` block:

```ts
beforeEach(() => {
  vi.mocked(shopApi.listShopCategories).mockResolvedValue({ categories });
  vi.mocked(shopApi.listShopProducts).mockResolvedValue({ products });
  vi.mocked(shopApi.getShopPoints).mockResolvedValue({ balance: 0 });
  vi.mocked(shopApi.getShopProductReviews).mockResolvedValue({ reviews: [] });
});
```

- [ ] **Step 2: Run the existing tests to confirm they still pass with the fixture update alone**

Run: `cd frontend && npx vitest run src/pages/ShopFlowPage.test.tsx`
Expected: PASS — all pre-existing tests (this step isolates "did I break anything by adding fields" from "do the new features work")

- [ ] **Step 3: Write the new failing tests**

Add to `frontend/src/pages/ShopFlowPage.test.tsx` (inside the `describe("ShopFlowPage", ...)` block):

```tsx
  it("shows the rating on each product card", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(await screen.findByText("飲品兌換"));

    expect(await screen.findByText(/4\.5/)).toBeInTheDocument();
  });

  it("sorts product cards by rating, highest first, when the sort toggle is on", async () => {
    const user = userEvent.setup();
    vi.mocked(shopApi.listShopProducts).mockResolvedValue({ products: sortableProducts });
    renderPage();

    await user.click(await screen.findByText("飲品兌換"));
    await screen.findByText("評分較低商品");

    const beforeOrder = screen.getAllByText(/評分較(低|高)商品/).map((el) => el.textContent);
    expect(beforeOrder).toEqual(["評分較低商品", "評分較高商品"]); // default order matches API response order

    await user.click(screen.getByText("依評分排序"));

    const afterOrder = screen.getAllByText(/評分較(低|高)商品/).map((el) => el.textContent);
    expect(afterOrder).toEqual(["評分較高商品", "評分較低商品"]); // now sorted highest-rated first
  });

  it("shows reviews when the review panel is expanded", async () => {
    const user = userEvent.setup();
    vi.mocked(shopApi.getShopProductReviews).mockResolvedValue({
      reviews: [
        {
          review_id: "rev_1",
          author: "小明",
          rating: 5,
          comment: "很好用！",
          created_at: "2026-05-01",
          verified_purchase: true,
        },
      ],
    });
    renderPage();

    await user.click(await screen.findByText("飲品兌換"));
    await user.click(await screen.findByText("商品 A"));
    await user.click(screen.getByText("查看評價"));

    expect(await screen.findByText("很好用！")).toBeInTheDocument();
    expect(screen.getByText("小明")).toBeInTheDocument();
    expect(shopApi.getShopProductReviews).toHaveBeenCalledWith("prod_a");
  });

  it("does not fetch reviews until the review panel is opened", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(await screen.findByText("飲品兌換"));
    await user.click(await screen.findByText("商品 A"));

    expect(shopApi.getShopProductReviews).not.toHaveBeenCalled();
  });

  it("opens directly to the product list for a category when the URL has a category_id param", async () => {
    vi.mocked(shopApi.listShopProducts).mockResolvedValue({ products: dailyProducts });

    renderPageAtRoute("/services/shop_purchase?category_id=cat_daily");

    expect(await screen.findByText("商品 C")).toBeInTheDocument();
    expect(shopApi.listShopProducts).toHaveBeenCalledWith("cat_daily");
    expect(screen.queryByText("請選擇商品類型")).not.toBeInTheDocument();
  });
```

- [ ] **Step 4: Run the tests to verify the new ones fail**

Run: `cd frontend && npx vitest run src/pages/ShopFlowPage.test.tsx`
Expected: FAIL — the 5 new tests fail (no rating displayed, no sort button, no review panel, no deep link handling yet)

- [ ] **Step 5: Add the imports and new state to `ShopFlowPage.tsx`**

Update the imports at the top of `frontend/src/pages/ShopFlowPage.tsx`:

```tsx
import { RatingStars } from "../components/RatingStars";
import {
  cancelShopOrder,
  getShopCompareGroup,
  getShopOrder,
  getShopPoints,
  getShopProductReviews,
  listShopCategories,
  listShopProducts,
  simulateShopOrderProgress,
  submitShopOrder,
} from "../api/shop";
import type { ShopCartLine, ShopCategory, ShopOrder, ShopProduct, ShopReview, ShopSubmitResult } from "../types/shop";
```

Add new state right after the existing `comparingGroupId`/`selectedSpecs` state declarations:

```tsx
  const [sortByRating, setSortByRating] = useState(false);
  const [showReviews, setShowReviews] = useState(false);
  const [reviews, setReviews] = useState<ShopReview[]>([]);
```

- [ ] **Step 6: Add the `category_id` deep link effect**

Add right after the existing `compareParam` `useEffect` block (after its closing `}, [compareParam]);`):

```tsx
  const categoryIdParam = searchParams.get("category_id");

  useEffect(() => {
    if (!categoryIdParam) return;
    setSelectedCategoryId(categoryIdParam);
    setStepIndex(STEP_ORDER.indexOf("product"));
  }, [categoryIdParam]);
```

- [ ] **Step 7: Add the reviews-reset and reviews-fetch effects**

Add right after the `matchedSku` `useMemo` block:

```tsx
  useEffect(() => {
    setShowReviews(false);
    setReviews([]);
  }, [activeProduct?.id]);

  useEffect(() => {
    if (!showReviews || !activeProduct) return;
    getShopProductReviews(activeProduct.id)
      .then((res) => setReviews(res.reviews))
      .catch(() => setToastText("評價載入失敗"));
  }, [showReviews, activeProduct]);
```

- [ ] **Step 8: Add the sorted-groups derivation**

Add right after the `productGroups` `useMemo` block (before `comparingOffers`):

```tsx
  const visibleGroups = useMemo(() => {
    if (!sortByRating) return productGroups;
    return [...productGroups].sort(
      (a, b) => Math.max(...b.offers.map((o) => o.rating_avg)) - Math.max(...a.offers.map((o) => o.rating_avg)),
    );
  }, [productGroups, sortByRating]);
```

- [ ] **Step 9: Add the sort toggle button and switch the render to `visibleGroups`**

In the Step 2 section (`{step === "product" && (...)}`), change the opening paragraph + product list block from:

```tsx
            <p className="text-base font-bold leading-relaxed text-[var(--color-foreground)]">請選擇商品</p>
            <div className="flex flex-col gap-3">
              {productGroups.map((group) => {
```

to:

```tsx
            <p className="text-base font-bold leading-relaxed text-[var(--color-foreground)]">請選擇商品</p>
            <button
              type="button"
              onClick={() => setSortByRating((v) => !v)}
              aria-pressed={sortByRating}
              className={`self-start rounded-full border-2 px-4 py-2 text-sm font-bold transition ${
                sortByRating
                  ? "border-brand bg-brand/5 text-brand"
                  : "border-[var(--color-border)] text-[var(--color-muted-foreground)] hover:border-[var(--color-primary)]"
              }`}
            >
              依評分排序
            </button>
            <div className="flex flex-col gap-3">
              {visibleGroups.map((group) => {
```

- [ ] **Step 10: Add rating display to the grouped (multi-vendor) product card**

Inside the same `.map()` callback, in the `if (group.offers.length > 1) { ... }` branch, change:

```tsx
                      <p className="text-base font-bold text-[var(--color-foreground)]">{group.offers[0].name}</p>
                      <p className="text-sm text-[var(--color-muted-foreground)]">
                        NT${Math.min(...prices)}~{Math.max(...prices)}
                      </p>
                      <p className="text-xs text-[var(--color-muted-foreground)]">共 {group.offers.length} 家店販售</p>
```

to:

```tsx
                      <p className="text-base font-bold text-[var(--color-foreground)]">{group.offers[0].name}</p>
                      <p className="text-sm text-[var(--color-muted-foreground)]">
                        NT${Math.min(...prices)}~{Math.max(...prices)}
                      </p>
                      <p className="text-xs text-[var(--color-muted-foreground)]">共 {group.offers.length} 家店販售</p>
                      <RatingStars rating={Math.max(...group.offers.map((o) => o.rating_avg))} />
```

- [ ] **Step 11: Add rating display to the single-vendor product card**

In the same `.map()` callback's single-product branch, change:

```tsx
                    <p className="text-base font-bold text-[var(--color-foreground)]">{product.name}</p>
                    <p className="text-sm text-[var(--color-muted-foreground)]">NT${product.skus[0]?.unit_price}</p>
                    <p className="text-xs text-[var(--color-muted-foreground)]">{product.store_name}</p>
```

to:

```tsx
                    <p className="text-base font-bold text-[var(--color-foreground)]">{product.name}</p>
                    <p className="text-sm text-[var(--color-muted-foreground)]">NT${product.skus[0]?.unit_price}</p>
                    <p className="text-xs text-[var(--color-muted-foreground)]">{product.store_name}</p>
                    <RatingStars rating={product.rating_avg} count={product.rating_count} />
```

- [ ] **Step 12: Add rating display to each compare-offer row**

In the `comparingGroupId && (...)` block, change:

```tsx
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-[var(--color-foreground)]">{offer.store_name}</span>
                      {index === 0 && (
                        <span className="rounded-full bg-[var(--color-success-soft)] px-2 py-0.5 text-xs font-bold text-[var(--color-success)]">
                          最便宜
                        </span>
                      )}
                    </div>
```

to:

```tsx
                    <div className="flex flex-col gap-1">
                      <div className="flex items-center gap-2">
                        <span className="text-sm text-[var(--color-foreground)]">{offer.store_name}</span>
                        {index === 0 && (
                          <span className="rounded-full bg-[var(--color-success-soft)] px-2 py-0.5 text-xs font-bold text-[var(--color-success)]">
                            最便宜
                          </span>
                        )}
                      </div>
                      <RatingStars rating={offer.rating_avg} count={offer.rating_count} />
                    </div>
```

- [ ] **Step 13: Add the reviews panel to the spec-selection card**

In the `activeProduct && (...)` block, add this right after the "加入購物車" button (still inside the same `<div>`):

```tsx
                <button
                  type="button"
                  onClick={() => setShowReviews((v) => !v)}
                  className="text-sm font-bold text-brand underline"
                >
                  {showReviews ? "收合評價" : "查看評價"}
                </button>
                {showReviews && (
                  <div className="flex flex-col gap-3 rounded-xl bg-[var(--color-canvas)] p-3">
                    {reviews.length === 0 && (
                      <p className="text-sm text-[var(--color-muted-foreground)]">目前還沒有評價</p>
                    )}
                    {reviews.map((review) => (
                      <div
                        key={review.review_id}
                        className="flex flex-col gap-1 border-b border-[var(--color-border)] pb-2 last:border-b-0 last:pb-0"
                      >
                        <div className="flex items-center justify-between">
                          <span className="text-sm font-bold text-[var(--color-foreground)]">{review.author}</span>
                          <span className="text-xs text-[var(--color-muted-foreground)]">{review.created_at}</span>
                        </div>
                        <RatingStars rating={review.rating} />
                        {review.verified_purchase && (
                          <span className="w-fit rounded-full bg-[var(--color-success-soft)] px-2 py-0.5 text-xs font-bold text-[var(--color-success)]">
                            已購買
                          </span>
                        )}
                        <p className="text-sm text-[var(--color-foreground)]">{review.comment}</p>
                      </div>
                    ))}
                  </div>
                )}
```

- [ ] **Step 14: Run the tests to verify they pass**

Run: `cd frontend && npx vitest run src/pages/ShopFlowPage.test.tsx`
Expected: PASS — all tests, pre-existing and new

- [ ] **Step 15: Typecheck the whole frontend**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors (this confirms Task 10's earlier expected type error is now resolved)

- [ ] **Step 16: Commit**

```bash
cd frontend && git add src/pages/ShopFlowPage.tsx src/pages/ShopFlowPage.test.tsx
git commit -m "feat: show ratings, add rating sort, review panel, and category_id deep link to ShopFlowPage"
```

---

### Task 13: Final integration — reseed stock, full test suite, lambda_tools consistency

**Files:**
- No file changes expected (verification-only task); may touch `backend/.local-store.json` (gitignored local mock store) as a side effect of running the seed script.

- [ ] **Step 1: Re-run the stock seed script for the new SKUs**

Run: `python backend/scripts/seed_shop_points.py`
Expected: output includes 7 new lines like `Seeded sku_mic_fifine_k669b with 20 in stock.` (one per new SKU from Task 2) alongside `Skipped ...` lines for every pre-existing SKU

- [ ] **Step 2: Run the full backend test suite**

Run: `python -m pytest backend -q`
Expected: all tests pass, 0 failures

- [ ] **Step 3: Run the full lambda_tools test suite**

Run: `python -m pytest lambda_tools -q`
Expected: all tests pass, 0 failures

- [ ] **Step 4: Run the full frontend test suite**

Run: `cd frontend && npx vitest run`
Expected: all tests pass, 0 failures

- [ ] **Step 5: Confirm the lambda_tools catalog copy is still identical to the backend copy**

Run: `diff backend/app/services/shop_catalog.py lambda_tools/shared_lambda/shop_catalog.py`
Expected: no output (still identical — nothing since Task 3 touched either file, this is a final guard)

- [ ] **Step 6: Manual smoke test of the chat flow (requires the dev servers running)**

This step needs a real `.env` with AWS credentials (the isolated worktree used for this plan does not have one — `backend/.env` is gitignored and was not copied into the worktree). Run this from an environment that has `USE_MOCK=false` and valid AWS credentials configured, most likely the main checkout, after merging this branch:

```bash
cd backend && uvicorn app.main:app --reload
```
In another terminal:
```bash
cd frontend && npm run dev
```
Then in the browser: log in, open the AI 管家 chat, and type "我想要錄podcast用的麥克風". Confirm:
- The reply lists multiple mic brands with prices, star ratings, and reasons
- Clicking through the redirect lands on `/services/shop_purchase?category_id=cat_electronics` showing the 3C 影音周邊 product list
- Product cards show ratings; "依評分排序" reorders them; "查看評價" expands real review text

If the reply falls back to "（這次是用關鍵字與評分挑選的，僅供參考）" instead of an LLM-composed reason, see the "Bedrock 部署備忘" section of `docs/superpowers/specs/2026-08-01-shop-ai-product-advisor-design.md` for how to diagnose (Bedrock model access / IAM permissions / region support).

- [ ] **Step 7: Final commit (only if Step 1's seed run produced tracked-file changes — normally it only touches the gitignored local store)**

```bash
git status
```
If `git status` shows no changes, there is nothing to commit — the plan is complete. If it shows changes to tracked files, review them, then:
```bash
git add -A
git commit -m "chore: final verification pass for shop AI product advisor"
```
