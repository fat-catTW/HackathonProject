# Implementation Plan: App 視覺大改版（Guarrent 科技風 + Light/Dark 雙模式）

## Overview

實作順序為「基礎設施 → 共用元件 → 頁面套用（Tier A→D）→ 驗證與回歸」。先建立色彩模式系統與設計 Token，讓所有後續元件與頁面都有可依賴的變數來源；再重構共用元件（含移除舊主題機制）；最後依 Tier 分級套用到 14 個頁面。實作語言為 TypeScript / React（沿用專案既有技術棧），測試以 Vitest 執行，property-based 測試新增 `fast-check`。

所有路徑相對於 repo 根目錄 `HackathonProject-main/`。`frontend/src/App.tsx` 的 Route 定義全程不得變更。

## Tasks

- [x] 1. 建立色彩模式系統（Color_Mode_System）
  - [x] 1.1 新增 `frontend/src/hooks/useColorMode.ts`
    - 定義 `ColorMode = "light" | "dark"` 與 `UseColorModeResult`（`mode` / `setMode` / `toggle`）
    - 以模組層級狀態 + `Set` 監聽器 + `useSyncExternalStore` 實作，比照 `frontend/src/hooks/useAccessibilityMode.ts` 既有寫法
    - 初始化：讀取 localStorage key `"ai-butler-color-mode"`，值為 `"light"`/`"dark"` 時採用，否則採用固定預設 `"light"`；不讀取 `prefers-color-scheme`
    - 讀寫 localStorage 一律包在 try/catch 中靜默失敗
    - 模式變更時執行 `document.documentElement.setAttribute("data-color-mode", mode)` 並寫回 localStorage
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 5.2_
  - [x] 1.2 於 `frontend/src/main.tsx` 匯入並初始化 `useColorMode` 的模組副作用
    - 確保首次繪製前 `data-color-mode` 已套用，避免閃屏
    - _Requirements: 1.5, 2.2_
  - [x] 1.3 新增 `fast-check` 至 `frontend/package.json` 的 devDependencies（固定版本號）
    - _Requirements: 20.1_
  - [x] 1.4 撰寫 `frontend/src/hooks/useColorMode.test.ts` 單元測試
    - 涵蓋預設值為 `"light"`、`setMode` 生效、`toggle` 切換、localStorage 讀寫拋錯時的 fallback、`window.matchMedia` 不存在時仍可初始化
    - 比照 `useAccessibilityMode.test.ts` 的檔案結構與風格
    - _Requirements: 2.5, 2.7, 20.3_
  - [x] 1.5 撰寫 Property 1 的 property-based 測試
    - **Property 1: 模式切換往返一致（Round trip）**
    - **Validates: Requirements 1.1, 1.2, 1.3, 1.4**
    - 迭代次數 ≥ 100；同時斷言 `mode` 恆屬合法集合、`data-color-mode` 與 `mode` 一致
  - [x] 1.6 撰寫 Property 2 的 property-based 測試
    - **Property 2: 持久化寫入與讀取往返一致**
    - **Validates: Requirements 2.1, 2.2**
    - 迭代次數 ≥ 100；以重新初始化 hook 模擬頁面重新載入
  - [x] 1.7 撰寫 Property 3 的 property-based 測試
    - **Property 3: 無效或缺失儲存值一律回退為預設模式**
    - **Validates: Requirements 2.3, 2.4, 2.5, 2.6**
    - 迭代次數 ≥ 100；生成器涵蓋任意字串、空字串、key 不存在、localStorage 拋錯、任意 `prefers-color-scheme` 回傳值；斷言結果恆為 `"light"` 且不拋出例外
  - [x] 1.8 撰寫 Property 4 的 property-based 測試
    - **Property 4: 模式切換不影響其他既有偏好設定**
    - **Validates: Requirements 5.1, 5.2, 5.4**
    - 迭代次數 ≥ 100；生成任意無障礙開關狀態 × 任意色彩模式操作序列，雙向斷言兩組 localStorage key 與 `data-*` 屬性互不改動

