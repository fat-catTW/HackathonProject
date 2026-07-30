# 商城購物留資表單（M10）Design

## 背景

新增「商城購物」服務：多店家、雙層規格商品（例如顏色 x 尺寸交叉出不同 SKU）、點數折抵、序號型商品（結帳後派發兌換碼）、實體商品多階段狀態推進。跟 `package_shipping`/`food_delivery`/`restaurant_reservation` 一樣，走「後端 embedded 目錄 + 專屬 service 模組 + 專屬 API router + 前端專屬多步驟頁面 + Lambda 對應分支」的既有模式，不走純 schema 通用引擎（因為購物車/規格挑選/點數試算都需要自訂 UI 邏輯，比對現有服務裡屬於「複雜服務」那一掛：`reservation.py`/`delivery.py`）。

本文件是把使用者提供的 M10 規劃（Problem Statement/Requirements/Background/Proposed Solution/15-Task Breakdown）對照現有程式碼驗證過的版本，修正了兩處跟現況不符的地方，其餘規劃內容基本照收。

## 對照現有程式碼驗證過的事實

- **Lambda `submit_service_request` 已經是「依 `service_id` 分派到專屬函式」的結構**：`lambda_tools/submit_service_request/handler.py` 的 `lambda_handler()` 依序檢查 `service["id"] == "food_delivery"` → `_submit_food_delivery()`、`"restaurant_reservation"` → `_submit_restaurant_reservation()`、其餘 → `_submit_generic()`。規劃裡「模仿 `_submit_food_delivery` 的結構加入 `_submit_shop_order` 分支」這個描述跟實際程式碼完全吻合，可以直接照做。
- **`order_type` 沒有代碼衝突**：目前已使用的 `order_type` 值只有 `"02"`（餐廳訂位）、`"06"`（外送）、`"20"`（包裹寄送，這個分支剛建立）。規劃提議的 `"07"`（序號型）／`"10"`（實體商品）目前都沒人用，可以直接採用。
- **`catalog.py` 的 `cms_type` 是另一個獨立欄位、目前沒有任何程式碼讀取它**（`grep` 全專案只在 `catalog.py` 自己的資料定義裡出現），純粹是資料庫位；已用值有 `"10"`（水電修繕）、`"2"`（洗衣機/冷氣）、`"1"`（居家清潔）、`"02"`（餐廳）、`"06"`（外送）、`"20"`（包裹寄送）。商城要用 `cms_type` 的話挑一個沒用過的值即可（例如 `"30"`），跟 `order_type` 的 `"07"`/`"10"` 是兩個不同命名空間，不會互相干擾，但為了不讓人混淆，實作時建議 `cms_type` 也避開 `"10"`（已被水電修繕用掉）。
- **目前完全沒有點數系統**：全專案 `grep "points"` 沒有任何既有程式碼，`store.py` 的 `BaseStore` 也沒有相關方法。這是全新功能，沒有既有模式要相容，但可以直接比照 `get_preferences`/`save_preferences`（`PK=USER#{actor_id}`, `SK=PREFERENCES`，讀取時 merge）這組既有方法的形狀來設計 `get_user_points`/`save_user_points`，一樣走 `SK` 子鍵模式，不需要新的儲存概念。

## 兩個跟原規劃不同的修正（已與你確認）

### 1. SKU 庫存要能真的即時扣減，不能是靜態資料

原規劃 Task 1 把 `stock` 當成 `shop_catalog.py`（寫死在 Python 檔案裡）的商品資料一部分——這在執行期沒辦法真的扣減，因為 Python 原始碼檔案不是可寫的執行期儲存。修正後的設計：

- `shop_catalog.py`／`shared_lambda/catalog.py` 只放**靜態**商品結構（`item_id`、`item_name`、`base_price`、`product_type`、`specs`、`skus` 陣列，`skus` 裡每個 SKU 只放 `sku_id`／`attributes`／`unit_price`／`unit_points`，**不放 `stock`**）。
- 庫存另外存成動態項目：`PK=SHOP_SKU#{sku_id}`, `SK=STOCK`，欄位 `{quantity: int}`。`BaseStore` 新增 `get_sku_stock(sku_id) -> int`、`decrement_sku_stock(sku_id, quantity) -> bool`（庫存不足回 `False`，不寫入）、`restock_sku(sku_id, quantity)`（取消訂單時補回）。
- **併發保護**：`MemoryStore` 已有 `threading.Lock`（`_lock`），`decrement_sku_stock` 要在同一個 lock 範圍內做「讀取現有庫存 → 檢查 → 寫回」，不能拆成兩次 `get_item`/`put_item`（中間會被其他請求插隊）。`DynamoDBStore` 要用 `update_item` 搭配 `ConditionExpression="quantity >= :qty"` + `UpdateExpression="SET quantity = quantity - :qty"`，讓 DynamoDB 自己做原子性的條件式扣減，失敗時捕捉 `ConditionalCheckFailedException` 回傳庫存不足，不要用「先 get 再 put」這種在 DynamoDB 上本來就不安全的寫法。
- 商品目錄的種子資料（demo 用的 2-3 個店家、3-5 個商品）裡各 SKU 的「初始庫存數字」要在 seed script 裡寫進 `SHOP_SKU#{sku_id}/STOCK`，不是寫進 `shop_catalog.py`。

