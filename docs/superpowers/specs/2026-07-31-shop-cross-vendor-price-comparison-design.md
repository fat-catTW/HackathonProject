# 商城購物：同商品跨店比價 Design

## 背景

商城購物（`ShopFlowPage.tsx` / `service_id: shop_purchase`）先前已完成「品類優先瀏覽」（見 `2026-07-31-shop-mall-category-browsing-design.md`），讓同品類下能看到不同廠商的商品，但那些商品彼此是**不同商品**（例如美式咖啡、拿鐵、冰美式是三種不同飲品），無法呈現「同一件商品，多家店家各自標價，使用者可以比價」的情境。

使用者這次要的是真正的比價：同一款商品（例如「維他命C發泡錠」）同時被 2～3 家店家販售，各自訂不同價格，使用者可以在商城頁面上一眼看到跨店價格，也可以直接跟 AI 管家說「我想比較 OO 的價格」，管家在對話中列出各店價格並附上深連結，直接帶去該商品的比價畫面。

## 目標與範圍

**範圍內：**
- 商品新增 `compare_group_id` 標記「同一商品的不同店家版本」，新增 3 組跨店比價商品（各 3 家店），新增 2 家通路型店家（屈臣氏、家樂福）
- 新增 `GET /api/shop/compare/{group_id}`，回傳同組所有店家的商品與價格（由低到高排序）
- `ShopFlowPage.tsx` Step 2 商品清單：同組商品合併成一張卡片，點擊後顯示「各店比價清單」，選定店家後才進入既有的規格/數量/加入購物車流程
- 支援 `?compare=<group_id>` URL 深連結，頁面掛載時自動定位到指定商品的比價清單
- 新增一次問答型服務 `shop_price_compare`（比照 `health_product_recommendation` 模式），AI 管家偵測到比價意圖時呼叫新 tool `compare_product_prices`，直接在對話中列出各店價格，並附上深連結到商城比價頁的 `redirect_path`
- 同步更新 `lambda_tools/shared_lambda/shop_catalog.py`（既有慣例：這份 catalog 資料在 backend 與 lambda_tools 各存一份，需保持一致）

**範圍外（不動）：**
- 訂單建立／取消／狀態推進／點數折抵／庫存扣減邏輯（`shop.py`、`store.py`）完全不變，這些邏輯只認 `sku_id`，跟比價分組無關
- 運費計算維持「整張訂單只要有實體商品就加一次 60 元」，不因跨店訂購而分開計算（沿用既有簡化）
- `compare_product_prices` 只做本地 mock 實作，**不**接 Lambda／MCP Gateway：比照 `shop_purchase` 本身也未串接這條路徑的既有慣例，`config.py`／`lambda_tools/`／MCP 工具清單都不需要異動
- 沒有比價組的既有商品（咖啡、拿鐵、T恤、紙巾……）完全不受影響，維持單一店家販售

## 資料模型變更

### 新增店家

`backend/app/services/shop_catalog.py` 與 `lambda_tools/shared_lambda/shop_catalog.py` 都新增：

```python
{"id": "store_watsons", "name": "屈臣氏 台北信義店", "category": "藥妝", "image": None},
{"id": "store_carrefour", "name": "家樂福 內湖店", "category": "量販", "image": None},
```

### 商品新增 `compare_group_id` 欄位，並新增比價組商品

每個 `SHOP_PRODUCTS` 項目新增 `compare_group_id: str | None` 欄位（既有商品預設 `None`，不影響既有測試）。新增／標記以下 3 組跨店比價商品：