- [x] 2. 重寫設計 Token 系統（`frontend/src/index.css`）
  - [x] 2.1 以 `html[data-color-mode="light"]` / `html[data-color-mode="dark"]` 取代既有 `html[data-theme="..."]` 區塊
    - 依 design.md〈Data Models〉逐項寫入品牌類、表面類、文字類、狀態類、Mascot 類變數
    - 兩區塊變數名稱集合必須完全相同，並各自宣告 `color-scheme: light` / `color-scheme: dark`
    - _Requirements: 6.1, 6.2, 6.3, 6.4_
  - [x] 2.2 新增 `.glass-panel` 工具類別與 Dark 模式加強樣式
    - Light：`backdrop-filter: blur(16px)`；Dark：`blur(20px)` + 內側高光 `inset` 陰影
    - 加入 `@supports not (backdrop-filter: blur(1px))` fallback，退回不透明 `--color-surface`
    - _Requirements: 9.4, 9.5, 9.6_
  - [x] 2.3 新增 `.bg-wordmark-texture` 與漸層工具類別
    - 大字紋理：`pointer-events: none`、置於內容層之下、Light `opacity: 0.05` / Dark `opacity: 0.08`
    - 漸層：`--color-primary` → `--color-primary-accent`，Dark 模式降飽和並疊深色 vignette
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_
  - [x] 2.4 新增字型 Token 與網路字型載入
    - `--font-display`（Space Grotesk → Noto Sans TC）、`--font-mono`（JetBrains Mono）、`--font-body` 維持不變
    - 於 `frontend/index.html` 以 `<link>` 載入並設定 `font-display: swap`
    - _Requirements: 7.1, 7.4, 7.5_
  - [x] 2.5 校準 `frontend/tailwind.config.js` 既有色彩別名對應至新變數名稱
    - 僅調整別名指向，不改寫 config 整體結構
    - _Requirements: 6.5_
  - [x] 2.6 撰寫設計 Token 靜態斷言測試
    - 解析 `index.css`，斷言兩個色彩模式區塊的變數名稱集合相等、必要變數皆存在、關鍵色值（`#2563EB`、`#60A5FA`、`#3B82F6`、`#7DD3FC`、`#0B1220`）正確、兩區塊皆含 `color-scheme`、`.glass-panel` 含 `@supports` fallback、字型變數存在
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 7.1, 9.5, 9.6, 10.1, 10.2, 10.3_
  - [x] 2.7 撰寫對比度計算測試
    - 對 design.md 列出的 Light/Dark token 配對逐一計算對比比值，斷言內文 ≥ 4.5:1、大字/圖示 ≥ 3:1
    - _Requirements: 16.1, 16.2_

