# M20｜高齡友善介面模式 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 讓使用者可以在首頁開啟/關閉「無障礙模式」，開啟後全站字級與間距放大 1.3 倍、常見淺灰文字對比度提高、首頁多一個一鍵撥打客服電話的大按鈕；設定存在 localStorage，下次造訪自動套用。

**Architecture:** 完全複用專案既有的「機器人換色」機制（`frontend/src/hooks/useTheme.ts` + `frontend/src/components/ThemeMenu.tsx`）：新增一個結構對稱的 `useAccessibilityMode.ts` hook（`useSyncExternalStore` + localStorage + 在 `<html>` 上設定 `data-a11y` 屬性），`index.css` 用屬性選擇器定義字級/間距/對比度規則，全站因為 Tailwind 的字級與間距 class 都是 rem 為單位而自動連動放大，不用逐元件修改。開關本身整合進 `ThemeMenu.tsx` 既有的選單，變成第 6 格（語意上是開關，用 `menuitemcheckbox` 而非色塊的 `menuitemradio`）。

**Tech Stack:** React + TypeScript + Vite + Tailwind（前端限定，這次不改後端）、vitest + @testing-library/react（測試）。

## Global Constraints

- 偏好設定只存 localStorage，key 為 `"ai-butler-a11y"`（比照現有 `useTheme.ts` 的 `"ai-butler-theme"` 命名風格），不新增後端 API、不接資料庫。
- 字級/間距放大倍率固定 1.3 倍：18px → 23.4px（root font-size）。
- 對比度覆寫只處理專案目前實際用到的四階淺灰文字 class：`text-gray-300`、`text-gray-400`、`text-gray-500`、`text-gray-600`，統一換成 `#1F2933`（Tailwind config 裡的 `ink` 色）。
- 客服電話用示範號碼 `0800-000-000` 佔位，`tel:0800000000` 連結格式。
- 不新增任何 npm 套件；不實作巢狀表格卡片化、不處理 iOS 系統層級動態字體疊加、不改動「一次一問」表單流程（這些都是規格文件裡列出的已知限制/非目標）。
- 所有互動元件觸控區域不小於 44×44px、狀態一律「顏色＋文字」雙重表達——沿用專案既有規範，不需額外檢查（本次改動的元件本來就滿足）。

---

## File Structure

### New files

| File | Responsibility |
|---|---|
| `frontend/src/hooks/useAccessibilityMode.ts` | 無障礙模式開關的狀態管理（localStorage 讀寫 + `data-a11y` 屬性設定 + 跨元件同步） |
| `frontend/src/hooks/useAccessibilityMode.test.ts` | 上述 hook 的單元測試 |

### Modified files

| File | Change |
|---|---|
| `frontend/src/index.css` | 新增 `html[data-a11y="true"]` 的字級放大與對比度覆寫規則 |
| `frontend/src/components/ServiceIcon.tsx` | 新增 `"zoom"`（放大鏡）圖示類型 |
| `frontend/src/components/ThemeMenu.tsx` | 選單網格新增第 6 格：無障礙模式開關 |
| `frontend/src/pages/HomePage.tsx` | 無障礙模式開啟時，服務卡片列表上方顯示「撥打客服專線」大按鈕 |

---

## Task 1: 無障礙模式狀態 Hook 與全站 CSS 規則

**Files:**
- Create: `frontend/src/hooks/useAccessibilityMode.ts`
- Create: `frontend/src/hooks/useAccessibilityMode.test.ts`
- Modify: `frontend/src/index.css`

**Interfaces:**
- Produces: `useAccessibilityMode(): { enabled: boolean; toggle: () => void }`
- Consumed by: Task 2（`ThemeMenu.tsx`）、Task 3（`HomePage.tsx`）

這個 hook 完全比照 `frontend/src/hooks/useTheme.ts` 的既有寫法（模組層級狀態 + `Set` 監聽器 + `useSyncExternalStore`，不用 React Context）。

- [ ] **Step 1: 寫失敗測試**

