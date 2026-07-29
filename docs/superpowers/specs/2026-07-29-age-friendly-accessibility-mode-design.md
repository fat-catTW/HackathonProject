# M20｜高齡友善介面模式（無障礙模式）Design

## 背景

現有專案已經是高齡友善取向的視覺系統（`index.css` 的 `html { font-size: 18px }`、44px 觸控區域、狀態一律「顏色＋文字」雙重表達等），但目前是「固定的單一基準」，沒有使用者可自行開啟的「加強版」模式。這次要新增一個可切換的「無障礙模式」開關，開啟後字級/間距再放大一階、常見淺灰文字對比度提高、首頁多一個大按鈕可以一鍵撥打客服電話。

專案裡已經有一套結構幾乎一樣的既有機制可以直接沿用：`frontend/src/hooks/useTheme.ts` + `frontend/src/components/ThemeMenu.tsx` 用 `data-theme` 屬性 + CSS 變數 + localStorage，做「機器人管家顏色切換」，全站即時生效、不用重新整理頁面、也不接後端。本次的無障礙模式在技術上是同一種機制（開關 → 改一個 `data-*` 屬性 → CSS 連動），直接複用這個已驗證的模式。

## 目標

1. 使用者可以在首頁開啟/關閉「無障礙模式」，全站即時套用，不需重新整理頁面。
2. 開啟後：全站字級與間距放大 1.3 倍（18px → 23.4px root font-size，因為 Tailwind 的字級/間距 class 都是 rem 為單位，改根字級即可連動全站，不用逐元件修改）。
3. 開啟後：全站常見的淺灰文字（`text-gray-300/400/500/600`，這是目前程式碼裡實際用到的四階）統一換成深色，提高對比度。
4. 開啟後：首頁服務卡片列表上方出現一個明顯的「撥打客服專線」大按鈕（`tel:` 連結，示範號碼 `0800-000-000` 佔位）。
5. 偏好設定存在 localStorage，同一裝置下次造訪自動套用（跟現有換色功能的持久化方式一致）。

## 非目標（本次不做，列為已知限制）

- **後端持久化／跨裝置同步**：不新增 `/user/ui-preference` API，不接資料庫。跟現有換色功能一樣，只存在使用者當前裝置的 localStorage，換裝置或清瀏覽器資料不會保留設定。
- **巢狀報價明細表格的卡片式替代版型**：目前專案沒有這種表格型元件，之後真的出現時再另外設計。
- **與 iOS/系統層級動態字體（Dynamic Type）疊加時取較大值**：網頁在標準瀏覽器環境下沒有可靠的 API 能偵測使用者的系統層級文字大小設定，技術上難以在這次範圍內做到「取較大值」；使用者若同時開啟系統字體放大與本功能，可能出現雙重放大的版面問題，暫不處理。
- **「一次一問」表單簡化**：現有聊天流程（一次一問）與精靈頁（一步一決策）架構已經符合這個需求，不需要額外修改。
- **精細的 WCAG AA 對比度逐一稽核**：只統一處理上述四階淺灰文字 class，不逐頁逐元件檢查所有顏色組合的對比度數值。

## 架構

### 1. `useAccessibilityMode.ts`（新檔案，`frontend/src/hooks/`）

完全比照 `useTheme.ts` 的實作模式：

- 模組層級狀態變數 + `Set<() => void>` 監聽器清單（不用 React Context）。
- `localStorage` key：`"ai-butler-a11y"`，值為 `"true"` / `"false"` 字串。
- 套用方式：`document.documentElement.setAttribute("data-a11y", enabled ? "true" : "false")`。
- `useSyncExternalStore` 讓任何元件都能訂閱目前開關狀態並在變更時重新渲染。
- 對外介面：`const { enabled, toggle } = useAccessibilityMode();`

### 2. `index.css` 新增規則

在既有 `html[data-theme="..."]` 那組規則之後，新增：

```css
html[data-a11y="true"] {
  font-size: 23.4px; /* 18px × 1.3，高齡友善模式：全站字級與間距（rem 為單位）連動放大 */
}

html[data-a11y="true"] .text-gray-300,
html[data-a11y="true"] .text-gray-400,
html[data-a11y="true"] .text-gray-500,
html[data-a11y="true"] .text-gray-600 {
  color: var(--color-ink, #1F2933);
}
```

（`--color-ink` 目前專案沒有定義成 CSS 變數，`ink` 是 Tailwind config 裡的固定色 `#1F2933`；這裡直接寫死色碼＋保留 var() fallback 語法，不用另外新增變數。）

### 3. `ThemeMenu.tsx` 新增第六格

在現有 5 個顏色格子的 `grid-cols-3` 網格裡加第 6 格，語意上是「開關」而不是「選色」，所以：

- 不是色塊，是一個放大鏡圖示（沿用專案既有 icon 元件慣例）＋文字「無障礙模式」。
- `role="menuitemcheckbox"` + `aria-checked={enabled}`（既有色塊格是 `role="menuitemradio"` + `aria-checked`，語意不同要分開，避免螢幕報讀器唸錯）。
- 選中狀態視覺上比照色塊的 `active` 樣式（邊框/底色標示），不引入新的視覺語言。
- 點擊呼叫 `toggle()`，**不**關閉選單（跟色塊選擇後會 `setOpen(false)` 不同——開關可能想跟換色一起操作，關掉選單會打斷操作流程）。

### 4. `HomePage.tsx` 新增客服撥號按鈕

`useAccessibilityMode()` 取得 `enabled`，為 `true` 時，在「目前所有服務」卡片列表**上方**插入：

```tsx
{enabled && (
  <a
    href="tel:0800000000"
    className="mb-4 flex items-center justify-center gap-3 rounded-2xl bg-brand py-6 text-xl font-black text-white shadow-sm"
  >
    <ServiceIcon type="phone" size={28} />
    撥打客服專線 0800-000-000
  </a>
)}
```

（`ServiceIcon` 的 `type="phone"` 沿用既有欄位輸入圖示，若沒有現成的話用最接近的既有圖示；電話號碼用字面常數，之後要換真號碼只需改這一行。）

## 資料流

不涉及後端或 API 呼叫。完全是前端 hook（localStorage 讀寫）→ DOM 屬性（`data-a11y`）→ CSS 選擇器連動的單向流程，跟現有換色功能的資料流完全對稱。

## 測試範圍

`useTheme.ts` 與 `ThemeMenu.tsx` 目前都沒有測試檔，這次不另立更嚴格的標準。只針對新的 `useAccessibilityMode.ts` 補 vitest 單元測試：

- 預設值（無 localStorage 紀錄時）為關閉。
- `toggle()` 正確切換狀態、寫入 localStorage、設定 `data-a11y` 屬性。
- 從 localStorage 讀到 `"true"` 時初始狀態為開啟。

`ThemeMenu.tsx`／`HomePage.tsx` 的改動不寫元件測試（跟現有換色功能一致）。完成後跑 `tsc --noEmit` 確認型別正確，不需要後端測試（本次不改後端）。
