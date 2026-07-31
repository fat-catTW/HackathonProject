# Requirements Document

## Introduction

本文件定義「App 視覺大改版（Guarrent 科技風 + Light/Dark 雙模式）」的需求規格，內容全部由已通過確認的 `design.md` 反推而來。此改版是**純前端視覺層置換**：14 個既有頁面與所有共用元件全部套用新視覺系統，同時將原本「機器人管家可自訂 5 色系換膚」機制替換為「單一品牌主色（Trust Blue）+ Light/Dark 雙色彩模式」，概念類似 VS Code 的 Light/Dark Theme 切換。

改版範圍**不包含**路由結構、資訊架構、資料流、表單驗證邏輯或任何後端／API 變更。所有需求聚焦於色彩模式系統的邏輯行為、設計 Token 系統、新增共用視覺元件，以及 14 個頁面分四級（Tier A–D）的視覺套用規則。

其中僅色彩模式系統背後的邏輯行為（切換、持久化、預設值解析、與既有偏好互不干擾）屬於可自動化通用驗證的部分，對應 `design.md`〈Correctness Properties〉的 4 個 property；其餘視覺呈現類驗收標準以範例式測試與人工視覺檢查驗證。

## Glossary

- **Color_Mode_System**: 色彩模式系統，即 `frontend/src/hooks/useColorMode.ts` 及其模組層級狀態，負責解析、套用、持久化 Light/Dark 模式
- **Color_Mode**: 色彩模式值，僅有 `"light"` 與 `"dark"` 兩個合法值
- **Appearance_Menu**: 外觀設定選單，即 `frontend/src/components/AppearanceMenu.tsx`，取代既有 `ThemeMenu.tsx`
- **Accessibility_Mode_System**: 既有無障礙模式系統，即 `frontend/src/hooks/useAccessibilityMode.ts`，使用 localStorage 鍵 `"ai-butler-a11y"` 與 DOM 屬性 `data-a11y`
- **Design_Token_System**: 設計 Token 系統，即 `frontend/src/index.css` 中的 CSS 變數定義與工具類別，搭配 `tailwind.config.js` 既有別名
- **Mascot_Component**: 機器人管家吉祥物元件，即 `frontend/src/components/Mascot.tsx`
- **Glass_Panel**: 玻璃擬態容器元件，即 `frontend/src/components/GlassPanel.tsx`
- **Phone_Mockup**: 手機外框元件，即 `frontend/src/components/PhoneMockup.tsx`
- **Floating_Badge**: 漂浮徽章元件，即 `frontend/src/components/FloatingBadge.tsx`
- **Landing_Page**: 行銷首頁，即 `frontend/src/pages/LandingPage.tsx`（Tier A）
- **Login_Pages**: 登入頁集合，即 `LoginPage.tsx` 與 `VendorLoginPage.tsx`（Tier B）
- **Operational_Pages**: 操作型頁面集合，即 `HomePage.tsx`、`NewRequestPage.tsx`、`ServiceFormPage.tsx`、`RequestDetailPage.tsx`、`MyServicesPage.tsx`、`ReservationFlowPage.tsx`、`DeliveryFlowPage.tsx`、`ShopFlowPage.tsx`、`HealthRecommendationPage.tsx`、`ButlerPanel.tsx`、`ButlerLauncher.tsx`（Tier C）
- **Flow_Pages**: 多步驟流程頁集合，即 `ReservationFlowPage.tsx`、`DeliveryFlowPage.tsx`、`ShopFlowPage.tsx`
- **Vendor_Pages**: 廠商後台頁面集合，即 `VendorRequestsPage.tsx` 與 `VendorRequestDetailPage.tsx`（Tier D）
- **Frontend_App**: 前端應用整體，即 `frontend/` 下的 React 應用
- **Frontend_Test_Suite**: 前端測試套件，以 Vitest 執行，含單元測試與 property-based 測試
- **Color_Mode_Storage_Key**: 色彩模式偏好在 localStorage 中的鍵名，固定為 `"ai-butler-color-mode"`
- **Color_Mode_DOM_Attribute**: 色彩模式套用至 DOM 的屬性，固定為 `document.documentElement` 上的 `data-color-mode`
- **Trust_Blue**: 本次改版的單一品牌主色，Light 模式為 `#2563EB`、漸層終點 `#60A5FA`；Dark 模式為 `#3B82F6`、漸層終點 `#7DD3FC`