- [x] 3. Checkpoint - 確認基礎設施可運作
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. 共用元件重構與新增
  - [x] 4.1 修改 `frontend/src/components/Mascot.tsx` 的 props 介面
    - 移除 `bodyColor` / `highlightColor`，新增 `tone?: "brand" | "inverted" | "muted"`（預設 `"brand"`）
    - `brand` 吃 `--color-mascot-body` / `--color-mascot-accent`；`inverted` 為白色系；`muted` 為低對比灰藍
    - 維持既有 SVG 造型結構與 `size` / `className` 行為
    - _Requirements: 3.4, 8.1, 8.2, 8.3, 8.4, 8.5, 8.6_
  - [x] 4.2 撰寫 `Mascot.test.tsx`
    - 三個 `tone` 各渲染一次斷言色彩輸出、省略 `tone` 時等同 `"brand"`、`size`/`className` 生效
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 20.4_
  - [x] 4.3 新增 `frontend/src/components/AppearanceMenu.tsx`（取代 `ThemeMenu.tsx`）
    - 以 Light/Dark 兩個選項取代 5 色塊；以 `aria-pressed` 或 `aria-checked` 標示目前模式
    - 保留既有無障礙模式開關與「重看導覽」入口的行為
    - 每個可互動元素觸控區 ≥ 44×44px，選項含可讀文字標籤
    - _Requirements: 3.3, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_
  - [x] 4.4 撰寫 `AppearanceMenu.test.tsx`
    - 斷言兩選項存在且無色塊選色 UI、點擊後 `data-color-mode` 變更、選取狀態標示正確、無障礙開關與重看導覽行為不變
    - _Requirements: 3.3, 4.1, 4.2, 4.3, 4.4, 20.4_
  - [x] 4.5 新增 `frontend/src/components/GlassPanel.tsx`
    - 封裝 `.glass-panel` 樣式，支援 `className` 與 `children` 透傳
    - _Requirements: 9.4, 9.5, 9.6_
  - [x] 4.6 新增 `frontend/src/components/PhoneMockup.tsx`
    - 純 CSS 手機外框（notch + 立體陰影），`children` 承載內容，不使用 `iframe`、不依賴外部圖片
    - _Requirements: 9.1, 9.7_
  - [x] 4.7 新增 `frontend/src/components/FloatingBadge.tsx`
    - 支援 `variant: "icon" | "avatar"`；`icon` 型接 `ServiceIcon` / `Mascot`
    - `avatar` 型未提供圖片來源時，以 `Mascot` 或姓名縮寫圓形色塊 fallback，不出現破圖
    - _Requirements: 9.2, 9.3, 9.7, 18.5_
  - [x] 4.8 撰寫 `GlassPanel` / `PhoneMockup` / `FloatingBadge` 渲染測試
    - 斷言 `GlassPanel` 套用 `glass-panel` class、`PhoneMockup` 查無 `iframe`、`FloatingBadge` 兩種 variant 與 avatar fallback 行為
    - _Requirements: 9.1, 9.2, 9.3, 9.4_
  - [x] 4.9 移除舊主題機制並更新所有引用端
    - 刪除 `frontend/src/hooks/useTheme.ts` 與 `frontend/src/components/ThemeMenu.tsx`
    - 將 `HomePage.tsx`、`LandingPage.tsx`、`OnboardingModal.tsx`、`LoginPage.tsx` 中的 `Mascot` 呼叫改為 `tone` 或省略；`ThemeMenu` 引用改為 `AppearanceMenu`
    - 確認 `tsc` 與 `vite build` 無未解析引用
    - _Requirements: 3.1, 3.2, 3.5, 8.7_

- [x] 5. 既有共用元件視覺套用
  - [x] 5.1 更新狀態呈現元件至新語意色 Token
    - `StatusBadge.tsx`：維持膠囊形與「顏色＋文字」雙重表達，soft 背景改用新狀態色變數
    - _Requirements: 6.6, 16.5, 16.6_
  - [x] 5.2 更新覆蓋層類元件
    - `ConfirmModal.tsx`、`Toast.tsx`、`OnboardingModal.tsx`、`SupportPanel.tsx`、`SupportLauncher.tsx` 改用 `--color-surface` / `--color-border` / `--color-foreground`
    - _Requirements: 6.6, 16.7_
  - [x] 5.3 更新清單與資料型元件（維持不透明實色，不套玻璃擬態或漸層）
    - `RequestCard.tsx`、`RestaurantCard.tsx`、`RestaurantCardList.tsx`、`ServiceIcon.tsx`、`ChatMessage.tsx`
    - _Requirements: 6.6, 15.2, 15.3_
  - [x] 5.4 更新表單控件類元件
    - `FieldPanel.tsx`、`PeopleCounter.tsx`、`PremiumToggle.tsx`、`ReservationDatePicker.tsx`、`TimeSlotSelector.tsx`、`ReservationContactForm.tsx`、`VoiceButton.tsx` 改用新 Token，維持既有觸控區與驗證行為
    - _Requirements: 6.6, 16.4, 17.4_
  - [x] 5.5 更新摘要型元件
    - `ReservationSummaryCard.tsx` 改用 `GlassPanel` 或漸層強調，維持既有欄位標籤與字級規範
    - _Requirements: 13.6, 15.1_
  - [x] 5.6 更新受影響的既有元件測試
    - 修正因 class / Token 變更而失敗的既有測試斷言，保持測試涵蓋的行為語意不變
    - 結果：無測試因 class / Token 變更而失敗（258 passed）。唯一失敗的 `FieldPanel.test.tsx`
      為測試檔既有的中文編碼 mojibake 問題（斷言字串與元件實際輸出的亂碼形式不一致），
      與本次視覺改版無關，依使用者指示留待 Task 12.4 處理
    - _Requirements: 17.4, 17.5_

