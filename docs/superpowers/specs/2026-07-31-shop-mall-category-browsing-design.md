# 商城購物：品類優先瀏覽 Design

## 背景

現行「商城購物」（`ShopFlowPage.tsx` / `service_id: shop_purchase`）流程是「選店家 → 該店家商品 → 購物車 → 結帳」。商品目前只掛在店家底下，且兩家既有店家（7-11、統一時代選物）賣的商品類型完全不重疊，無法呈現「同一種商品，不同廠商可以比較選購」的情境。

使用者希望改成類似蝦皮的體驗：先選「商品品類」，再看到該品類下不同廠商的類似商品，最後才選購。這需要同時調整資料模型（商品要有品類歸屬）與前端瀏覽流程（品類取代店家成為第一步）。

## 目標與範圍

**範圍內：**
- 新增「品類」資料層，商品掛品類而非只掛店家
- 擴充假資料，讓每個品類下至少有 2 家不同廠商的商品
- 前端瀏覽流程改為「選品類 → 商品列表（跨廠商）→ 購物車（依廠商分組）→ 結帳 → 結果」
- 新增 `GET /api/shop/categories`，`GET /api/shop/products` 改用 `category_id` 篩選
- 同步更新 `lambda_tools/shared_lambda/shop_catalog.py`（既有慣例：這份 catalog 資料在 backend 與 lambda_tools 各存一份，需保持一致）

**範圍外（不動）：**
- 訂單建立／取消／狀態推進／點數折抵／庫存扣減邏輯（`backend/app/services/shop.py`、`store.py`）完全不變，這些邏輯只認 `sku_id`，跟品類無關
- 運費計算維持「整張訂單只要有實體商品就加一次 60 元」，不依廠商分開計算（已與使用者確認過的簡化）
- Lambda tool `get_shop_products`／`list_shop_stores` 的輸入輸出 schema 不變（現行聊天 Agent 對 `shop_purchase` 是整頁重導向到 `ShopFlowPage`，不透過這兩個 lambda tool 做商城瀏覽，只需同步 catalog 資料內容，不需新增 `category_id` 篩選能力）
- 店家既有的 `category` 欄位（如「超商」「百貨選物」）保留不動，僅單純不再是瀏覽入口

## 資料模型變更

### 新增品類清單

`backend/app/services/shop_catalog.py` 與 `lambda_tools/shared_lambda/shop_catalog.py` 都新增：

```python
SHOP_CATEGORIES: list[dict] = [
    {"id": "cat_beverage", "name": "飲品兌換"},
    {"id": "cat_food", "name": "美食兌換"},
    {"id": "cat_daily", "name": "生活日用品"},
    {"id": "cat_cleaning", "name": "居家清潔用品"},
    {"id": "cat_health", "name": "保健營養品"},
]
```

### 商品新增 `category_id` 欄位，並擴充店家與商品

每個 `SHOP_PRODUCTS` 項目新增 `category_id` 欄位。既有 4 樣商品的 `id`／`store_id`／`skus`（含 `sku_id`）完全不變，只新增這個欄位。新增以下店家與商品：

| 品類 | 店家（`store_id`） | 商品 | 規格 | SKU / 單價 / 點數 |
|---|---|---|---|---|
| 飲品兌換 `cat_beverage` | `store_711_taipei`（既有） | City Café 中杯美式兌換券（既有） | 無 | `sku_coffee_americano_m` NT$45 / 4 點 |
| | `store_family_mart`（新，全家便利商店） | 現萃拿鐵兌換券 | 無 | `sku_familymart_latte_m` NT$50 / 5 點 |
| | `store_louisa`（新，路易莎咖啡） | 冰美式兌換券 | 無 | `sku_louisa_iced_americano` NT$55 / 5 點 |
| 美食兌換 `cat_food` | `store_711_taipei`（既有） | 御飯糰任選兌換券（既有） | 無 | `sku_onigiri_any` NT$35 / 3 點 |
| | `store_family_mart`（新） | 茶葉蛋兌換券（3入） | 無 | `sku_familymart_egg_3` NT$30 / 3 點 |
| | `store_mos_burger`（新，摩斯漢堡） | 薯條兌換券（小） | 無 | `sku_mos_fries_s` NT$40 / 4 點 |
| 生活日用品 `cat_daily` | `store_uni_style`（既有） | 純棉基本款T恤（既有）／不鏽鋼保溫杯（既有） | 顏色/尺寸 | 沿用既有 SKU |
| | `store_daiso`（新，大創生活館） | 多功能收納盒 | 顏色：白／灰 | `sku_daiso_box_white`／`sku_daiso_box_gray` NT$99 / 10 點 |
| 居家清潔用品 `cat_cleaning` | `store_shujie`（新，舒潔生活館） | 多功能清潔噴霧 500ml | 香味：檸檬／茶樹 | `sku_clean_spray_lemon`／`sku_clean_spray_tea` NT$129 / 13 點 |
| | `store_miaojie`（新，妙潔小舖） | 廚房紙巾抽取包（80抽） | 無 | `sku_kitchen_wipes_80` NT$79 / 8 點 |
| 保健營養品 `cat_health` | `store_health_mart`（新，健康藥妝） | 維他命C發泡錠 | 無 | `sku_vitamin_c_effervescent` NT$259 / 26 點 |
| | `store_lohas_health`（新，樂活保健） | 魚油軟膠囊（60粒） | 無 | `sku_fish_oil_60` NT$399 / 40 點 |