## Requirements

### Requirement 1: 色彩模式切換行為

**User Story:** 身為使用者，我希望能在淺色與深色外觀之間切換，以便在不同光線環境下都能舒適地使用 App。

#### Acceptance Criteria

1. THE Color_Mode_System SHALL 提供 `mode`、`setMode(mode)` 與 `toggle()` 三項介面，且 `mode` 在任何時刻的值必為 `"light"` 或 `"dark"` 其中之一
2. WHEN 呼叫 `setMode` 並傳入合法 Color_Mode 值, THE Color_Mode_System SHALL 將生效模式更新為該值
3. WHEN 呼叫 `toggle`, THE Color_Mode_System SHALL 將生效模式切換為另一個 Color_Mode 值（`"light"` 切換為 `"dark"`，`"dark"` 切換為 `"light"`）
4. WHEN 生效模式變更, THE Color_Mode_System SHALL 將 Color_Mode_DOM_Attribute 設為與生效模式完全相同的字串值
5. WHEN 生效模式變更, THE Color_Mode_System SHALL 使新色彩即時生效，使用者無需重新整理頁面
6. THE Color_Mode_System SHALL 以模組層級狀態搭配 `useSyncExternalStore` 與監聽器集合實作，使所有訂閱該狀態的元件於模式變更時同步重新渲染，與 Accessibility_Mode_System 既有實作慣例一致

### Requirement 2: 色彩模式偏好持久化與預設值解析

**User Story:** 身為使用者，我希望我選擇的外觀模式在下次開啟 App 時仍然保留，且即使儲存資料損壞或瀏覽器不允許儲存，App 也不會出錯。

#### Acceptance Criteria

1. WHEN 生效模式變更, THE Color_Mode_System SHALL 將該 Color_Mode 值寫入 Color_Mode_Storage_Key
2. WHEN Frontend_App 啟動且 Color_Mode_Storage_Key 存有合法 Color_Mode 值, THE Color_Mode_System SHALL 以該值作為初始生效模式
3. IF Color_Mode_Storage_Key 不存在, THEN THE Color_Mode_System SHALL 以 `"light"` 作為初始生效模式
4. IF Color_Mode_Storage_Key 的值不是 `"light"` 也不是 `"dark"`（含空字串與任意其他字串）, THEN THE Color_Mode_System SHALL 以 `"light"` 作為初始生效模式
5. IF localStorage 讀取或寫入時拋出例外（無痕模式、瀏覽器封鎖、配額已滿）, THEN THE Color_Mode_System SHALL 捕捉該例外、繼續以記憶體內狀態運作、不向使用者顯示錯誤訊息，且不中斷 Frontend_App 初始化
6. THE Color_Mode_System SHALL 以固定值 `"light"` 作為系統預設模式，不以 `prefers-color-scheme` 作為初始模式的判斷依據
7. IF 瀏覽器不支援 `matchMedia`, THEN THE Color_Mode_System SHALL 正常完成初始化並套用預設模式

### Requirement 3: 移除多色主題換膚機制

**User Story:** 身為產品負責人，我希望移除舊的 5 色換膚機制，以便全站色彩收斂為單一品牌主色，降低視覺不一致與維護成本。

#### Acceptance Criteria

