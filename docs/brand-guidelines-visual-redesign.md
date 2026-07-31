# 品牌視覺敘述：Guarrent 科技風 + Light/Dark 雙模式

> 對應 spec：`.kiro/specs/app-visual-redesign/`
> 狀態：本次改版已實作完成
> 適用範圍：`frontend/` 的 14 個頁面與共用元件

本文件記錄本次視覺改版所採用的品牌敘述與設計 Token。**本文件不修改 `PRODUCT.md` 與
`DESIGN.md` 的內容**；兩者與本次方向的衝突之處集中列於文末〈與既有文件的衝突〉一節。

---

## 1. 品牌敘述

**核心定位：可信賴的科技感服務管家。**

介面要傳達的是「這套系統背後有真正的技術在運作、而且運作得很穩」。視覺語言以科技藍為主調、
玻璃擬態與品牌漸層作為重點強調，搭配大字紋理建立品牌存在感。

同時保留高齡友善的既有基礎，不因追求科技感而犧牲可用性：
根字級維持 18px、觸控區維持 ≥44×44px、狀態一律「顏色 + 文字」雙重表達、
內文對比 ≥4.5:1，且無障礙模式（`data-a11y`）與色彩模式（`data-color-mode`）互不干擾。

**Light / Dark 為使用者可自行切換的兩種呈現，非主題色自訂。** 使用者只選「亮/暗」，
不選顏色 —— 色彩決策收回設計系統，確保任何模式下的對比與語意都經過驗證。

---

## 2. 色彩 Token

單一來源：`frontend/src/index.css`。兩個模式的變數名稱集合完全相同，
切換 `html[data-color-mode]` 即可整站換裝，元件端不需要成對的 class 分支。

### 2.1 品牌色（Brand）

| Token | Light | Dark | 用途 |
|---|---|---|---|
| `--color-primary` | `#2563EB` | `#3B82F6` | 主要行動按鈕、連結、選取狀態 |
| `--color-primary-hover` | `#1D4ED8` | `#60A5FA` | hover / active |
| `--color-primary-accent` | `#60A5FA` | `#7DD3FC` | 漸層終點色 |
| `--color-on-primary` | `#FFFFFF` | `#0B1220` | 疊在品牌填色上的文字／圖示 |
| `--color-primary-soft` | `#EFF6FF` | `rgba(59,130,246,0.16)` | 圖示襯底、低強調區塊 |

> `--color-on-primary` 在 Dark 模式為近黑：primary 提亮後配白字對比不足，改用深色字才達標。

### 2.2 表面色（Surface）

| Token | Light | Dark | 用途 |
|---|---|---|---|
| `--color-background` | `#F8FAFC` | `#0B1220` | 頁面底 |
| `--color-canvas` | `#EEF2FA` | `#0F1A2E` | 區塊底、次級容器 |
| `--color-surface` | `#FFFFFF` | `#141E33` | 不透明卡片 |
| `--color-surface-glass` | `rgba(255,255,255,0.6)` | `rgba(20,30,51,0.55)` | 玻璃卡片底 |
| `--color-border` | `#E2E8F0` | `rgba(255,255,255,0.08)` | 邊框、分隔線 |
| `--color-glass-border` | `rgba(255,255,255,0.8)` | `rgba(255,255,255,0.14)` | 玻璃卡片邊框 |
| `--color-scrim` | `rgba(15,23,42,0.5)` | `rgba(2,6,23,0.6)` | Modal / Drawer 遮罩 |

### 2.3 文字色（Text）

| Token | Light | Dark | 用途 |
|---|---|---|---|
| `--color-foreground` | `#0F172A` | `#F1F5F9` | 標題與內文 |
| `--color-muted-foreground` | `#475569` | `#94A3B8` | 次要說明、時間戳 |

### 2.4 語意狀態色（Semantic）

| Token | Light | Dark |
|---|---|---|
| `--color-success` / `-soft` | `#15803D` / `#DCFCE7` | `#4ADE80` / `rgba(74,222,128,0.16)` |
| `--color-warning` / `-soft` | `#B45309` / `#FEF3C7` | `#FBBF24` / `rgba(251,191,36,0.16)` |
| `--color-danger` / `-soft` | `#B91C1C` / `#FEE2E2` | `#F87171` / `rgba(248,113,113,0.16)` |
| `--color-info` / `-soft` | `#2563EB` / `#EFF6FF` | `#60A5FA` / `rgba(59,130,246,0.16)` |

Light 模式的狀態色刻意比常見的 `green-600 / amber-600 / red-600` 各深一階：
原色作為徽章文字疊在自身 soft 背景上僅 2.86–3.95:1，未達 4.5:1。
所有配對由 `frontend/src/styles/contrast.test.ts` 自動驗證。

### 2.5 Mascot 色（固定，使用者不可自訂）

| Token | Light | Dark |
|---|---|---|
| `--color-mascot-body` | `#2563EB` | `#3B82F6` |
| `--color-mascot-accent` | `#60A5FA` | `#7DD3FC` |

`Mascot` 以 `tone` prop 控制色調（`brand` / `inverted` / `muted`），
不再接受任意色字串。造型結構在兩模式間完全相同。