```ts
// frontend/src/hooks/useAccessibilityMode.test.ts
import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

async function importFreshHook() {
  vi.resetModules();
  const mod = await import("./useAccessibilityMode");
  return mod.useAccessibilityMode;
}

beforeEach(() => {
  localStorage.clear();
  document.documentElement.removeAttribute("data-a11y");
});

describe("useAccessibilityMode", () => {
  it("defaults to disabled when localStorage has no saved preference", async () => {
    const useAccessibilityMode = await importFreshHook();
    const { result } = renderHook(() => useAccessibilityMode());

    expect(result.current.enabled).toBe(false);
    expect(document.documentElement.getAttribute("data-a11y")).toBe("false");
  });

  it("reads a previously saved enabled preference on load", async () => {
    localStorage.setItem("ai-butler-a11y", "true");
    const useAccessibilityMode = await importFreshHook();
    const { result } = renderHook(() => useAccessibilityMode());

    expect(result.current.enabled).toBe(true);
    expect(document.documentElement.getAttribute("data-a11y")).toBe("true");
  });

  it("toggle() flips the state, persists it, and updates the data-a11y attribute", async () => {
    const useAccessibilityMode = await importFreshHook();
    const { result } = renderHook(() => useAccessibilityMode());
    expect(result.current.enabled).toBe(false);

    act(() => {
      result.current.toggle();
    });

    expect(result.current.enabled).toBe(true);
    expect(localStorage.getItem("ai-butler-a11y")).toBe("true");
    expect(document.documentElement.getAttribute("data-a11y")).toBe("true");

    act(() => {
      result.current.toggle();
    });

    expect(result.current.enabled).toBe(false);
    expect(localStorage.getItem("ai-butler-a11y")).toBe("false");
    expect(document.documentElement.getAttribute("data-a11y")).toBe("false");
  });
});
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `cd frontend && npx vitest run src/hooks/useAccessibilityMode.test.ts`
Expected: FAIL，錯誤訊息包含找不到 `./useAccessibilityMode` 模組（檔案還不存在）

- [ ] **Step 3: 實作 hook**

```ts
// frontend/src/hooks/useAccessibilityMode.ts
import { useCallback, useSyncExternalStore } from "react";

const STORAGE_KEY = "ai-butler-a11y";
const listeners = new Set<() => void>();

function readStoredEnabled(): boolean {
  try {
    return localStorage.getItem(STORAGE_KEY) === "true";
  } catch {
    return false;
  }
}

function applyToDocument(enabled: boolean) {
  if (typeof document !== "undefined") {
    document.documentElement.setAttribute("data-a11y", enabled ? "true" : "false");
  }
}

let currentEnabled = readStoredEnabled();
applyToDocument(currentEnabled);

function notify() {
  listeners.forEach((fn) => fn());
}

export function useAccessibilityMode() {
  const enabled = useSyncExternalStore(
    (cb) => {
      listeners.add(cb);
      return () => listeners.delete(cb);
    },
    () => currentEnabled,
  );

  const toggle = useCallback(() => {
    currentEnabled = !currentEnabled;
    try {
      localStorage.setItem(STORAGE_KEY, String(currentEnabled));
    } catch {
      /* ignore write failures (private browsing, quota) */
    }
    applyToDocument(currentEnabled);
    notify();
  }, []);

  return { enabled, toggle };
}
```

- [ ] **Step 4: 執行測試確認通過**

Run: `cd frontend && npx vitest run src/hooks/useAccessibilityMode.test.ts`
Expected: PASS（3 passed）

- [ ] **Step 5: 新增 CSS 規則**

在 `frontend/src/index.css` 裡，找到既有的 `html[data-theme="twilight"] { ... }` 區塊（第五組主題色規則，結尾是 `}`），在它之後、`@keyframes fade-up-in` 之前，插入：

```css
/* 無障礙模式：字級/間距（rem 為單位）連動放大，並提高淺灰文字對比度 */
html[data-a11y="true"] {
  font-size: 23.4px; /* 18px × 1.3 */
}