1. THE Color_Mode_System SHALL 取代既有 `useTheme.ts` 的多色主題機制，Frontend_App 不再提供主題色清單，也不再提供以主題 id 設定色系的 API
2. THE Design_Token_System SHALL 以 Trust_Blue 作為唯一品牌主色，使用者不可自行指定任意品牌色
3. THE Appearance_Menu SHALL 不提供色塊選色 UI
4. THE Mascot_Component SHALL 不接受任意色字串作為外觀色彩輸入
5. WHERE 既有程式碼引用已移除的介面（`useTheme`、`THEMES`、`setTheme`、`bodyColor`、`highlightColor`）, THE Frontend_App SHALL 全數改為引用新介面，使建置與型別檢查不出現未解析引用

### Requirement 4: 外觀設定選單

**User Story:** 身為使用者，我希望能在一個明確的入口切換外觀模式，以便隨時調整而不需要尋找設定。

#### Acceptance Criteria

1. THE Appearance_Menu SHALL 提供「淺色」與「深色」兩個 Color_Mode 選項
2. WHEN 使用者於 Appearance_Menu 選擇某一模式, THE Appearance_Menu SHALL 呼叫 Color_Mode_System 將生效模式設為該值
3. THE Appearance_Menu SHALL 以 `aria-pressed` 或 `aria-checked` 標示目前生效模式的選項為選取狀態，其餘選項為未選取狀態
4. THE Appearance_Menu SHALL 保留既有的無障礙模式開關與「重看導覽」入口，兩者行為與改版前一致
5. THE Appearance_Menu SHALL 使所有可互動元素的觸控區域不小於 44×44px
6. THE Appearance_Menu SHALL 同時以文字標籤與視覺狀態表達目前選取的模式，不單靠顏色區分

### Requirement 5: 色彩模式與既有偏好設定互不干擾

**User Story:** 身為已開啟無障礙模式的使用者，我希望切換外觀模式時我的字級放大設定不會被重置，以便我不需要重複設定。

#### Acceptance Criteria

1. WHEN 生效色彩模式變更, THE Color_Mode_System SHALL 保持 Accessibility_Mode_System 的偏好值不變
2. THE Color_Mode_System SHALL 僅讀寫 Color_Mode_Storage_Key 與 Color_Mode_DOM_Attribute，不讀取也不寫入 Accessibility_Mode_System 所使用的 localStorage 鍵 `"ai-butler-a11y"` 與 DOM 屬性 `data-a11y`
3. WHILE 無障礙模式為啟用狀態, THE Frontend_App SHALL 於 Light 與 Dark 兩模式下皆維持既有字級放大行為
4. WHEN 無障礙模式偏好變更, THE Frontend_App SHALL 保持生效色彩模式不變

### Requirement 6: 雙模式設計 Token 系統

**User Story:** 身為開發者，我希望所有顏色都來自語意化 Token，以便 Light/Dark 兩模式能以同一份元件程式碼同時支援。

#### Acceptance Criteria

1. THE Design_Token_System SHALL 於 `html[data-color-mode="light"]` 與 `html[data-color-mode="dark"]` 兩個選擇器下各定義一組完整的語意色彩變數，且兩組變數名稱集合完全相同
2. THE Design_Token_System SHALL 定義品牌類（`--color-primary`、`--color-primary-hover`、`--color-primary-accent`、`--color-on-primary`、`--color-primary-soft`）、表面類（`--color-background`、`--color-canvas`、`--color-surface`、`--color-surface-glass`、`--color-border`、`--color-glass-border`）、文字類（`--color-foreground`、`--color-muted-foreground`）、狀態類（`success`／`warning`／`danger`／`info` 及其對應 `-soft` 版本）與 Mascot 類（`--color-mascot-body`、`--color-mascot-accent`）變數
3. THE Design_Token_System SHALL 採用 design.md〈Data Models〉所列的具體色值，包含 Light 模式主色 `#2563EB`、漸層終點 `#60A5FA`、背景 `#F8FAFC`，與 Dark 模式主色 `#3B82F6`、漸層終點 `#7DD3FC`、背景 `#0B1220`
4. THE Design_Token_System SHALL 於各模式區塊宣告對應的 `color-scheme` 值（Light 為 `light`、Dark 為 `dark`），使瀏覽器原生控件配色與頁面一致
5. THE Frontend_App SHALL 透過 `tailwind.config.js` 既有別名對應至上述 CSS 變數，維持既有 className 慣例，不整體改寫 Tailwind 設定結構
6. WHERE 元件需要顏色, THE Frontend_App SHALL 引用語意色彩變數，不在元件中寫入硬編碼色碼

