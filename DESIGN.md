---
name: AI 智慧生活服務管家
description: 溫暖可靠的高齡友善服務管家 App，一次一問完成生活服務預約
colors:
  brand: "#0F4C81"
  brand-dark: "#0A3A63"
  brand-soft: "#EAF1F8"
  accent: "#F2A93B"
  accent-soft: "#FDF3E1"
  success: "#2FA766"
  success-soft: "#E7F5EC"
  info: "#2C7BE5"
  info-soft: "#EAF1FC"
  danger: "#C0392B"
  paper: "#FFFDF8"
  paper2: "#FAF9F6"
  canvas: "#EEF1F4"
  ink: "#1F2933"
typography:
  display:
    fontFamily: '"Noto Sans TC", "PingFang TC", "Microsoft JhengHei", sans-serif'
    fontSize: "1.5rem"
    fontWeight: 800
    lineHeight: 1.2
    letterSpacing: "normal"
  title:
    fontFamily: '"Noto Sans TC", "PingFang TC", "Microsoft JhengHei", sans-serif'
    fontSize: "1.125rem"
    fontWeight: 800
    lineHeight: 1.3
  body:
    fontFamily: '"Noto Sans TC", "PingFang TC", "Microsoft JhengHei", sans-serif'
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.6
  label:
    fontFamily: '"Noto Sans TC", "PingFang TC", "Microsoft JhengHei", sans-serif'
    fontSize: "0.875rem"
    fontWeight: 500
rounded:
  md: "16px"
  lg: "24px"
  full: "9999px"
spacing:
  sm: "12px"
  md: "16px"
  lg: "20px"
  xl: "24px"
components:
  button-primary:
    backgroundColor: "{colors.brand}"
    textColor: "{colors.paper}"
    rounded: "{rounded.lg}"
    padding: "20px 24px"
  button-primary-disabled:
    backgroundColor: "{colors.brand}"
    textColor: "{colors.paper}"
    rounded: "{rounded.lg}"
    padding: "20px 24px"
  button-secondary:
    backgroundColor: "{colors.paper}"
    textColor: "#6B7280"
    rounded: "{rounded.lg}"
    padding: "18px 24px"
  card:
    backgroundColor: "{colors.paper}"
    rounded: "{rounded.md}"
    padding: "16px"
  badge-pending:
    backgroundColor: "{colors.accent-soft}"
    textColor: "{colors.accent}"
    rounded: "{rounded.full}"
    padding: "4px 12px"
  badge-success:
    backgroundColor: "{colors.success-soft}"
    textColor: "{colors.success}"
    rounded: "{rounded.full}"
    padding: "4px 12px"
  badge-info:
    backgroundColor: "{colors.info-soft}"
    textColor: "{colors.info}"
    rounded: "{rounded.full}"
    padding: "4px 12px"
  input-field:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.lg}"
    padding: "14px 16px"
---

# Design System: AI 智慧生活服務管家

## 1. Overview

**Creative North Star: "多顏色的小幫手"（The Many-Colored Helper）**

這是一個服務給高齡使用者的生活服務管家 App，核心比喻不是「科技工具」而是「一位可以換裝的家人小幫手」——外殼（Mascot 機器人）可以是不同顏色，但骨架、動作、說話方式永遠是同一位熟悉、可靠的家人。目前的視覺系統本身已經是溫暖、圓潤、平面化、字級放大的高齡友善風格，**這份 DESIGN.md 記錄的是現狀，不是重新設計**——它是之後加入「機器人色系切換」功能時，用來確保「換色不換個性」的基準線。

系統明確拒絕：年輕人愛用的炫技科技感（深色賽博漸層、密集小卡片、小字級）；制式官方表單網站的擁擠與死板；任何需要使用者同時記住多個步驟的介面（違背 Agent「一次一問」的對話邏輯）。

**Key Characteristics:**
- 大量圓角（16–24px），沒有尖角、沒有 `border-left` 色條
- 整體偏平面，淡陰影只出現在彈窗與少數重要卡片
- 大字級（18px base）、粗體標籤、寬鬆內距、大觸控區
- 一套主色（深海藍）+ 一個強調色（溫暖琥珀）+ 三個語意色，色彩角色分工明確，不混用

## 2. Colors

目前已上線的色票是「單一色系」，但 Tailwind config 裡已經預留了三組尚未串接進元件的色相（pine 深綠、leaf 綠、sky 藍）——這正好是未來「機器人換色」功能的天然起點：換色即是把 `brand` token 換成這些預備色相之一。