html[data-a11y="true"] .text-gray-300,
html[data-a11y="true"] .text-gray-400,
html[data-a11y="true"] .text-gray-500,
html[data-a11y="true"] .text-gray-600 {
  color: #1F2933;
}
```

- [ ] **Step 6: 執行完整前端測試套件確認沒有回歸**

Run: `cd frontend && npx vitest run`
Expected: 全部通過（含既有測試，確認新增檔案沒有破壞其他東西）

- [ ] **Step 7: Commit**

```bash
git add frontend/src/hooks/useAccessibilityMode.ts frontend/src/hooks/useAccessibilityMode.test.ts frontend/src/index.css
git commit -m "feat: add accessibility mode hook and global CSS scaling rules"
```

---

## Task 2: 無障礙模式開關整合進換色選單

**Files:**
- Modify: `frontend/src/components/ServiceIcon.tsx`
- Modify: `frontend/src/components/ThemeMenu.tsx`

**Interfaces:**
- Consumes: `useAccessibilityMode()`（Task 1）
- Produces: `ServiceIconType` 新增 `"zoom"` 成員

`ThemeMenu.tsx` 跟 `ServiceIcon.tsx` 目前都沒有既有測試檔案覆蓋這類 UI 整合改動（`ServiceIcon.test.tsx` 只測試泛用行為，不逐一測試每種圖示），這個任務不另外新增測試，跟現有慣例一致，用 `tsc --noEmit` 把關型別正確性。

- [ ] **Step 1: 在 `ServiceIcon.tsx` 新增 `"zoom"` 圖示**

把 `frontend/src/components/ServiceIcon.tsx` 第 1-5 行的型別定義：

```ts
export type ServiceIconType =
  | "aircon" | "plumbing" | "appliance" | "cleaning" | "pest" | "moving" | "restaurant"
  | "mic" | "send" | "check" | "chevronRight" | "chevronDown" | "close"
  | "back" | "phone" | "location" | "calendar" | "clock" | "chat"
  | "info" | "warning" | "logo";
```

改成：

```ts
export type ServiceIconType =
  | "aircon" | "plumbing" | "appliance" | "cleaning" | "pest" | "moving" | "restaurant"
  | "mic" | "send" | "check" | "chevronRight" | "chevronDown" | "close"
  | "back" | "phone" | "location" | "calendar" | "clock" | "chat"
  | "info" | "warning" | "logo" | "zoom";
```

在 `PATHS` 物件裡，`logo: (...)` 那個條目之後（`};` 收尾之前）新增：

```tsx
  zoom: (
    <>
      <circle cx="10" cy="10" r="6.5" /><line x1="14.8" y1="14.8" x2="20" y2="20" />
    </>
  ),
```

- [ ] **Step 2: 執行既有 ServiceIcon 測試確認沒有回歸**

Run: `cd frontend && npx vitest run src/components/ServiceIcon.test.tsx`
Expected: PASS（3 passed，確認新增圖示類型沒有破壞現有的泛用渲染測試）

- [ ] **Step 3: `ThemeMenu.tsx` 加上無障礙模式開關格**

把 `frontend/src/components/ThemeMenu.tsx` 檔案開頭的 import：

```tsx
import { useEffect, useRef, useState } from "react";
import { useTheme } from "../hooks/useTheme";
import { Mascot } from "./Mascot";
```

改成：

```tsx
import { useEffect, useRef, useState } from "react";
import { useAccessibilityMode } from "../hooks/useAccessibilityMode";
import { useTheme } from "../hooks/useTheme";
import { Mascot } from "./Mascot";
import { ServiceIcon } from "./ServiceIcon";
```

把函式內第一行：

```tsx
  const { themeId, themes, setTheme } = useTheme();
```

改成：

```tsx
  const { themeId, themes, setTheme } = useTheme();
  const { enabled: a11yEnabled, toggle: toggleA11y } = useAccessibilityMode();
```

在顏色格子的 `{themes.map((t) => { ... })}` 區塊結束、`</div>`（`grid grid-cols-3 gap-3` 的收尾）之前，插入第 6 格：

```tsx
            <button
              type="button"
              role="menuitemcheckbox"
              aria-checked={a11yEnabled}
              aria-label="切換無障礙模式"
              onClick={toggleA11y}
              className={`flex flex-col items-center gap-1.5 rounded-2xl border-2 p-2 transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand ${
                a11yEnabled ? "border-brand bg-brand-soft" : "border-transparent hover:border-gray-200"
              }`}
            >
              <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gray-100 text-slate-600">
                <ServiceIcon type="zoom" size={26} />
              </span>
              <span className="text-xs font-bold text-slate-600">無障礙模式</span>
            </button>
```

（完整結構：`themes.map(...)` 產生的 5 個 `<button role="menuitemradio">` 之後，緊接著這個第 6 個 `<button role="menuitemcheckbox">`，兩者是同一個 `grid grid-cols-3 gap-3` 容器裡的手足元素。）

- [ ] **Step 4: 型別檢查**

Run: `cd frontend && npx tsc --noEmit`
Expected: 無錯誤輸出

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ServiceIcon.tsx frontend/src/components/ThemeMenu.tsx
git commit -m "feat: add accessibility mode toggle to theme menu"
```

---

## Task 3: 首頁客服撥號按鈕

**Files:**
- Modify: `frontend/src/pages/HomePage.tsx`