### Requirement 7: 字型 Token

**User Story:** 身為使用者，我希望介面的英數標題有科技感，同時中文內容依然清楚易讀，以便在視覺升級的同時不損失可讀性。

#### Acceptance Criteria

1. THE Design_Token_System SHALL 定義 `--font-display`（以 Space Grotesk 起首、Noto Sans TC 等 CJK 字族接續）、`--font-body`（以 Noto Sans TC 起首，維持改版前設定）與 `--font-mono`（以 JetBrains Mono 起首）
2. THE Frontend_App SHALL 以 `--font-display` 呈現大標題與行銷型英數字排版
3. THE Frontend_App SHALL 以 `--font-mono` 呈現案件編號與時間戳等資料型文字
4. THE Frontend_App SHALL 以 `font-display: swap` 載入新增的網路字型，使字型載入不阻擋首屏文字顯示
5. IF 新增網路字型載入失敗, THEN THE Frontend_App SHALL 以 Noto Sans TC 或系統 CJK 字族正常顯示所有中文內容

### Requirement 8: Mascot 受控色彩介面

**User Story:** 身為產品負責人，我希望吉祥物色彩由設計系統統一控制，以便它在任何背景與模式下都保持品牌一致與足夠對比。

#### Acceptance Criteria

1. THE Mascot_Component SHALL 接受 `tone` 屬性，其合法值限於 `"brand"`、`"inverted"`、`"muted"`
2. WHERE `tone` 未指定, THE Mascot_Component SHALL 採用 `"brand"` 作為預設值
3. WHEN `tone` 為 `"brand"`, THE Mascot_Component SHALL 以 `--color-mascot-body` 與 `--color-mascot-accent` 上色
4. WHEN `tone` 為 `"inverted"`, THE Mascot_Component SHALL 以白色系上色，供深色漸層卡片上的裝飾用途使用
5. WHEN `tone` 為 `"muted"`, THE Mascot_Component SHALL 以低對比灰藍色系上色，供背景裝飾用途使用
6. THE Mascot_Component SHALL 維持既有 SVG 造型結構與 `size`、`className` 屬性行為不變
7. THE Frontend_App SHALL 將所有 Mascot_Component 呼叫端（Appearance_Menu、`HomePage.tsx`、`LandingPage.tsx`、`OnboardingModal.tsx`、`LoginPage.tsx`）改為使用 `tone` 屬性或省略該屬性

### Requirement 9: 新增共用視覺元件

**User Story:** 身為開發者，我希望手機外框、漂浮徽章與玻璃擬態容器都是可重用元件，以便多處套用時樣式一致且易於維護。

#### Acceptance Criteria

1. THE Phone_Mockup SHALL 以純 CSS 呈現手機外框（含頂部 notch 與立體陰影），以 `children` 承載內容，且不使用 `iframe`、不依賴外部圖片素材
2. THE Floating_Badge SHALL 支援 `variant` 屬性，其合法值為 `"icon"` 與 `"avatar"`
3. IF `variant` 為 `"avatar"` 且未提供頭像圖片來源, THEN THE Floating_Badge SHALL 以 Mascot_Component 或姓名縮寫圓形色塊作為替代顯示，不出現破圖或空白區塊
4. THE Glass_Panel SHALL 封裝玻璃擬態樣式（半透明背景、背景模糊、細邊框），並取代 `ButlerPanel.tsx` 內既有手寫的內嵌玻璃樣式
5. IF 瀏覽器不支援 `backdrop-filter`, THEN THE Glass_Panel SHALL 退回使用不透明的 `--color-surface` 純色背景，使面板內文字仍可讀
6. WHILE Dark 模式生效, THE Glass_Panel SHALL 套用較高的模糊強度與內側高光邊框，使其與底層背景形成可辨識的層次
7. THE Floating_Badge 與 Phone_Mockup SHALL 不遮擋任何可互動元素的觸控區域

