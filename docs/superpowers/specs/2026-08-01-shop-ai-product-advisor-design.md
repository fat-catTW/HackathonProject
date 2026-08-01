# 商城購物：AI 選購顧問（跨品牌比較 + 評分評價）Design

## 背景

商城購物（`ShopFlowPage.tsx` / `service_id: shop_purchase`）目前是「選品類 → 商品列表（跨廠商，同商品可能有多店比價卡片）→ 購物車 → 結帳」的瀏覽式流程，且商城裡完全沒有評分／評價資料，商品也沒有涵蓋 3C 電子這種「同一種需求、不同品牌各有取捨」的品類。

使用者想要的是類似 Amazon Rufus 的體驗：跟 AI 管家說出使用情境或想要的商品（例如「我想要錄 podcast 用的麥克風」），AI 理解情境後，從商城裡跨品牌／跨店家比較，參考評分與消費者評價，直接給出推薦與理由，而不是要使用者自己一個一個品類點進去慢慢挑。

這需要三件事同時到位：(1) 商城要有評分／評價這種資料本來就沒有的東西，(2) 商城要有一個「同需求、多品牌可比較」的品類當作 demo 情境（麥克風），(3) 要有一個 AI 推薦引擎把「情境語意」轉成「商品清單 + 理由」。

**與既有「跨店比價」功能的關係**：商城已經有 `compare_group_id`／`GET /api/shop/compare/{group_id}`／一次問答服務 `shop_price_compare`（同一款商品、不同店家各自標價，使用者可直接問「哪裡最便宜」）。這次的 AI 選購顧問是不同情境：使用者說的是**需求或使用情境**（不是明確商品名稱），要跨的是**不同品牌的不同商品**（不是同一款商品的跨店標價），兩者資料模型與服務都各自獨立、不衝突，新商品可以同時擁有 `tags`（給選購顧問用）而不需要 `compare_group_id`。

## 目標與範圍

**範圍內：**
- 新增品類 `cat_electronics`「3C 影音周邊」，含 7 個新品牌旗艦店與 7 樣商品（5 支不同定位的麥克風 + 視訊鏡頭 + 錄音介面），刻意做出價格與規格差異，讓「跨品牌比較」有意義。
- 新增 `backend/app/services/shop_reviews.py`：**全站所有商品**（現有 19 樣 + 新增 7 樣，共 26 樣）都補上 3–6 則評價（星等、作者、內容、日期、是否為實際購買），並提供依評價算出的平均分／則數。
- `shop_catalog.list_products()`／`get_product()` 回傳內容新增 `rating_avg`、`rating_count`。
- 新增 `GET /api/shop/products/{product_id}/reviews`。
- 新增 AI 推薦引擎：`backend/app/services/shop_recommendation.py`（呼叫 `app/agent/llm.py` 新函式 `recommend_shop_products()`，走既有 Bedrock `converse` client；LLM 不可用時退回關鍵字/標籤＋評分排序的 fallback），推薦範圍是**整個商城**（不侷限電子品類），因為這是通用選購顧問，麥克風只是本次的 demo 情境。
- 新增一次問答型服務 `shop_product_advisor`（比照 `health_product_recommendation`／`shop_price_compare` 現有模式），管家在對話中列出推薦商品（品牌／店家／價格／評分／理由），並附深連結帶去商城對應品類。
- `ShopFlowPage.tsx`：商品卡片顯示評分、可依評分排序（純前端排序）、可展開查看評價、支援 `?category_id=` 深連結。
- 同步更新 `lambda_tools/shared_lambda/shop_catalog.py` 的品類/店家/商品資料（既有慣例），**不**新增對應 Lambda handler。

**範圍外（不動）：**
- 訂單建立／取消／狀態推進／點數折抵／庫存扣減邏輯（`shop.py`、`store.py`）完全不變。
- 既有的跨店比價功能（`compare_group_id`／`shop_price_compare`／`ShopFlowPage.tsx` 的比價卡片與比價清單 UI）完全不動，本次新增內容與其共存。
- 不做即時爬蟲抓外部電商（PChome／momo／露天）評價——評價維持這個專案一貫的靜態假資料模式。
- 不新增 Lambda handler／MCP 工具給 `recommend_shop_products_by_need`（跟既有 `shop_purchase`／`shop_price_compare` 一樣，只在 `AGENT_TOOL_MODE=embedded` 可用）。