**Interfaces:**
- Consumes: `useAccessibilityMode()`（Task 1）、`ServiceIcon type="phone"`（既有圖示，Task 2 未變動）

`HomePage.tsx` 目前沒有測試檔案，這個任務不另外新增，跟現有慣例一致。

- [ ] **Step 1: 加上無障礙模式判斷與撥號按鈕**

把 `frontend/src/pages/HomePage.tsx` 檔案開頭的 import：

```tsx
import { useNavigate } from "react-router-dom";
import { ButlerLauncher } from "../components/ButlerLauncher";
import { Mascot } from "../components/Mascot";
import { ServiceIcon } from "../components/ServiceIcon";
import { ThemeMenu } from "../components/ThemeMenu";
import { SERVICES } from "../data/services";
import { useAuth } from "../hooks/useAuth";
```

改成：

```tsx
import { useNavigate } from "react-router-dom";
import { ButlerLauncher } from "../components/ButlerLauncher";
import { Mascot } from "../components/Mascot";
import { ServiceIcon } from "../components/ServiceIcon";
import { ThemeMenu } from "../components/ThemeMenu";
import { SERVICES } from "../data/services";
import { useAccessibilityMode } from "../hooks/useAccessibilityMode";
import { useAuth } from "../hooks/useAuth";
```

把函式內第一行：

```tsx
  const { name, logout } = useAuth();
```

改成：

```tsx
  const { name, logout } = useAuth();
  const { enabled: a11yEnabled } = useAccessibilityMode();
```

在服務首頁介紹卡片（`<section className="relative mt-8 overflow-hidden rounded-[32px] bg-gradient-to-br ...">` 那一整段，結尾是 `</section>`）之後、「目前所有服務」那個 `<section className="mt-8">` 之前，插入：

```tsx
        {a11yEnabled && (
          <a
            href="tel:0800000000"
            className="mt-8 flex items-center justify-center gap-3 rounded-2xl bg-brand py-6 text-xl font-black text-white shadow-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
          >
            <ServiceIcon type="phone" size={28} />
            撥打客服專線 0800-000-000
          </a>
        )}
```

- [ ] **Step 2: 型別檢查**

Run: `cd frontend && npx tsc --noEmit`
Expected: 無錯誤輸出

- [ ] **Step 3: 執行完整前端測試套件確認沒有回歸**

Run: `cd frontend && npx vitest run`
Expected: 全部通過

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/HomePage.tsx
git commit -m "feat: show call-support button on home page when accessibility mode is on"
```

---

## Task 4: 端到端手動驗證

沒有新程式碼。CSS 視覺效果跟跨檔案的「開關→全站連動」行為沒辦法用這個專案現有的測試工具鏈自動驗證（vitest 用 jsdom，不會真的套用 index.css 的樣式層疊），所以用手動驗證收尾。

- [ ] **Step 1: 啟動前端**

Run: `cd frontend && npm run dev`

- [ ] **Step 2: 驗證開關與全站放大**

在瀏覽器打開首頁，點左上角管家頭像圖示展開選單，確認：
- 選單網格出現第 6 格，圖示是放大鏡、文字寫「無障礙模式」，跟前面 5 個顏色格子視覺上一致但不是色塊。
- 點擊它，全站文字與按鈕立即變大（不用重新整理頁面），選單本身也應該變大。
- 切換到別的頁面（如「我的服務」），確認放大效果有跨頁面持續套用。
- 重新整理瀏覽器，確認無障礙模式維持開啟狀態（讀取 localStorage 成功）。
- 再點一次同一格，確認能正確關閉、全站恢復原本字級。

- [ ] **Step 3: 驗證對比度**

開啟無障礙模式後，找一個原本用淺灰文字的地方（例如「我的服務」列表裡案件的次要說明文字），確認顏色變深、看起來更清楚。

- [ ] **Step 4: 驗證客服撥號按鈕**

回到首頁，確認無障礙模式開啟時「目前所有服務」卡片列表上方出現「撥打客服專線 0800-000-000」大按鈕；關閉無障礙模式後這顆按鈕應該消失。在手機瀏覽器或手機模擬模式下點擊，確認會觸發撥號（`tel:` 連結行為，桌機瀏覽器可能只會跳出詢問要用哪個應用程式撥打）。

- [ ] **Step 5: 記錄結果**

若任何一步行為與預期不符，回到對應任務修正並補測試（如果可以自動化的話），不要跳過直接修 patch。全部驗證通過後，本計畫視為完成。