`product_type` 全部沿用既有分類方式：兌換券類商品用 `SERIAL_CODE`，實體商品（T恤、保溫杯、收納盒、清潔噴霧、紙巾、保健食品）用 `PHYSICAL`。新店家沿用既有 `ShopStore` 形狀（`id`／`name`／`category`／`image`），`category` 欄位純資料展示用、不影響瀏覽邏輯，8 家新店家的確切值：

```python
{"id": "store_family_mart", "name": "全家便利商店 台北忠孝店", "category": "超商", "image": None},
{"id": "store_louisa", "name": "路易莎咖啡 信義店", "category": "連鎖咖啡", "image": None},
{"id": "store_mos_burger", "name": "摩斯漢堡 台北車站店", "category": "連鎖速食", "image": None},
{"id": "store_daiso", "name": "大創生活館 西門店", "category": "生活雜貨", "image": None},
{"id": "store_shujie", "name": "舒潔生活館", "category": "居家清潔", "image": None},
{"id": "store_miaojie", "name": "妙潔小舖", "category": "居家清潔", "image": None},
{"id": "store_health_mart", "name": "健康藥妝", "category": "藥妝保健", "image": None},
{"id": "store_lohas_health", "name": "樂活保健", "category": "藥妝保健", "image": None},
```

### `shop_catalog.py` 函式新增/調整

```python
def list_categories() -> list[dict]:
    return SHOP_CATEGORIES

def list_products(category_id: str | None = None, store_id: str | None = None) -> list[dict]:
    products = SHOP_PRODUCTS
    if category_id is not None:
        products = [p for p in products if p["category_id"] == category_id]
    if store_id is not None:
        products = [p for p in products if p["store_id"] == store_id]
    return products
```

`list_products` 回傳的每個商品字典，額外附加一個 `store_name` 欄位（由 `get_store(p["store_id"])["name"]` 查得），讓前端不用自己再拉一次店家清單做對應。

## 後端 API 變更（`backend/app/api/shop.py`）

- 新增 `GET /api/shop/categories` → `{"categories": shop_catalog.list_categories()}`
- `GET /api/shop/products` 支援 `category_id`（新）與 `store_id`（既有保留）兩個 query 參數，可各自獨立篩選
- `GET /api/shop/products/{product_id}` 不變

`shop.py`（訂單服務）、`store.py`（庫存/點數儲存）完全不受影響。

## 前端變更

### 型別（`frontend/src/types/shop.ts`）

```ts
export interface ShopCategory {
  id: string;
  name: string;
}
```

`ShopProduct` 新增：
```ts
category_id: string;
store_name: string;
```

### API client（`frontend/src/api/shop.ts`）

```ts
export function listShopCategories(): Promise<{ categories: ShopCategory[] }> {
  return api("/api/shop/categories");
}

export function listShopProducts(categoryId?: string): Promise<{ products: ShopProduct[] }> {
  const query = categoryId ? `?category_id=${encodeURIComponent(categoryId)}` : "";
  return api(`/api/shop/products${query}`);
}
```

`listShopProducts` 的參數語意從「店家 id」改為「品類 id」；`store_id` 篩選仍由後端支援，但前端不再呼叫這個用法。

### `ShopFlowPage.tsx` 流程調整

`Step` 型別的第一步從 `"store"` 改為 `"category"`：

```ts
type Step = "category" | "product" | "cart" | "checkout" | "result";
```

