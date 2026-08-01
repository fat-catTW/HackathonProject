---
inclusion: fileMatch
fileMatchPattern: "*.test.ts*"
---

# 測試撰寫慣例

## 單元測試

- 使用 Vitest + Testing Library；模組層級狀態（如 `useColorMode`、`useAccessibilityMode`）的 hook 測試須以 `vi.resetModules()` 搭配動態 `import()` 取得乾淨初始狀態，並在 `beforeEach` 清空 `localStorage` 與相關 `data-*` 屬性。
- 涉及計時器的行為（例如 `Toast` 的自動關閉）使用 `vi.useFakeTimers()` 明確控制，並在 `afterEach` 還原。

## Property-Based Testing

- 使用 `fast-check`，套件版本一律鎖定固定版本號（不使用 `^`/`~`）。
- 每個正式的 correctness property 迭代次數至少 100 次（`numRuns: 100`）。
- 生成器範圍需覆蓋邊界情況：空字串、非法列舉值、資料存取拋出例外、瀏覽器 API（如 `matchMedia`）不存在等情境。
- 每個 property 測試上方以註解標明對應的需求編號（`Validates: Requirements ...`），方便追溯規格。

## 靜態樣式斷言

- 對 `index.css` 這類非模組化樣式檔案，改用 `node:fs` 直接讀取原始碼並解析，而非依賴 Vitest 的 CSS 轉換管線（`?raw` 匯入在目前設定下會得到空字串）。
- 解析工具集中在共用模組中，避免多份測試各自維護一套 CSS parser。