### Requirement 10: 背景紋理與漸層工具類別

**User Story:** 身為使用者，我希望行銷頁面有現代科技質感的背景層次，同時前景文字依然清楚，以便我能專注在內容上。

#### Acceptance Criteria

1. THE Design_Token_System SHALL 提供 `.bg-wordmark-texture` 工具類別，以純 CSS 產生旋轉的大字背景紋理，不依賴圖片素材
2. THE `.bg-wordmark-texture` SHALL 設為不可互動（`pointer-events: none`）且位於內容層之下
3. THE `.bg-wordmark-texture` SHALL 於 Light 模式使用約 0.05 的不透明度、於 Dark 模式使用約 0.08 的不透明度，兩者皆低於可辨識文字的門檻
4. THE Design_Token_System SHALL 提供由 `--color-primary` 至 `--color-primary-accent` 的漸層樣式，供 Hero、摘要卡與主要行動按鈕使用
5. WHILE Dark 模式生效, THE Frontend_App SHALL 降低漸層飽和度並疊加深色 vignette，使漸層在深色頁面中不過度刺眼

### Requirement 11: 行銷首頁視覺套用（Tier A）

**User Story:** 身為初次造訪的訪客，我希望首頁一眼呈現產品的現代科技質感與實際使用畫面，以便我快速理解這是什麼服務。

#### Acceptance Criteria

1. THE Landing_Page SHALL 於 Hero 區同時呈現背景大字紋理、科技藍漸層背景、置中的 Phone_Mockup，以及 3 至 5 個環繞的 Floating_Badge
2. THE Landing_Page SHALL 移除既有主題色塊預覽區塊及其相關預覽狀態邏輯
3. THE Landing_Page SHALL 於 Phone_Mockup 內呈現產品實際 UI 的縮小示意（服務卡或對話氣泡），不以照片替代
4. THE Landing_Page SHALL 保留既有 Highlights 與 Services 區塊的內容與結構，僅更新其色彩與字型至新 Token
5. THE Landing_Page SHALL 於 Light 與 Dark 兩模式下皆使 Hero 內所有文字對比符合 WCAG 2.1 AA 標準

### Requirement 12: 登入頁視覺套用（Tier B）

**User Story:** 身為要登入的使用者，我希望登入頁在視覺升級後仍然清楚易填，以便我能順利完成登入。

#### Acceptance Criteria

1. THE Login_Pages SHALL 以淡化版背景大字紋理作為背景層，其不透明度低於 Landing_Page 所使用的數值
2. THE Login_Pages SHALL 以不透明 `--color-surface` 背景呈現表單卡片，不套用玻璃擬態
3. THE Login_Pages SHALL 維持既有版面結構與欄位順序（含 Demo 帳號說明卡）不變
4. THE Login_Pages SHALL 以 `tone="brand"` 呈現 Mascot_Component

### Requirement 13: 操作型頁面視覺套用（Tier C）

**User Story:** 身為正在使用服務的使用者，我希望操作頁面在視覺升級後仍然好讀好操作，以便我能順利完成服務申請。

#### Acceptance Criteria