- [x] 6. Checkpoint - 確認共用元件在兩模式下皆正確渲染
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Tier A：`frontend/src/pages/LandingPage.tsx` 視覺重寫
  - [x] 7.1 重寫 Hero 區
    - 疊入 `.bg-wordmark-texture` 背景層 + 科技藍漸層背景
    - 置中 `PhoneMockup`，內部渲染服務卡或對話氣泡的縮小示意（不使用照片）
    - 環繞放置 3–5 個 `FloatingBadge`（含 2 個 icon 型、1–2 個 avatar 型），確保不遮擋可互動元素
    - _Requirements: 11.1, 11.3, 9.7, 10.1, 10.4_
  - [x] 7.2 移除主題色塊預覽區塊
    - 刪除 `THEMES` 色塊預覽 UI 與 `previewId` / `previewTheme` 相關 state 與 handler
    - 結果：該區塊已於 Task 4.9 移除 `useTheme` 時一併清除，本任務僅作驗證並由
      `LandingPage.test.tsx` 加上迴歸斷言（查無色塊預覽元素）
    - _Requirements: 3.1, 3.3, 11.2_
  - [x] 7.3 更新 Highlights 與 Services 區塊配色與字型
    - 內容與結構不變，僅改用新色彩 Token 與 `--font-display`
    - _Requirements: 7.2, 11.4_
  - [x] 7.4 接入 Hero 頭像素材或 placeholder
    - 預留 2 張 1:1 頭像（年長使用者、到府服務人員）的引用位置，兩模式共用同一份圖片、不套濾鏡
    - 素材未到齊時以 `Mascot` / 姓名縮寫色塊 placeholder 呈現
    - 若採用可選的居家場景底圖，於 Dark 模式額外疊 `rgba(11,18,32,0.55)` 遮罩
    - _Requirements: 18.1, 18.2, 18.3, 18.4, 18.5_
  - [x] 7.5 撰寫 `LandingPage` 渲染測試
    - 斷言 `PhoneMockup` 存在、`FloatingBadge` 數量在 3–5 之間、查無主題色塊預覽元素、Highlights/Services 區塊仍存在
    - _Requirements: 11.1, 11.2, 11.4_

- [x] 8. Tier B：登入頁視覺套用
  - [x] 8.1 更新 `frontend/src/pages/LoginPage.tsx`
    - 背景使用淡化版 `.bg-wordmark-texture`（不透明度低於 LandingPage）；表單卡維持不透明 `--color-surface`，不套玻璃擬態
    - `Mascot` 改為 `tone="brand"`；版面結構與欄位順序不變
    - _Requirements: 12.1, 12.2, 12.3, 12.4_
  - [x] 8.2 更新 `frontend/src/pages/VendorLoginPage.tsx`
    - 同 8.1 處理原則，保留 Demo 帳號說明卡結構
    - _Requirements: 12.1, 12.2, 12.3_
  - [x] 8.3 撰寫兩個登入頁的渲染測試
    - 檔案：`frontend/src/pages/LoginPage.visual.test.tsx`（涵蓋兩個登入頁）
    - 斷言表單卡未套 `glass-panel` class、`Mascot` tone 正確、既有欄位仍存在
    - _Requirements: 12.2, 12.3, 12.4_