## 資料模型變更

### 新增店家（`backend/app/services/shop_catalog.py` 與 `lambda_tools/shared_lambda/shop_catalog.py` 都要加）

```python
{"id": "store_fifine_official", "name": "FIFINE 官方旗艦店", "category": "3C影音", "image": None},
{"id": "store_blue_mic_tw", "name": "Blue 麥克風台灣旗艦店", "category": "3C影音", "image": None},
{"id": "store_rode_tw", "name": "Rode 台灣官方旗艦店", "category": "3C影音", "image": None},
{"id": "store_hyperx_tw", "name": "HyperX 官方旗艦店", "category": "3C影音", "image": None},
{"id": "store_audio_technica_tw", "name": "Audio-Technica 台灣總代理", "category": "3C影音", "image": None},
{"id": "store_logitech_tw", "name": "羅技官方旗艦店", "category": "3C影音", "image": None},
{"id": "store_pro_audio_tw", "name": "音響數位樂器行", "category": "3C影音", "image": None},
```

### 新增品類

```python
{"id": "cat_electronics", "name": "3C 影音周邊"},
```

### 新增商品

商品新增一個可選欄位 `tags: list[str]`（既有商品不補這個欄位也沒關係，`fallback_recommend` 讀取時用 `product.get("tags", [])`；不影響既有的 `compare_group_id` 欄位，兩者互相獨立，新商品一律不帶 `compare_group_id`）。

| `id` | 店家 | 商品名稱 | 單價 | 定位 | `tags` |
|---|---|---|---|---|---|
| `prod_mic_fifine_k669b` | `store_fifine_official` | FIFINE K669B USB 電容式麥克風 | NT$990 | 入門/預算 | 麥克風、USB麥克風、入門、podcast、直播、預算有限 |
| `prod_mic_blue_yeti_x` | `store_blue_mic_tw` | Blue Yeti X USB 電容式麥克風 | NT$4,590 | 經典/高音質 | 麥克風、USB麥克風、podcast、直播、電容式、多指向模式、高音質 |
| `prod_mic_rode_nt_usb_mini` | `store_rode_tw` | Rode NT-USB Mini 電容式麥克風 | NT$2,690 | 輕便/乾淨收音 | 麥克風、USB麥克風、podcast、輕便、磁吸防震架、乾淨收音 |
| `prod_mic_hyperx_quadcast_s` | `store_hyperx_tw` | HyperX QuadCast S USB 麥克風 | NT$5,980 | 電競/直播 | 麥克風、USB麥克風、直播、電競、RGB、podcast、防噴罩 |
| `prod_mic_atr2100x_usb` | `store_audio_technica_tw` | Audio-Technica ATR2100x-USB 動圈式麥克風 | NT$3,280 | 雙人訪談/抗噪 | 麥克風、動圈式、USB、XLR、雙訪談、podcast、抗噪 |
| `prod_webcam_logitech_c920` | `store_logitech_tw` | 羅技 C920 HD Pro 視訊鏡頭 | NT$2,190 | 視訊周邊 | 視訊鏡頭、webcam、直播、視訊會議、1080p |
| `prod_audio_interface_scarlett_solo` | `store_pro_audio_tw` | Focusrite Scarlett Solo (Gen 4) 錄音介面 | NT$3,480 | 進階升級 | 錄音介面、audio interface、XLR、podcast、專業錄音 |

全部 `category_id: "cat_electronics"`、`product_type: "PHYSICAL"`、`specs: []`、單一 SKU（`sku_id` 用 `sku_` 前綴＋商品關鍵字，`unit_points` 約單價 10%）。這 7 家店滿足既有測試不變量 `test_each_category_has_at_least_two_distinct_vendors`。

### 新增 `backend/app/services/shop_reviews.py`