1. THE Operational_Pages SHALL 套用一致的 App 殼層背景（`--color-canvas`）與新語意色彩 Token
2. THE `HomePage.tsx` SHALL 以新漸層 Token 呈現頂部 hero 並以 Glass_Panel 包裝其文字區塊，服務卡 grid 維持不透明卡片
3. THE `HomePage.tsx` SHALL 以 Appearance_Menu 取代既有主題選單入口
4. THE `ServiceFormPage.tsx` SHALL 以新漸層 Token 呈現頂部服務資訊卡，表單欄位群組維持不透明卡片
5. THE `RequestDetailPage.tsx`、`MyServicesPage.tsx` 與 `HealthRecommendationPage.tsx` SHALL 以不透明卡片呈現資料密集內容，並以新語意狀態色呈現狀態標示
6. THE Flow_Pages SHALL 以不透明卡片呈現各步驟內容，僅最終確認摘要卡套用 Glass_Panel 或漸層強調
7. THE `ButlerPanel.tsx` SHALL 於 overlay 模式使用 Glass_Panel，於非 overlay 模式使用 `--color-canvas` 底色搭配不透明卡片
8. THE `ButlerLauncher.tsx` SHALL 以漸層 Token 呈現浮動行動按鈕
9. THE `NewRequestPage.tsx` SHALL 不進行自身視覺改動，其外觀變化全數來自 `ButlerPanel.tsx`

### Requirement 14: 廠商後台視覺套用（Tier D）

**User Story:** 身為廠商人員，我希望後台在視覺升級後仍以資訊掃視效率為優先，以便我能快速處理大量案件。

#### Acceptance Criteria

1. THE `VendorRequestsPage.tsx` SHALL 以不透明實色卡片呈現 Tab 列與案件列表，僅頂部標題區可使用極淡漸層色帶做區隔
2. THE `VendorRequestDetailPage.tsx` SHALL 沿用 `RequestDetailPage.tsx` 的不透明卡片處理原則
3. WHILE Dark 模式生效, THE Vendor_Pages SHALL 使列表項目之間的分隔線可被辨識
4. THE Vendor_Pages SHALL 維持既有資訊欄位與操作按鈕的位置與順序不變

### Requirement 15: 視覺特效使用邊界與效能

**User Story:** 身為高齡使用者，我希望資料密集的畫面不要因為特效而變得難讀，以便我能看清楚每一筆資訊。

#### Acceptance Criteria

1. THE Frontend_App SHALL 僅在 Hero、摘要與行銷型卡片使用玻璃擬態與漸層背景
2. THE Frontend_App SHALL 於清單型與資料密集型元件（`RequestCard.tsx`、`VendorRequestsPage.tsx` 列表、`ServiceFormPage.tsx` 表單欄位群組）使用不透明實色卡片，不套用玻璃擬態或漸層
3. THE Frontend_App SHALL 不在列表項目或高頻重繪元素上使用 `backdrop-filter`
4. THE Frontend_App SHALL 以靜態 CSS 實作背景紋理與漸層，不因此新增 JavaScript 運算或動畫迴圈
5. WHILE 使用者裝置的 `prefers-reduced-motion` 為 `reduce`, THE Frontend_App SHALL 維持新增視覺層完整可讀，且不新增任何非必要動畫

### Requirement 16: 對比與高齡友善保證

**User Story:** 身為高齡使用者，我希望不論淺色或深色模式，文字與狀態都清楚可辨，以便我不需要瞇眼或猜測。

#### Acceptance Criteria

1. THE Frontend_App SHALL 使一般內文文字在 Light 與 Dark 兩模式下的對比度皆不低於 4.5:1
2. THE Frontend_App SHALL 使大型文字與圖示在 Light 與 Dark 兩模式下的對比度皆不低於 3:1
3. THE Glass_Panel SHALL 使其內部前景文字在 Light 與 Dark 兩模式下的對比度皆不低於 4.5:1
4. THE Frontend_App SHALL 維持所有可互動元素的觸控區域不小於 44×44px
5. THE Frontend_App SHALL 同時以顏色與文字標籤傳達所有狀態資訊，不單靠顏色區分
6. THE Frontend_App SHALL 使邊框與分隔線在 Light 與 Dark 兩模式下皆可被辨識
7. THE Frontend_App SHALL 使 Modal 與 Toast 在 Light 與 Dark 兩模式下皆具備足夠對比與可辨識的邊界