### Primary
- **深海藍 Deep Ocean Blue** (`#0F4C81` / dark `#0A3A63` / soft `#EAF1F8`): 按鈕、連結、輸入框 focus 邊框、Mascot 機器人身體。整個介面唯一的「行動色」，看到深海藍代表「可以按」。

### Secondary
- **溫暖琥珀 Warm Amber** (`#F2A93B` / soft `#FDF3E1`): Mascot 眼睛與天線、待處理狀態徽章（SUBMITTED / PENDING_PROVIDER）。少量點綴，代表「有事情正在等你」。

### Tertiary（語意色，用於案件狀態）
- **安心綠 Reassuring Green** (`#2FA766` / soft `#E7F5EC`): 已確認／進行中狀態。
- **進度藍 Progress Blue** (`#2C7BE5` / soft `#EAF1FC`): 已完成狀態。
- **警示磚紅 Alert Brick** (`#C0392B`): 失敗狀態與破壞性操作（取消案件確認鈕），刻意選磚紅而非高飽和正紅，降低高齡使用者的焦慮感。

### Neutral
- **暖紙白 Warm Paper** (`#FFFDF8`, 次要 `#FAF9F6`): 全站背景、卡片背景。
- **柔霧灰 Soft Canvas** (`#EEF1F4`): App 殼層背景（非 overlay 模式的 ButlerPanel）。
- **深墨 Deep Ink** (`#1F2933`): 主要文字色，對比暖紙白達 AA 以上。

### Named Rules
**The One Action Color Rule.** 深海藍只用在「可以按下去會發生事情」的元素上（按鈕、連結、focus 狀態）。裝飾性色塊一律用語意色或 soft 色階，不借用主色搶走行動提示的辨識度。
**The Reserved Palette Rule.** pine／leaf／sky 三組色相已定義但未使用，保留給未來「機器人色系切換」功能，不可挪作他用（例如拿 leaf 綠做裝飾性背景），以免將來換色主題互相打架。

## 3. Typography

**Display Font:** "Noto Sans TC", PingFang TC, Microsoft JhengHei, sans-serif
**Body Font:** 同一字族，僅字重與字級不同
**Character:** 單一無襯線字族貫穿全系統，靠字重（400 / 500 / 700 / 800）與字級做層次，不做字型混搭——這符合「不炫技、易辨識」的高齡友善原則。全站基礎字級 18px（`html { font-size: 18px }`），比一般網站預設大一階。

### Hierarchy
- **Display**（800, 1.5rem / 24px, 行高 1.2）：頁面／面板主標題，如服務名稱、「AI 管家」標題。
- **Title**（800, 1.125rem / 18px, 行高 1.3）：卡片內主要資訊，如服務名稱、金額。
- **Body**（400, 1rem / 16–18px, 行高 1.6）：對話內容、說明文字，控制在 65–75ch 內。
- **Label**（500, 0.875rem / 14px）：欄位標籤、次要資訊（時間、狀態說明）。

### Named Rules
**The No-Small-Text Rule.** 任何攜帶資訊的文字不得小於 14px；裝飾性圖示旁的說明文字一律沿用 body 或 label 字級，不為了「精緻感」縮小字級。

## 4. Elevation

系統以**平面為主**，陰影不是常態而是「例外狀態的訊號」。日常卡片（服務清單、案件卡）只用極淡的 `shadow-sm`；只有彈窗（ConfirmModal）與需要從背景中「浮出來」的重要卡片（確認摘要卡）才使用明顯陰影 `shadow-xl`。這個決定是刻意的：陰影太多會讓高齡使用者分不清楚畫面重點在哪裡。

### Shadow Vocabulary
- **surface-low** (`box-shadow: 0 1px 2px rgba(0,0,0,0.05)` / Tailwind `shadow-sm`): 一般卡片（RequestCard、確認摘要卡）的預設狀態，僅用來和背景做極輕微的區隔。
- **overlay-high** (`box-shadow: 0 20px 25px -5px rgba(0,0,0,0.1)` / Tailwind `shadow-xl`): 彈窗（ConfirmModal）等蓋在畫面最上層、必須被立刻注意到的元素。
- **butler-overlay** (`box-shadow: 0 40px 120px rgba(0,0,0,0.48)`): AI 管家面板以浮層模式開啟時的專屬深色陰影，強調「這是暫時蓋上來的對話層」。