```python
SHOP_REVIEWS: dict[str, list[dict]] = {
    "prod_mic_fifine_k669b": [
        {
            "review_id": "rev_fifine_k669b_01",
            "author": "阿凱",
            "rating": 5,
            "comment": "第一次錄 podcast 就用這支，收音乾淨、價格親民，新手很夠用。",
            "created_at": "2026-05-12",
            "verified_purchase": True,
        },
        # ... 每個商品 3–6 則，評分刻意有高有低（不是全部 5 分），
        # 內容具體提到規格/使用情境（收音品質、CP值、雙人訪談、直播穩定度等），
        # 讓 AI fallback 關鍵字比對與人類閱讀時都有實際參考價值。
    ],
    # ... 全站每個 product_id 都要有一筆，包含同款商品在不同店家的個別
    # product_id（例如 prod_vitamin_c / prod_vitamin_c_lohas / prod_vitamin_c_watsons
    # 是同一款商品的三個不同店家版本，各自要有自己的評價，因為評價反映的是
    # 「跟這家店買」的體驗，不是商品本身）。
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

**涵蓋範圍**：`shop_catalog.SHOP_PRODUCTS` 目前的全部 19 樣商品（T恤、保溫杯×3店、各種兌換券、收納盒、清潔噴霧×3店、紙巾、維他命C×3店、魚油）＋新增的 7 樣電子商品，共 26 樣，每樣都要有評價資料，不能有商品是 `rating_count == 0`。

### `shop_catalog.py` 調整

現有 `list_products()` 已經會合併 `store_name` 與 `compare_group_id`；`get_product()` 目前是直接回傳原始 dict（不合併任何欄位）。這次在兩者都加上評分合併：

```python
from . import shop_reviews

def list_products(*, category_id=None, store_id=None) -> list[dict]:
    ...
    return [
        {
            **p,
            "store_name": (get_store(p["store_id"]) or {}).get("name", ""),
            "compare_group_id": p.get("compare_group_id"),
            **shop_reviews.get_rating_summary(p["id"]),
        }
        for p in products
    ]


def get_product(product_id: str) -> dict | None:
    product = next((p for p in SHOP_PRODUCTS if p["id"] == product_id), None)
    if product is None:
        return None
    return {**product, **shop_reviews.get_rating_summary(product_id)}
```

## AI 推薦引擎

### `backend/app/agent/llm.py` 新增

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

放在既有 `choose_service`／`plan_turn` 附近，沿用同一個 `_converse_json`（`bedrock-runtime` `converse`，`settings.bedrock_model_id`），呼叫失敗或 client 不可用時回傳 `None`，由呼叫端 fallback；也沿用 `_set_debug_info` 既有的除錯資訊機制（`_converse_json` 內部已經處理，不需要額外加）。**這支呼叫用的是專案裡已經在用的同一個 Bedrock client／設定，不需要新的 AWS 資源或權限設定**——只要現有 `.env` 的 AWS 金鑰能讓既有的服務判斷／表單流程正常運作，這支新函式就能直接運作。

### 新增 `backend/app/services/shop_recommendation.py`

```python
from ..agent import llm


def fallback_recommend(query: str, products: list[dict]) -> list[dict]:
    def match_score(product: dict) -> int:
        tags = product.get("tags", [])
        name_hit = 1 if product["name"] in query or any(
            keyword in product["name"] for keyword in tags
        ) else 0
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

`products` 傳入 `shop_catalog.list_products()`（**全商城**，不侷限 `cat_electronics`），因為這是通用選購顧問。

### `backend/app/agent/tools.py`

```python
from ..services import shop_catalog, shop_recommendation  # shop_catalog 已是既有 import

def _embedded_recommend_shop_products_by_need(params: dict) -> dict:
    query = str(params.get("query") or "").strip()
    if not query:
        return {"success": False, "error": {"code": "INVALID_QUERY", "message": "query is required."}}
    result = shop_recommendation.recommend(query, shop_catalog.list_products())
    return {"success": True, **result}
```

註冊進 `_EMBEDDED_TOOLS["recommend_shop_products_by_need"]`（現有字典裡已經有 `compare_product_prices` 這種只在 embedded 模式可用的先例）。不加進 `_invoke_lambda`／`_gateway_tool_name` 對照表。

## 後端 API 變更（`backend/app/api/shop.py`）