- **Step 1「選品類」**：`useEffect` 改呼叫 `listShopCategories()`；卡片沿用既有 `store` 步驟的按鈕樣式（`rounded-2xl border-2` 卡片），文案改為「請選擇商品類型」，點選後 `setSelectedCategoryId` 並 `goNext()`
- **Step 2「選商品」**：`useEffect` 依 `selectedCategoryId` 呼叫 `listShopProducts(categoryId)`；商品卡片在既有的名稱／價格下方新增一行小字（`text-xs text-slate-400`）顯示 `product.store_name`，讓使用者知道這是哪家廠商賣的。規格選擇／數量／加入購物車的既有邏輯（`matchedSku`／`addToCart` 等）不變
- **Step 3「購物車」**：`CartEntry` 新增 `storeId`／`storeName` 欄位（加入購物車時從 `activeProduct.store_id`／`activeProduct.store_name` 帶入）。渲染時先用 `storeId` 做 `groupBy`，每組上方顯示一個小標題（店家名稱），組內沿用既有的單行商品列樣式；總金額計算（`cartTotal`／`shippingFee`／`orderTotal`）邏輯完全不變，只是 UI 多一層分組標題
- **Step 4/5「結帳／結果」**：不變
- 返回鍵文案微調：Step 2 的「返回選店家」改為「返回選品類」

### 移除項

- `selectedStoreId` state 與相關 `useEffect`（原本依 `selectedStoreId` 觸發 `listShopProducts`）移除，改用 `selectedCategoryId`
- Step 1 不再呼叫 `listShopStores()`；但 Step 3 分組顯示需要店家名稱，這已经透過後端在 `list_products` 回傳附帶的 `store_name` 解決，因此前端完全不需要再拉一次店家清單

## 錯誤處理與邊界情況

- 品類載入失敗：沿用既有 `setToastText("店家清單載入失敗")` 的模式，改文案為「商品類型載入失敗」
- 商品載入失敗：沿用既有「商品清單載入失敗」
- 每個品類目前資料上保證至少 2 家不同廠商，不會出現「品類下沒有商品」的畫面；若未來品類下商品被清空，Step 2 沿用既有「商品清單為空就不顯示卡片」的隱性行為（不特別加空狀態文案，超出本次範圍）

## 測試計畫

### 後端（`backend/tests/test_shop_catalog.py`）

新增：
- `test_list_categories_returns_all_categories`：至少 5 筆，且都有 `id`／`name`
- `test_every_product_has_a_valid_category_id`：所有商品的 `category_id` 都能對應到 `list_categories()` 其中一筆
- `test_each_category_has_at_least_two_distinct_vendors`：每個品類下的商品，其 `store_id` 至少來自 2 家不同店家
- `test_list_products_filtered_by_category`：`list_products(category_id=...)` 只回傳該品類商品
- `test_list_products_includes_store_name`：回傳的商品字典帶有正確的 `store_name`

既有測試（`test_every_product_belongs_to_a_real_store`／`test_sku_ids_are_globally_unique`／`test_physical_products_have_specs_matching_sku_attribute_keys` 等）在資料擴充後應維持全數通過，新增的店家/商品需符合這些既有不變量。

`test_shop_service.py`（訂單建立/取消/點數/庫存）不需改動，既有測試依賴的 `sku_id` 未變動。

### 前端

比照 `DeliveryFlowPage.test.tsx`／`ReservationFlowPage.test.tsx` 既有模式，新增 `ShopFlowPage.test.tsx`，涵蓋：
- 進入頁面先顯示品類清單（mock `listShopCategories`）
- 點選品類後呼叫 `listShopProducts(categoryId)` 並顯示對應商品，商品卡片顯示 `store_name`
- 加入購物車後，購物車畫面依 `storeName` 分組顯示

### 資料同步注意事項

- `backend/scripts/seed_shop_points.py` 遍歷 `shop_catalog.SHOP_PRODUCTS` 幫新 SKU 補庫存，資料擴充後需要重新執行一次（本地與 AWS 皆同一支腳本，見腳本內註解）
- `lambda_tools/shared_lambda/shop_catalog.py` 需與 `backend/app/services/shop_catalog.py` 內容保持一致（既有慣例：這是兩份分開維護的靜態資料檔）

## 已知限制

- 運費不分廠商計算，維持「整單一次 60 元」的既有簡化邏輯（已與使用者確認）
- Lambda tool（`get_shop_products`／`list_shop_stores`）不新增 `category_id` 篩選能力，僅同步資料內容；若未來聊天 Agent 需要用語音/文字瀏覽品類，需另開範圍評估
- 新增的店家/商品皆為 demo 假資料，`image` 欄位維持 `None`