| 比價組 `compare_group_id` | 品類 | 商品 | 店家 | 單價 | 備註 |
|---|---|---|---|---|---|
| `cmp_vitamin_c` | 保健營養品 `cat_health` | 維他命C發泡錠 | `store_health_mart`（既有商品，補標籤） | NT$259 | 無規格 |
| | | | `store_lohas_health`（新商品項，既有店家） | NT$239 | 無規格 |
| | | | `store_watsons`（新店家＋新商品項） | NT$249 | 無規格 |
| `cmp_clean_spray` | 居家清潔用品 `cat_cleaning` | 多功能清潔噴霧 500ml | `store_shujie`（既有商品，補標籤） | NT$129 | 規格：香味 檸檬/茶樹 |
| | | | `store_miaojie`（新商品項，既有店家） | NT$119 | 規格：香味 檸檬/茶樹 |
| | | | `store_carrefour`（新店家＋新商品項） | NT$109 | 規格：香味 檸檬/茶樹 |
| `cmp_tumbler` | 生活日用品 `cat_daily` | 不鏽鋼保溫杯 500ml | `store_uni_style`（既有商品，補標籤） | NT$590 | 規格：顏色 粉/藍 |
| | | | `store_daiso`（新商品項，既有店家） | NT$490 | 規格：顏色 粉/藍 |
| | | | `store_watsons`（新店家共用商品項） | NT$550 | 規格：顏色 粉/藍 |

同組商品的 `name`／`description`／`product_type`／`specs` 結構需完全一致（同一款商品），只有 `id`／`store_id`／`skus`（各自的 `sku_id`／`unit_price`／`unit_points`）不同。`unit_points` 沿用既有比例（約單價的 10%）。

### `shop_catalog.py` 新增函式

```python
def list_compare_offers(group_id: str) -> list[dict]:
    """回傳同一 compare_group_id 底下所有商品，each 附加 store_name 與
    min_unit_price（該商品所有 SKU 中最低單價），依 min_unit_price 由低到高排序。
    找不到該 group_id 回傳空 list。"""
    offers = [
        {**p, "store_name": (get_store(p["store_id"]) or {}).get("name", ""),
         "min_unit_price": min(sku["unit_price"] for sku in p["skus"])}
        for p in SHOP_PRODUCTS
        if p.get("compare_group_id") == group_id
    ]
    return sorted(offers, key=lambda o: o["min_unit_price"])


def find_compare_group_id_by_query(query: str) -> str | None:
    """用商品名稱做子字串比對（雙向：商品名稱在 query 裡，或 query 在商品名稱裡），
    找第一個有 compare_group_id 的相符商品，回傳其 compare_group_id；
    沒有相符或該商品沒有比價組都回傳 None。"""
    for p in SHOP_PRODUCTS:
        if not p.get("compare_group_id"):
            continue
        if p["name"] in query or query in p["name"]:
            return p["compare_group_id"]
    return None
```

## 後端 API 變更（`backend/app/api/shop.py`）

新增：
```python
@router.get("/api/shop/compare/{group_id}")
def get_shop_compare_group(group_id: str) -> dict:
    offers = shop_catalog.list_compare_offers(group_id)
    if not offers:
        _raise_api_error(404, "COMPARE_GROUP_NOT_FOUND", "找不到這組比價商品")
    return {"group_id": group_id, "category_id": offers[0]["category_id"], "offers": offers}
```

既有的 `GET /api/shop/products`／`GET /api/shop/products/{product_id}` 不變，回傳的商品字典會多一個 `compare_group_id` 欄位（多數商品是 `null`）。

## 前端變更

### 型別（`frontend/src/types/shop.ts`）

`ShopProduct` 新增：
```ts
compare_group_id: string | null;
```

新增：
```ts
export interface ShopCompareOffer extends ShopProduct {
  store_name: string;
  min_unit_price: number;
}

export interface ShopCompareGroup {
  group_id: string;
  category_id: string;
  offers: ShopCompareOffer[];
}
```

### API client（`frontend/src/api/shop.ts`）

```ts
export function getShopCompareGroup(groupId: string): Promise<ShopCompareGroup> {
  return api(`/api/shop/compare/${encodeURIComponent(groupId)}`);
}
```

### `ShopFlowPage.tsx` 流程調整