### Requirement 17: 改版範圍限制

**User Story:** 身為專案負責人，我希望這次改版只動視覺層，以便功能行為不受影響、風險可控。

#### Acceptance Criteria

1. THE Frontend_App SHALL 維持 `App.tsx` 中的路由定義與頁面對應關係完全不變
2. THE Frontend_App SHALL 不變更任何 API 呼叫、資料模型或後端行為
3. THE Frontend_App SHALL 不新增、刪除或合併頁面，也不調整資訊架構
4. THE Frontend_App SHALL 維持既有表單驗證規則、狀態流轉與業務邏輯不變
5. WHERE 既有自動化測試涉及已移除的主題機制（`useTheme`、`ThemeMenu`）, THE Frontend_Test_Suite SHALL 同步更新該測試至新介面；其餘既有測試 SHALL 在改版後仍全數通過

### Requirement 18: 圖片素材策略

**User Story:** 身為專案負責人，我希望改版對外部圖片素材的依賴降到最低，以便素材尚未到齊時開發仍可繼續。

#### Acceptance Criteria

1. THE Frontend_App SHALL 僅於 Landing_Page 的 Hero 區使用真實人物或場景照片，其餘頁面不依賴照片素材
2. THE Landing_Page SHALL 於 Hero 區使用 2 張 1:1 可裁切的人物頭像照片，分別代表年長使用者與到府服務人員
3. THE Landing_Page SHALL 對上述頭像照片在 Light 與 Dark 兩模式下使用同一份圖片，不另備模式專屬版本、不套用濾鏡處理
4. WHERE Landing_Page 採用可選的居家場景淡化底圖, THE Landing_Page SHALL 於 Dark 模式額外疊加 `rgba(11,18,32,0.55)` 深色遮罩再疊加漸層
5. IF 照片素材尚未提供, THEN THE Landing_Page SHALL 以 Mascot_Component 或姓名縮寫圓形色塊作為 placeholder，使其餘視覺工作不被阻塞

### Requirement 19: 品牌敘述文件記錄

**User Story:** 身為未來的協作者，我希望這次改版的品牌方向被明確記錄下來，以便我不會依據過時文件做出衝突的設計決策。

#### Acceptance Criteria

1. THE Frontend_App 專案 SHALL 新增 `docs/brand-guidelines-visual-redesign.md`，記錄本次科技感品牌敘述、雙模式色彩 Token 與視覺特效使用邊界
2. THE `docs/brand-guidelines-visual-redesign.md` SHALL 標註其與 `PRODUCT.md`、`DESIGN.md` 既有敘述衝突之處，並說明本次方向為使用者明確選擇
3. THE Frontend_App 專案 SHALL 不修改 `PRODUCT.md` 與 `DESIGN.md` 本文內容

### Requirement 20: 測試與驗證涵蓋

**User Story:** 身為開發者，我希望色彩模式邏輯有自動化測試、視覺變更有明確檢查清單，以便改版品質可被驗證。

#### Acceptance Criteria

1. THE Frontend_Test_Suite SHALL 以 Vitest 執行，並新增 `fast-check` 至 `frontend/package.json` 的 devDependencies 作為 property-based testing 套件
2. THE Frontend_Test_Suite SHALL 對 design.md〈Correctness Properties〉所列的每一個 property 各執行至少 100 次隨機迭代
3. THE Frontend_Test_Suite SHALL 包含 Color_Mode_System 的單元測試，涵蓋預設值解析、`setMode`、`toggle`，以及 localStorage 讀寫失敗時的 fallback 行為
4. THE Frontend_Test_Suite SHALL 包含 Appearance_Menu 與 Mascot_Component 的渲染測試，驗證選取狀態標示與 `tone` 對應的色彩輸出
5. THE Frontend_App SHALL 於交付前完成 14 個頁面 × Light/Dark 兩模式的人工視覺檢查，並逐項確認 design.md〈Testing Strategy〉的 Pre-Delivery Checklist