新增（放在既有 `get_shop_compare_group` 之後）：
```python
@router.get("/api/shop/products/{product_id}/reviews")
def get_shop_product_reviews(product_id: str) -> dict:
    product = shop_catalog.get_product(product_id)
    if not product:
        _raise_api_error(404, "PRODUCT_NOT_FOUND", "找不到這項商品")
    return {"reviews": shop_reviews.list_reviews(product_id)}
```

需要新增 `from ..services import shop_reviews` import。既有 `GET /api/shop/products`／`GET /api/shop/products/{id}`／`GET /api/shop/compare/{group_id}` 路由不變，回傳內容新增 `rating_avg`／`rating_count` 欄位。

## AI 管家整合

### `backend/app/services/catalog.py` 新增服務

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

關鍵字**刻意不放「比較」／「比價」**，因為那是既有 `shop_price_compare` 的關鍵字（`["比價", "比較", "比較價格", "哪裡最便宜", "哪家最便宜", "最便宜", "價格比較"]`），避免兩份關鍵字表放同一個高頻詞造成閱讀上的混淆（`_message_matches_service` 本身允許多個服務關鍵字有重疊而不影響正確性，但關鍵字表分工清楚比較好維護）。比照 `health_product_recommendation`，這是一次問答型服務，不進入通用表單收集流程。關鍵字清單刻意涵蓋常見「選購/評價」語彙及本次 demo 主打商品名詞，因為這是通用型選購顧問、無法窮舉所有商品名稱——實際辨識主要靠 `llm.choose_service`（看得懂完整語意），關鍵字表只是 `_message_matches_service` 的防呆檢查層，這點與 `health_product_recommendation`／`shop_price_compare` 現有設計一致（見「已知限制」）。

### `backend/app/agent/agent.py`

在 `handle_message` 判斷出新服務 schema 後，比照既有 `health_product_recommendation`／`shop_purchase`／`shop_price_compare` 攔截區塊旁新增：

```python
if service_id == "shop_product_advisor":
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

`redirect_requires_confirmation` 沿用 `shop_price_compare` 現有的做法（有 `redirect_path` 才要求確認）。新增輔助函式（放在 `_answer_price_compare` 附近）：

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

深連結用**第一個推薦結果自己的 `category_id`**（不寫死 `cat_electronics`），因為推薦引擎本來就是全商城範圍。

## 前端變更

### 型別（`frontend/src/types/shop.ts`）

```ts
export interface ShopProduct {
  // ...既有欄位（含既有的 compare_group_id）
  rating_avg: number;
  rating_count: number;
}