**Step 2 商品清單分組顯示：**
- 用 `product.compare_group_id ?? product.id` 當 key，把 `products` 分組（`useMemo`）
- 群組只有 1 件商品：卡片顯示方式與行為完全不變（既有邏輯：點擊直接 `setActiveProduct`）
- 群組有多件商品：卡片顯示商品名稱、「NT$${min}~${max}」（取各商品 `skus` 最低價的最小值/最大值）、「共 N 家店販售」；點擊後**不**設定 `activeProduct`，改為 `setComparingGroupId(groupKey)`

**比價清單面板（新增）：**
- 當 `comparingGroupId` 有值時，在原本顯示規格選擇面板的位置（`activeProduct &&` 區塊之前）改渲染比價清單：每家店一行，顯示 `store_name`、`min_unit_price`；價格最低的一行加註「最便宜」徽章（沿用 `badge-success` 樣式）
- 每行有「選這家」按鈕：點擊後 `setActiveProduct(該店的商品)`、`setComparingGroupId(null)`，接續既有規格/數量/加入購物車邏輯（`matchedSku`／`addToCart` 完全不變，因為它們操作的仍是單一 `ShopProduct`）
- 比價清單有一個「返回商品列表」的次要按鈕，只清空 `comparingGroupId`（不切換 `stepIndex`）

**深連結（`?compare=<group_id>`）：**
- 用 `useSearchParams`（react-router-dom）讀取 `compare` 參數
- 掛載時的 `useEffect`（僅執行一次）：若有 `compare` 參數，呼叫 `getShopCompareGroup(groupId)`；成功後 `setSelectedCategoryId(result.category_id)`、`setComparingGroupId(result.group_id)`、`setStepIndex(STEP_ORDER.indexOf("product"))`；失敗則 `setToastText("比價資料載入失敗")`
- 選品類時（Step 1 卡片 `onClick`）與比價清單「返回商品列表」以外的路徑離開 Step 2 時（`goBack` 回 Step 1），額外呼叫 `setComparingGroupId(null)`，避免殘留狀態

### 移除項
無（純新增）。

## AI 管家整合

### `backend/app/services/catalog.py` 新增服務

```python
{
    "id": "shop_price_compare",
    "name": "商品比價",
    "description": "說出想比價的商品名稱，馬上看到各店家價格",
    "service_vendor_id": None,
    "cms_type": None,
    "enabled": True,
    "keywords": ["比價", "比較價格", "哪裡便宜", "哪家便宜", "最便宜", "價格比較"],
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

比照 `health_product_recommendation`，這是一次問答型服務，不進入通用表單收集流程。

### `backend/app/agent/agent.py`

在 `handle_message` 判斷出新服務 schema 後（既有 `health_product_recommendation` / `shop_purchase` 攔截區塊旁），新增：

```python
if service_id == "shop_price_compare":
    reply, redirect_path = _answer_price_compare(text, auth_token)
    state["service_id"] = None
    state["service_name"] = None
    state["service_schema"] = None
    state["collected_fields"] = {}
    state["missing_fields"] = []
    return _reply(state, reply, redirect_path=redirect_path)
```

新增輔助函式：

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

### `backend/app/agent/tools.py`

新增（import `shop_catalog`）：

```python
def _embedded_compare_product_prices(params: dict) -> dict:
    query = str(params.get("query") or "").strip()
    if not query:
        return {"success": False, "error": {"code": "INVALID_QUERY", "message": "query is required."}}
    group_id = shop_catalog.find_compare_group_id_by_query(query)
    if not group_id:
        return {"success": False, "error": {"code": "PRODUCT_NOT_FOUND", "message": f"找不到「{query}」的比價商品"}}
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

註冊進 `_EMBEDDED_TOOLS["compare_product_prices"]`。**不**加進 `_invoke_lambda`／`_gateway_tool_name` 的對照表，也**不**新增對應的 lambda handler：與 `shop_purchase` 一致，這條路徑只在 `settings.use_mock` 為真時可用；`agent_tool_mode` 為 `lambda`／`mcp`／`dynamodb` 時呼叫 `compare_product_prices` 會回傳 `TOOL_INVOCATION_FAILED`，導致 `_answer_price_compare` 走「找不到比價資訊」的回覆分支（不會壞掉，只是暫時沒有比價功能，等同已知限制）。