### 2. 點數初始化比照既有 seed script 模式

比照 `backend/scripts/seed_food_delivery_catalog.py`／`seed_restaurant_reservation_catalog.py` 的既有慣例，新增一支 `backend/scripts/seed_shop_points.py`，幫 demo 帳號（`user-vincent`／`user-mei`）寫入初始點數（例如 5000 點）到 `PK=USER#{actor_id}`, `SK=POINTS`。這支腳本在 mock 模式（跑一次寫進 `.local-store.json`）與 DynamoDB 模式（跑一次寫真表）都適用，不用为兩種模式各寫一套初始化邏輯——跟現有兩支 seed script 對 mock/DynamoDB 都通用的做法一致。

## 其餘規劃內容（照使用者原提供的 15-Task Breakdown，未改動實質內容）

- Task 1（修正版）：`backend/app/services/shop_catalog.py`，靜態店家/商品/規格/SKU 目錄（不含 stock，見上方修正）。
- Task 2：`lambda_tools/shared_lambda/catalog.py` 同步商城資料 + `shop_purchase` 服務定義加入 `FALLBACK_SERVICES`。
- Task 3（修正版）：`store.py` 新增點數方法（`get_user_points`/`deduct_user_points`/`refund_user_points`）+ 上方新增的庫存方法 + `seed_shop_points.py`。
- Task 4：`backend/app/services/shop.py`（`create_shop_order`/`get_shop_order`/`cancel_shop_order`/`update_shop_status_from_vendor`），比照 `delivery.py` 結構，庫存扣減走上方修正後的原子操作。
- Task 5：`backend/app/api/shop.py` RESTful router，`main.py` 掛載。
- Task 6–9：四個 Lambda tool（`list_shop_stores`/`get_shop_products`/`get_user_points`/`submit_service_request` 的 `shop_purchase` 分支），照現有 `list_services`/`get_service_schema` handler 的結構與 `tool_schemas/` + `package_lambda_tools.py` 註冊慣例。
- Task 10–13：前端型別、API client、`ShopFlowPage.tsx`（多步驟：店 → 商品/規格 → 購物車 → 結帳/點數折抵 → 結果/追蹤）、路由與首頁卡片註冊（`App.tsx` 專屬路由要放在通用 `/services/:serviceId` 之前，比照 `restaurant_reservation`/`food_delivery` 的既有寫法；`data/services.ts` 該筆 `fields: []`，因為走專屬頁面不走通用表單）。
- Task 14：`lambda_tools/page_knowledge/pages.json` 新增 `service_form_shop_purchase` 頁面條目，沿用這份檔案現有的**英文**慣例（跟 `package_shipping` 那筆的處理方式一致，不要在這裡混入中文，另外那份檔案整體中文化與否是待決定的獨立議題，不在這個功能範圍內）。
- Task 15：`config.py` 新增三個 Lambda function name 設定、`.env.example` 對應說明、確認 `package_lambda_tools.py` 打包得出新 zip。

## 已知限制（沿用 hackathon 時程下的合理簡化，留給你確認是否接受）

- 庫存併發保護做到 DynamoDB 條件式更新／MemoryStore lock 這個程度，不做「預留庫存倒數計時」「购物車鎖庫存」這類更完整的電商庫存機制。
- 點數折抵公式 `final = original + shipping - (used_points * rate)` 沒有處理「折抵後金額為負」的邊界情況，需要在 `create_shop_order` 裡加一個下限檢查（例如折抵上限不超過商品金額）。
- 序號型商品的兌換碼只做隨機產生 + 存進訂單，不做碼與庫存的綁定核銷機制（例如同一組碼被使用兩次的防護），demo 情境下應該足夠。