- [x] 9. Tier C：操作型頁面視覺套用
  - [x] 9.1 更新 `frontend/src/components/ButlerPanel.tsx` 與 `ButlerLauncher.tsx`
    - Overlay 模式：以 `GlassPanel` 取代手寫 `bg-white/[0.06] backdrop-blur-xl` 內嵌樣式，DOM 結構不變
    - 非 overlay 模式：`--color-canvas` 底色 + 不透明卡片
    - `ButlerLauncher` 浮動行動按鈕改用漸層 Token
    - _Requirements: 9.4, 13.7, 13.8, 15.1_
  - [x] 9.2 更新 `frontend/src/pages/HomePage.tsx`
    - 頂部 hero 改用新漸層 Token 並以 `GlassPanel` 包裝文字區塊；服務卡 grid 維持不透明卡片
    - 以 `AppearanceMenu` 取代原主題選單入口
    - _Requirements: 13.1, 13.2, 13.3, 15.1, 15.2_
  - [x] 9.3 更新 `frontend/src/pages/ServiceFormPage.tsx`
    - 頂部服務資訊卡改用新漸層 Token；表單欄位群組維持不透明實色卡片
    - _Requirements: 13.4, 15.1, 15.2_
  - [x] 9.4 更新資料密集頁面
    - `RequestDetailPage.tsx`、`MyServicesPage.tsx`、`HealthRecommendationPage.tsx` 以不透明卡片呈現，狀態標示改用新語意狀態色
    - 狀態標示皆沿用已於 5.1 改版的共用 `StatusBadge`，自動取得新語意狀態色
    - _Requirements: 13.1, 13.5, 15.2_
  - [x] 9.5 更新多步驟流程頁
    - `ReservationFlowPage.tsx`、`DeliveryFlowPage.tsx`、`ShopFlowPage.tsx`：各步驟卡維持不透明實色，僅最終確認摘要卡套 `GlassPanel` 或漸層強調
    - `ReservationFlowPage` 經共用 `ReservationSummaryCard`（5.5 已套 `GlassPanel`）取得強調；
      `DeliveryFlowPage` / `ShopFlowPage` 的「應付金額」摘要卡改為 `GlassPanel`
    - _Requirements: 13.1, 13.6, 15.1, 15.2_
  - [x] 9.6 驗證 `frontend/src/pages/NewRequestPage.tsx` 無需自身視覺改動
    - 確認其外觀變化全數來自 `ButlerPanel`，該檔案不含硬編碼色碼
    - 結果：該檔案僅 6 行，只轉發 props 給 `ButlerPanel`，無任何 className 或色值
    - _Requirements: 6.6, 13.9_
  - [x] 9.7 更新 Tier C 頁面的既有測試並補充 class 斷言
    - 結果：`ServiceFormPage.test.tsx`、`ReservationFlowPage.test.tsx`、`DeliveryFlowPage.test.tsx`
      在改版後全數通過，無需修正斷言；玻璃擬態邊界的斷言統一集中於 Task 12.1 的靜態掃描測試
    - 修正 `ServiceFormPage.test.tsx`、`ReservationFlowPage.test.tsx`、`DeliveryFlowPage.test.tsx` 因樣式變更失敗的斷言；補充「摘要卡套 GlassPanel、步驟卡未套」的斷言
    - _Requirements: 13.6, 15.1, 15.2, 17.4, 17.5_

- [x] 10. Tier D：廠商後台視覺套用
  - [x] 10.1 更新 `frontend/src/pages/VendorRequestsPage.tsx`
    - Tab 列與案件列表維持不透明實色卡片；僅頂部標題區使用極淡漸層色帶
    - Dark 模式下列表項目分隔線需可辨識；既有欄位與操作按鈕位置不變
    - _Requirements: 14.1, 14.3, 14.4, 15.2_
  - [x] 10.2 更新 `frontend/src/pages/VendorRequestDetailPage.tsx`
    - 沿用 `RequestDetailPage` 的不透明卡片原則，狀態標示改用新語意狀態色
    - _Requirements: 14.2, 14.3, 14.4_
  - [x] 10.3 撰寫 Tier D 頁面渲染測試
    - 斷言列表未套 `glass-panel` class、欄位與操作按鈕順序不變
    - 檔案：`frontend/src/pages/VendorPages.visual.test.tsx`
    - _Requirements: 14.1, 14.4_