---

## 3. 字型配對

| Token | 字族 | 用途 |
|---|---|---|
| `--font-display` | Space Grotesk → Noto Sans TC | 大標題、行銷型排版（拉丁字母吃 Space Grotesk，中文自動 fallback） |
| `--font-body` | Noto Sans TC → PingFang TC → Microsoft JhengHei | 內文（維持改版前設定不變） |
| `--font-mono` | JetBrains Mono → SFMono-Regular → Consolas | 資料型文字：案件編號、時間戳、金額、電話、時段 |

網路字型於 `frontend/index.html` 以 `<link>` 載入並設定 `font-display: swap`，
字型未載入完成前先以系統字族呈現，不出現空白文字。

---

## 4. 視覺特效使用邊界

科技感特效只用在「重點」，不用在「資料」。這條界線由
`frontend/src/styles/visualBoundaries.test.ts` 靜態掃描守住。

| 特效 | 可以用在 | 不可以用在 |
|---|---|---|
| 玻璃擬態 `.glass-panel` / `<GlassPanel>` | Hero 文字區、最終確認摘要卡、AI 管家 overlay、漂浮徽章 | 案件列表、餐廳卡、對話氣泡、欄位面板、表單欄位群組、廠商後台列表 |
| 品牌漸層 `.bg-brand-gradient` | 首頁 hero、服務資訊卡、主要行動按鈕、AI 管家浮動按鈕 | 任何列表項目、表單欄位 |
| 極淡漸層 `.bg-brand-gradient-soft` | 資料密集頁面的標題區色帶 | 列表本身、Tab 列 |
| 大字紋理 `.bg-wordmark-texture` | LandingPage Hero | — |
| 淡化紋理 `--subtle` 變體 | 登入頁背景 | — |

補充規則：

- 玻璃擬態一律附 `@supports not (backdrop-filter: ...)` fallback，退回不透明 `--color-surface`
- 大字紋理為 `aria-hidden` + `pointer-events: none`，永不攔截互動
- 漂浮徽章 `FloatingBadge` 整張卡 `pointer-events: none`，不遮擋可互動元素
- 所有動效在 `prefers-reduced-motion: reduce` 下由 `index.css` 全域停用
- 元件與頁面不得出現硬編碼 hex 色碼（唯一例外：`Mascot.tsx` 的造型固定色）

---

## 5. 與既有文件的衝突

以下四點與 `PRODUCT.md` / `DESIGN.md` 的既有敘述直接衝突。
**本次方向為使用者在 spec 需求釐清階段的明確選擇**，兩份既有文件維持原狀未修改，
後續若要收斂敘述，應由產品端另行決定以哪一份為準。

| # | 既有敘述 | 本次方向 |
|---|---|---|
| 1 | `PRODUCT.md` L35 與 `DESIGN.md` L99 明確拒絕「深色系賽博風、誇張漸層」的炫技科技感，理由是對高齡用戶不友善 | 本次採用科技藍主調 + Dark 模式 + 玻璃擬態與漸層。高齡友善的具體措施（18px 根字級、≥44px 觸控區、對比 ≥4.5:1、顏色＋文字雙重表達）全數保留並以自動化測試驗證 |
| 2 | `PRODUCT.md` L29／L45：使用者可自訂 Mascot 顏色／風格，介面隨之換色，作為「屬於我自己」的品牌個性實作 | 移除 5 色塊主題自訂機制（`useTheme` / `ThemeMenu` 已刪除），改為 Light/Dark 兩模式切換；Mascot 色彩固定由設計系統決定 |
| 3 | `DESIGN.md` L105：一套主色（深海藍）+ 一個強調色（溫暖琥珀） | 主色改為科技藍 `#2563EB`，強調色改為亮藍 `#60A5FA`；琥珀色退為 `--color-warning` 的語意狀態色 |
| 4 | `DESIGN.md` L21–39：全站單一字族 Noto Sans TC | 新增 `--font-display`（Space Grotesk）與 `--font-mono`（JetBrains Mono）；內文字族仍為 Noto Sans TC，未變動 |

---

## 6. 相關檔案

| 檔案 | 角色 |
|---|---|
| `frontend/src/index.css` | 色彩／字型 Token 與工具類別的單一來源 |
| `frontend/src/hooks/useColorMode.ts` | 色彩模式狀態與持久化 |
| `frontend/src/components/AppearanceMenu.tsx` | Light/Dark 切換與無障礙開關入口 |
| `frontend/src/components/GlassPanel.tsx` | 玻璃擬態容器 |
| `frontend/src/components/PhoneMockup.tsx` | 純 CSS 手機外框 |
| `frontend/src/components/FloatingBadge.tsx` | 漂浮徽章（icon / avatar 兩型） |
| `frontend/tailwind.config.js` | 既有色彩別名對應至語意 Token |
| `frontend/src/styles/contrast.test.ts` | 對比度自動驗證 |
| `frontend/src/styles/visualBoundaries.test.ts` | 特效邊界、硬編碼色碼與改版範圍的靜態掃描 |