## 錯誤處理與邊界情況

- `GET /api/shop/compare/{group_id}` 傳入不存在的 `group_id` → 404 `COMPARE_GROUP_NOT_FOUND`；前端深連結載入失敗時 `setToastText("比價資料載入失敗")`，維持在 Step 1（不強制跳轉）
- 聊天比價找不到符合的商品名稱 → 管家純文字回覆道歉語句，`redirect_path` 為 `None`，不夾帶按鈕
- 使用者輸入的商品名稱同時是多組比價商品的子字串（例如都含「保溫杯」）→ 用 `SHOP_PRODUCTS` 原始順序取第一個相符者，行為是確定性但非語意匹配；demo 資料只有 1 組保溫杯，暫不構成問題
- 比價清單內任一店家商品缺貨（`decrement_sku_stock` 失敗）→ 沿用既有 `OUT_OF_STOCK` 錯誤流程，不受本次改動影響

## 測試計畫

### 後端

`backend/tests/test_shop_catalog.py` 新增：
- `test_list_compare_offers_sorted_by_price_ascending`：`cmp_vitamin_c` 回傳 3 筆，`min_unit_price` 由低到高
- `test_list_compare_offers_unknown_group_returns_empty`
- `test_find_compare_group_id_by_query_matches_partial_name`：查詢「維他命C」能找到 `cmp_vitamin_c`
- `test_find_compare_group_id_by_query_no_match_returns_none`
- 既有不變量測試（`test_each_category_has_at_least_two_distinct_vendors`、`test_sku_ids_are_globally_unique`、`test_physical_products_have_specs_matching_sku_attribute_keys` 等）在新增商品後應維持全數通過

`backend/tests/test_shop_api.py` 新增：
- `GET /api/shop/compare/cmp_vitamin_c` 回傳 200，3 筆 offers 且排序正確
- `GET /api/shop/compare/does_not_exist` 回傳 404

`backend/tests/test_agent_*`（比照既有 health_recommendation 的 agent 測試檔案模式）新增：
- 使用者說「我想比較維他命C的價格」→ reply 包含各店價格與最便宜標記，`redirect_path == "/services/shop_purchase?compare=cmp_vitamin_c"`
- 查無比價商品時 reply 為道歉語句，`redirect_path is None`

### 前端

`ShopFlowPage.test.tsx` 新增：
- 同 `compare_group_id` 的多筆商品在 Step 2 合併成一張卡片，顯示價格區間與店家數
- 點擊該卡片顯示比價清單，最低價一列有「最便宜」標記
- 點擊「選這家」後進入既有規格選擇/加入購物車流程
- 帶 `?compare=cmp_vitamin_c` 進入頁面時，自動定位到 Step 2 並展開該組比價清單

### 資料同步注意事項

- `backend/scripts/seed_shop_points.py` 需重新執行，為新增的 SKU 補庫存
- `lambda_tools/shared_lambda/shop_catalog.py` 需與 `backend/app/services/shop_catalog.py` 內容保持一致（既有慣例）

## 已知限制

- `compare_product_prices` 只有本地 mock 實作，未串接 Lambda／MCP Gateway；`USE_MOCK=false` 環境下比價聊天功能會暫時退化為「找不到比價資訊」
- 只有 3 個品類各有 1 組跨店比價商品（保健營養品、居家清潔用品、生活日用品），其餘既有商品維持單一店家販售，不做比價
- 比價的商品名稱比對是簡單子字串匹配，非語意搜尋；同名或高度相似的多組比價商品可能命中錯的組別（demo 資料範圍內不會發生）
- 運費、跨店訂單金額計算沿用既有「整單一次 60 元」簡化邏輯，不因為同時跟多家比價店下單而改變