- [x] 11. Checkpoint - 確認 14 個頁面皆已套用新 Token
  - Ensure all tests pass, ask the user if questions arise.

- [x] 12. 特效邊界與範圍限制驗證
  - [x] 12.1 撰寫視覺特效邊界靜態掃描測試
    - 斷言 `RequestCard.tsx`、`VendorRequestsPage.tsx` 列表區塊、`ServiceFormPage.tsx` 表單欄位群組不含 `glass-panel` 或 `backdrop-filter`
    - 檔案：`frontend/src/styles/visualBoundaries.test.ts`（掃描前先移除註解，避免說明文字造成假性失敗）
    - _Requirements: 15.1, 15.2, 15.3_
  - [x] 12.2 撰寫硬編碼色碼掃描測試
    - 掃描 `frontend/src/components` 與 `frontend/src/pages`，斷言無硬編碼 hex 色碼（允許清單除外）
    - 允許清單僅 `Mascot.tsx`（inverted/muted tone 與造型固定色，Requirement 8.7）
    - _Requirements: 6.6_
  - [x] 12.3 驗證改版範圍限制
    - 確認 `frontend/src/App.tsx` 的 Route 定義未變更、`frontend/src/api` 與 `backend/` 未被修改、頁面檔案清單無增減
    - 已另以 `git status` 確認 `App.tsx`、`frontend/src/api`、`backend/` 三者皆無變更
    - _Requirements: 17.1, 17.2, 17.3_
  - [x] 12.4 執行完整前端測試套件回歸
    - 確認既有測試全數通過；僅涉及已移除主題機制的測試允許被更新
    - 結果：`tsc -b` 無錯誤，`vitest run` 35 個測試檔 / 333 項測試全數通過
    - `FieldPanel.test.tsx` 的既有失敗經查非本次改版造成：該斷言寫成「服務地址」，但
      `utils/fieldLabels.ts` 的 `FIELD_LABELS.address` 為「地址」，屬長期存在的文案不一致。
      已將斷言改為引用 `fieldLabel()` 對齊單一來源，未改動使用者可見文案
    - _Requirements: 17.4, 17.5, 20.2, 20.3, 20.4_

- [x] 13. 新增品牌敘述文件
  - [x] 13.1 建立 `docs/brand-guidelines-visual-redesign.md`
    - 記錄本次科技感品牌敘述、Light/Dark 雙模式色彩 Token 表、字型配對、視覺特效使用邊界
    - 標註與 `PRODUCT.md` / `DESIGN.md` 既有敘述的衝突之處，並說明本次方向為使用者明確選擇
    - 不修改 `PRODUCT.md` 與 `DESIGN.md` 本文
    - _Requirements: 19.1, 19.2, 19.3_

- [ ] 14. 最終 checkpoint - 交付前驗證
  - Ensure all tests pass, ask the user if questions arise.
  - 請使用者依 design.md〈Testing Strategy〉的 Pre-Delivery Checklist，對 14 個頁面 × Light/Dark 兩模式逐項人工視覺檢查（對比度、玻璃卡片文字清晰度、漂浮元素不遮擋、觸控區 ≥44px、reduced-motion 下可讀性、模式即時切換、兩組偏好互不干擾）
  - _Requirements: 16.3, 16.4, 16.6, 16.7, 15.5, 20.5_

## Notes

- 標記 `*` 的子任務為測試相關，可視 MVP 進度略過，但 1.5–1.8（四個 property test）建議保留，因它們是唯一涵蓋色彩模式邏輯正確性的自動化驗證
- 每個 property test 需設定至少 100 次隨機迭代（`fast-check` 的 `numRuns`）
- Task 1 與 Task 2 為所有後續工作的前置依賴，必須先完成
- Task 4.9（移除舊主題機制）需在 4.1–4.7 完成後執行，避免中途出現未解析引用
- Tier A→D 的頁面套用（Task 7–10）彼此獨立，可平行進行
- 視覺呈現類驗收標準（顏色、字型、間距、對比度、觸控區）多屬人工/瀏覽器驗證範圍，已集中於 Task 14 的交付前檢查