### Named Rules
**The Flat-By-Default Rule.** 表面在靜止狀態下一律平面；陰影只在「這個元素蓋在別的內容上面」時才出現，不作為裝飾。

## 5. Components

整體元件個性：**柔軟圓潤、觸手可及**——大圓角、寬內距、粗體字、大觸控區，像可以被安心抓握的實體物件，而不是精巧但難點的科技介面。

### Buttons
- **Shape:** 大圓角（`rounded-2xl` = 16px，主要 CTA 常見 `rounded-2xl`／面板內大按鈕）
- **Primary:** `bg-brand` 深海藍底、白字、粗體，內距寬鬆（`py-5` ≈ 20px 上下），如「確認送出」
- **Disabled:** 同色但 `opacity-40`，不改變顏色語意，只降低存在感
- **Secondary / Ghost:** 白底、2px 灰邊框（`border-gray-200`）、灰字，用於「返回修改」「取消」等次要動作
- **Hover / Focus:** focus 狀態邊框轉為 `border-brand`，維持鍵盤可操作性

### Cards / Containers
- **Corner Style:** `rounded-2xl`（16px）到 `rounded-3xl`（24px），數字越大代表層級越高（案件卡 16px，確認摘要卡 24px）
- **Background:** 一律暖紙白 `paper` / `#FFFFFF`，不使用深色卡片
- **Shadow Strategy:** 見 Elevation 的 surface-low
- **Border:** `border border-gray-200`，細邊框輔助陰影做區隔
- **Internal Padding:** 16–24px（`p-4` 到 `p-6`）

### Badges（案件狀態）
- **Style:** 膠囊形（`rounded-full`），soft 背景 + 對應語意色文字，前綴一個 `bg-current` 圓點
- **State:** 顏色即狀態語意，但一律搭配文字標籤，不單靠顏色傳達（無障礙要求）

### Inputs / Fields
- **Style:** `rounded-2xl`、2px 灰邊框、白底、寬內距（`px-4 py-3.5`）
- **Focus:** 邊框轉為 `border-brand`，無額外陰影或發光效果，維持平面風格一致

### Navigation / Chat Header
- **Style:** 頂部 sticky header，底部 1px 分隔線；overlay 模式下改為半透明白／黑玻璃感（`bg-white/[0.06] backdrop-blur`），僅限於「浮層對話」情境使用，非全站常態

### Mascot（招牌元件）
品牌吉祥物：SVG 機器人，身體用 `brand` 深海藍、眼睛與天線用 `accent` 溫暖琥珀，圓角矩形身體＋圓形頭部＋一對橢圓耳朵，表情用簡單的白底圓臉＋兩點眼睛＋微笑弧線構成。**這是唯一被設計為「可換色」的元件**——未來的機器人色系切換功能，應該只替換 body/eye 的填色 token，不改變造型結構本身，保持「同一位家人、換了件外套」的辨識度。

## 6. Do's and Don'ts

### Do:
- **Do** 保持大圓角家族（16px／24px／full），不混用直角或極小圓角。
- **Do** 陰影只用於彈窗與需要浮出的重要卡片，其餘保持平面（The Flat-By-Default Rule）。
- **Do** 狀態一律「顏色 + 文字／圖示」雙重表達，不單靠顏色（延續 PRODUCT.md 的無障礙要求）。
- **Do** 深海藍只保留給「可互動的行動點」（The One Action Color Rule）。
- **Do** 任何新增動效遵守 `prefers-reduced-motion`，比照現有全域規則。
- **Do** 未來機器人換色功能只替換 token 值（brand/accent 對應色相），沿用既有造型與版面結構。

### Don't:
- **Don't** 做成年輕人愛用的炫技科技感介面（深色賽博漸層、誇張漸層文字、密集小卡片、小字級）—— PRODUCT.md 明確列為 anti-reference。
- **Don't** 做成制式官方表單網站的樣子（死板、擁擠、一次攤開大量必填欄位）—— 違背「一次一問」的產品邏輯。
- **Don't** 使用 `border-left` 色條作為卡片或列表的強調手法。
- **Don't** 對正文文字使用漸層或 `background-clip: text` 效果。
- **Don't** 挪用保留色相（pine／leaf／sky）做裝飾性背景，它們是未來換色主題的專屬資源。
- **Don't** 讓任何互動元件的觸控區小於 44px，或讓使用者需要同時記住兩個以上步驟才能完成一個操作。