export interface ShopReview {
  review_id: string;
  author: string;
  rating: number;
  comment: string;
  created_at: string;
  verified_purchase: boolean;
}
```

### API client（`frontend/src/api/shop.ts`）

```ts
export function getShopProductReviews(productId: string): Promise<{ reviews: ShopReview[] }> {
  return api(`/api/shop/products/${encodeURIComponent(productId)}/reviews`);
}
```

### 新元件 `frontend/src/components/RatingStars.tsx`

純展示元件，輸入 `rating`（0–5）與可選 `count`，輸出星等圖示＋數字（例："★★★★☆ 4.6（128）"）。商品卡片、比價清單、評價清單都會共用，避免重複 render 邏輯。

### `ShopFlowPage.tsx` 調整

現有頁面已經有 `useSearchParams`（給既有的 `?compare=` 深連結用）、`productGroups`（用 `compare_group_id ?? id` 分組，同商品多店家會合併成一張「共 N 家店販售」卡片）這些既有結構，這次直接沿用：

- **深連結**：新增讀取 `category_id` 參數（與既有 `compareParam` 各自獨立的 `useEffect`）；有值時 `setSelectedCategoryId(categoryIdParam)` 並 `setStepIndex(STEP_ORDER.indexOf("product"))`，跳過選品類畫面。不用額外呼叫 API 驗證品類是否存在——如果帶了不存在的 `category_id`，`listShopProducts` 自然會回傳空清單，Step 2 就是空的商品列表，不用特別處理（維持既有「品類下沒商品」的隱性行為，跟既有品類瀏覽功能一致）。
- **Step 2 商品卡片**：`productGroups.map()` 的兩個分支（多店家比價卡片／單店家商品卡片）都在價格下方加一行 `<RatingStars rating={...} count={...} />`——多店家卡片顯示該組內最高評分的那筆（`Math.max(...group.offers.map(o => o.rating_avg))`），單店家卡片直接顯示 `product.rating_avg`／`product.rating_count`。比價清單（`comparingOffers.map`）每一行也順便加上小字評分，方便使用者比價時一併參考評分。
- **Step 2 排序**：新增「依評分排序」切換按鈕（`sortByRating` boolean state）；渲染時用 `sortByRating ? [...productGroups].sort((a, b) => Math.max(...b.offers.map(o => o.rating_avg)) - Math.max(...a.offers.map(o => o.rating_avg))) : productGroups` 取代直接用 `productGroups`，純前端排序、不影響 `productGroups` 這個 `useMemo` 本身。
- **規格面板新增「查看評價」**：`activeProduct` 存在時，面板下方加一個可展開區塊（`showReviews` boolean state，選新商品時重置為 `false`）；展開時才呼叫 `getShopProductReviews(activeProduct.id)`（`useEffect` 依 `activeProduct?.id` 與 `showReviews` 觸發，避免每個商品都預先載入），列出評價卡片：`RatingStars`、作者、日期、（已購買）標籤、內容文字。

### 移除項
無（純新增）。

## 錯誤處理與邊界情況

- `GET /api/shop/products/{product_id}/reviews` 傳入不存在的 `product_id` → 404 `PRODUCT_NOT_FOUND`（與既有 `get_shop_product` 一致）；前端載入失敗時該區塊顯示「評價載入失敗」文字，不擋住其餘操作。
- 聊天問到選購顧問但商城裡真的沒有符合的商品（理論上不會發生，因為 fallback 會回傳評分最高的商品作為保底）→ 目前設計下 `recommendations` 一定非空（只要商城至少有一樣商品），故「找不到符合商品」的分支只在 `tools.call` 本身失敗（`success=False`）時觸發。
- Bedrock 呼叫逾時／額度不足／模型未開通 → `_converse_json` 已有 `except Exception` 包住並回傳 `None`，自動退回 `fallback_recommend`，使用者會看到「這次是用關鍵字與評分挑選的，僅供參考」提示，不會整個功能掛掉。
- 使用者輸入的情境完全查無關鍵字比對（fallback 模式）→ `fallback_recommend` 的 `matched` 為空，退回全商城評分最高的 5 樣商品當保底，不會回傳空清單。
- 深連結帶入不存在或空的 `category_id` → 不特別驗證，直接進入 Step 2 顯示空清單，使用者可以用「返回選品類」重新選擇，不是本次要特別處理的路徑。

## 測試計畫

### 後端

`backend/tests/test_shop_catalog.py` 新增／需維持全數通過：
- 既有不變量（`test_each_category_has_at_least_two_distinct_vendors`、`test_sku_ids_are_globally_unique`、`test_physical_products_have_specs_matching_sku_attribute_keys`、既有的比價相關測試等）在新增電子商品後仍需全數通過
- `test_list_products_includes_rating_fields`：`list_products()` 每筆都有 `rating_avg`（float）與 `rating_count`（int ≥ 1）
- `test_get_product_includes_rating_fields`

新增 `backend/tests/test_shop_reviews.py`：
- `test_every_product_has_at_least_one_review`：`shop_catalog.list_products()` 的每個 `id` 在 `SHOP_REVIEWS` 都能找到至少一筆
- `test_get_rating_summary_computes_average_and_count`
- `test_get_rating_summary_unknown_product_returns_zero`

新增 `backend/tests/test_shop_recommendation.py`：
- `test_fallback_recommend_matches_by_tag_keyword`：query 含「麥克風」「podcast」，回傳結果都跟麥克風相關
- `test_fallback_recommend_falls_back_to_top_rated_when_no_match`：完全不相關的 query 仍回傳 5 筆、依評分排序
- `test_recommend_uses_llm_when_available_and_falls_back_when_not`（mock `llm.recommend_shop_products` 回傳 `None` / 有值兩種情境）

`backend/tests/test_shop_api.py` 新增：
- `GET /api/shop/products/prod_mic_blue_yeti_x/reviews` 回傳 200 與非空 `reviews`
- `GET /api/shop/products/does_not_exist/reviews` 回傳 404

Agent 對話測試（比照既有 `test_health_recommendation.py`／既有 `shop_price_compare` agent 測試模式）新增：
- 使用者說「我想要錄 podcast 用的麥克風，可以推薦一下嗎」→ 正確路由到 `shop_product_advisor`（不是 `health_product_recommendation`／`shop_purchase`／`shop_price_compare`），reply 包含店家名稱與評分，`redirect_path` 指向 `/services/shop_purchase?category_id=cat_electronics`
- `tools.call` 回傳失敗時，reply 是道歉訊息、`redirect_path is None`

### 前端

`ShopFlowPage.test.tsx` 新增：
- 商品卡片（含多店家比價卡片）顯示評分
- 點擊「依評分排序」後商品卡片順序依評分由高到低
- 展開「查看評價」後呼叫 `getShopProductReviews` 並顯示評價內容
- 帶 `?category_id=cat_electronics` 進入頁面時跳過 Step 1，直接顯示該品類商品

### 資料同步注意事項

- `backend/scripts/seed_shop_points.py` 需重新執行，為新增的 7 個 SKU 補庫存
- `lambda_tools/shared_lambda/shop_catalog.py` 需與 `backend/app/services/shop_catalog.py` 內容保持一致（既有慣例）；`shop_reviews.py` 不需要同步到 `lambda_tools/`（既有慣例：只有走 Lambda 路徑的資料才需要鏡射，這次推薦功能不走 Lambda）

## Bedrock 部署備忘（給還不熟 Bedrock 的操作指引）

專案的 `.env` 已經有 `USE_MOCK=false`、AWS 金鑰、`BEDROCK_MODEL_ID=apac.amazon.nova-pro-v1:0`，`app/agent/llm.py` 的 `_converse_json` 早就在用這組設定跑既有的服務判斷／表單流程——**這代表 Bedrock 存取理論上已經是通的，本次新功能只是多一支用同一個 client 打的呼叫，不需要新的 AWS 資源**。實作時會先跑一個小驗證（直接呼叫一次 `recommend_shop_products` 確認有正常回應）；如果驗證失敗，常見原因與排除方式：

1. **模型尚未開通**：AWS Console → Bedrock →左側「Model access」→ 找到 Amazon Nova Pro（或 `.env` 裡設定的其他模型）→ 申請/啟用存取，通常幾分鐘內生效。要在 `.env` 的 `AWS_REGION`（目前是 `ap-northeast-1`）那個 region 開通。
2. **IAM 權限不足**：目前用的 AWS 使用者/角色要有 `bedrock:InvokeModel` 與 `bedrock:Converse`（`_converse_json` 用的是 `converse` API）的權限，最簡單是先掛 AWS 官方的 `AmazonBedrockFullAccess` 測試，能動之後再收斂成最小權限的自訂 policy。
3. **Region 不支援該模型**：不是每個模型在每個 region 都能用，若 `apac.amazon.nova-pro-v1:0` 在你的 region 不可用，需要換一個該 region 有支援的模型 ID（Bedrock Console 的「Model access」頁面看得到各 region 可用清單）。

## 已知限制

- 評分／評價是手寫的靜態假資料，不是真的去爬外部電商——這是這個 hackathon 專案一貫的 mock 資料模式，不是本次範圍要解決的事。
- `shop_product_advisor` 的服務辨識關鍵字表無法窮舉所有商品名稱／使用情境措辭，靠 LLM `choose_service` 理解語意為主，關鍵字只是防呆層；如果使用者的措辭完全不含清單裡任何字詞、且 `choose_service` 的 LLM 呼叫本身也失敗（Bedrock 不可用時 `choose_service` 回 `None`），該次訊息可能不會被路由到這個服務——這跟現有 `health_product_recommendation`／`shop_price_compare` 的已知限制一致，不是本次新增的弱點。
- `recommend_shop_products_by_need` 只有 `embedded` 模式可用，`AGENT_TOOL_MODE=lambda`／`mcp`／`dynamodb` 時會導致這個工具呼叫失敗，退化為「查詢失敗」的道歉回覆。
- 「依評分排序」只在前端排序當頁已載入的商品，不影響後端 `GET /api/shop/products` 的預設排序（沿用資料宣告順序）。
