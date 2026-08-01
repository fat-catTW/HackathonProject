---
inclusion: always
---

# 設計 Token 與色彩模式規範

本專案的視覺樣式一律透過語意化 CSS 變數（design tokens）驅動，禁止在元件或樣式檔中寫死色碼。

## 色彩模式

- 色彩模式由 `html[data-color-mode="light"]` / `html[data-color-mode="dark"]` 兩個屬性選擇器切換，變數集合須完全相同。
- 兩個模式皆須宣告對應的 `color-scheme`。
- 初始化邏輯集中於 `frontend/src/hooks/useColorMode.ts`：讀取 localStorage key `ai-butler-color-mode`，無效或缺失值一律回退為系統固定預設 `"light"`，不依賴 `prefers-color-scheme`。
- 所有讀寫 localStorage 的動作必須包在 try/catch 中靜默失敗，不可讓偏好設定的儲存失敗影響畫面渲染。

## Token 分層

- Brand（`--color-primary` 系列）、Surface（`--color-background` / `--color-surface` / `--color-canvas`）、Text（`--color-foreground` / `--color-muted-foreground`）、Semantic status（`--color-success` / `-warning` / `-danger` / `-info`，含 `-soft` 變體）、Mascot（`--color-mascot-body` / `-accent`，固定值不可由使用者自訂）。
- 元件一律以 `bg-[var(--color-...)]` / `text-[var(--color-...)]` 的形式引用 token，不使用固定的 Tailwind 色階（例如 `bg-gray-100`、`text-red-600`）或硬編碼 hex。

## 對比度與無障礙

- 一般內文文字對比須 ≥ 4.5:1，大型文字與圖示須 ≥ 3:1（WCAG AA）。
- 狀態呈現（如 `StatusBadge`）必須同時以顏色與文字傳達語意，不可只靠顏色。
- 玻璃擬態元件（`.glass-panel`）須提供 `@supports not (backdrop-filter: blur(1px))` 的不透明退回樣式。
- Modal / Drawer 的遮罩不透明度需落在可隔離前景內容的區間（約 40–60% 深色）。

## 新增樣式時的檢查清單

1. 新色彩一律先加入 `frontend/src/index.css` 的 Light/Dark 兩個區塊，不要在元件內另開變數。
2. 新增後執行對比度計算，確認符合上述門檻。
3. 不確定色彩語意時，優先重用既有的狀態色（success/warning/danger/info），避免新增一次性色碼。
