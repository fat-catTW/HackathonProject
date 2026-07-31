import { act, renderHook } from "@testing-library/react";
import fc from "fast-check";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ColorMode } from "./useColorMode";

const STORAGE_KEY = "ai-butler-color-mode";
const DOM_ATTRIBUTE = "data-color-mode";
const VALID_MODES: ColorMode[] = ["light", "dark"];

/** 重新載入模組，模擬「重新開啟頁面」並取得乾淨的模組層級狀態 */
async function importFreshHook() {
  vi.resetModules();
  const mod = await import("./useColorMode");
  return mod.useColorMode;
}

/** 生成器：只產生合法的 Color_Mode 值（constrain 到實際輸入空間） */
const colorModeArb = fc.constantFrom<ColorMode>(...VALID_MODES);

function other(mode: ColorMode): ColorMode {
  return mode === "light" ? "dark" : "light";
}

/** mode 恆屬合法集合，且 data-color-mode 與 mode 完全一致 */
function assertInvariants(mode: ColorMode) {
  expect(VALID_MODES).toContain(mode);
  expect(document.documentElement.getAttribute(DOM_ATTRIBUTE)).toBe(mode);
}

beforeEach(() => {
  localStorage.clear();
  document.documentElement.removeAttribute(DOM_ATTRIBUTE);
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("useColorMode property-based tests", () => {
  it("Property 1: 模式切換往返一致（Round trip）", async () => {
    await fc.assert(
      fc.asyncProperty(
        colorModeArb,
        fc.boolean(),
        fc.boolean(),
        async (initial, switchAwayViaToggle, switchBackViaToggle) => {
          localStorage.clear();
          localStorage.setItem(STORAGE_KEY, initial);
          document.documentElement.removeAttribute(DOM_ATTRIBUTE);

          const useColorMode = await importFreshHook();
          const { result, unmount } = renderHook(() => useColorMode());

          try {
            // 起始狀態
            expect(result.current.mode).toBe(initial);
            assertInvariants(result.current.mode);

            // 切到另一個模式（setMode 或 toggle 皆須有相同效果）
            const away = other(initial);
            act(() => {
              if (switchAwayViaToggle) {
                result.current.toggle();
              } else {
                result.current.setMode(away);
              }
            });

            expect(result.current.mode).toBe(away);
            assertInvariants(result.current.mode);

            // 再切回原模式 → 回到起始值
            act(() => {
              if (switchBackViaToggle) {
                result.current.toggle();
              } else {
                result.current.setMode(initial);
              }
            });

            expect(result.current.mode).toBe(initial);
            assertInvariants(result.current.mode);
          } finally {
            unmount();
          }
        },
      ),
      { numRuns: 100 },
    );
  });
});
describe("useColorMode property-based tests (persistence)", () => {
  /**
   * Property 2: 持久化寫入與讀取往返一致
   *
   * **Validates: Requirements 2.1, 2.2**
   */
  it("Property 2: 持久化寫入與讀取往返一致", async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.array(colorModeArb, { minLength: 1, maxLength: 6 }),
        async (writes) => {
          localStorage.clear();
          document.documentElement.removeAttribute(DOM_ATTRIBUTE);

          const written = writes[writes.length - 1];

          // 第一次「頁面生命週期」：依序寫入模式
          const useColorMode = await importFreshHook();
          const first = renderHook(() => useColorMode());

          try {
            for (const mode of writes) {
              act(() => {
                first.result.current.setMode(mode);
              });
            }

            expect(first.result.current.mode).toBe(written);
            assertInvariants(first.result.current.mode);
            // 生效模式變更時已寫入 Color_Mode_Storage_Key
            expect(localStorage.getItem(STORAGE_KEY)).toBe(written);
          } finally {
            first.unmount();
          }

          // 第二次「頁面生命週期」：重新初始化 hook，模擬重新載入頁面
          document.documentElement.removeAttribute(DOM_ATTRIBUTE);
          const useColorModeReloaded = await importFreshHook();
          const second = renderHook(() => useColorModeReloaded());

          try {
            expect(second.result.current.mode).toBe(written);
            assertInvariants(second.result.current.mode);
          } finally {
            second.unmount();
          }
        },
      ),
      { numRuns: 100 },
    );
  });
});

describe("useColorMode property-based tests (default resolution)", () => {
  /** 儲存值情境：key 不存在 / 存入任意非法字串（含空字串） / localStorage 讀寫拋錯 */
  type StorageScenario =
    | { kind: "absent" }
    | { kind: "invalidValue"; value: string }
    | { kind: "throws" };

  /** 任意字串，但排除合法的 Color_Mode 值，使 property 定義明確 */
  const invalidStoredValueArb = fc
    .oneof(
      fc.constant(""),
      fc.constant("  "),
      fc.constant("Light"),
      fc.constant("DARK"),
      fc.constant("null"),
      fc.constant("undefined"),
      fc.string(),
      fc.string({ unit: "grapheme" }),
      fc.json(),
    )
    .filter((value) => !VALID_MODES.includes(value as ColorMode));

  const storageScenarioArb = fc.oneof(
    fc.constant<StorageScenario>({ kind: "absent" }),
    invalidStoredValueArb.map<StorageScenario>((value) => ({
      kind: "invalidValue",
      value,
    })),
    fc.constant<StorageScenario>({ kind: "throws" }),
  );

  /** `prefers-color-scheme` 情境：不支援 matchMedia / 回傳任意 matches 值 */
  type MediaScenario = { kind: "absent" } | { kind: "stub"; matches: boolean };

  const mediaScenarioArb = fc.oneof(
    fc.constant<MediaScenario>({ kind: "absent" }),
    fc.boolean().map<MediaScenario>((matches) => ({ kind: "stub", matches })),
  );

  const originalMatchMedia = window.matchMedia;

  /** 以旗標控制 localStorage 是否拋錯（happy-dom 的 localStorage 是 Proxy，直接 spy 難以還原） */
  let storageThrows = false;
  const realGetItem = window.localStorage.getItem.bind(window.localStorage);
  const realSetItem = window.localStorage.setItem.bind(window.localStorage);

  function installStorageWrappers() {
    window.localStorage.getItem = (key: string) => {
      if (storageThrows) throw new Error("localStorage blocked");
      return realGetItem(key);
    };
    window.localStorage.setItem = (key: string, value: string) => {
      if (storageThrows) throw new Error("localStorage quota exceeded");
      realSetItem(key, value);
    };
  }

  function uninstallStorageWrappers() {
    storageThrows = false;
    window.localStorage.getItem = realGetItem;
    window.localStorage.setItem = realSetItem;
  }

  function applyStorageScenario(scenario: StorageScenario) {
    storageThrows = false;
    localStorage.clear();
    if (scenario.kind === "invalidValue") {
      localStorage.setItem(STORAGE_KEY, scenario.value);
    }
    if (scenario.kind === "throws") {
      storageThrows = true;
    }
  }

  function applyMediaScenario(scenario: MediaScenario) {
    if (scenario.kind === "absent") {
      // 模擬極舊瀏覽器不支援 matchMedia
      Reflect.deleteProperty(window, "matchMedia");
      return;
    }
    window.matchMedia = ((query: string) => ({
      matches: scenario.matches,
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    })) as unknown as typeof window.matchMedia;
  }

  /**
   * Property 3: 無效或缺失儲存值一律回退為預設模式
   *
   * **Validates: Requirements 2.3, 2.4, 2.5, 2.6**
   */
  it("Property 3: 無效或缺失儲存值一律回退為預設模式", async () => {
    installStorageWrappers();

    try {
      await fc.assert(
        fc.asyncProperty(
          storageScenarioArb,
          mediaScenarioArb,
          async (storageScenario, mediaScenario) => {
            document.documentElement.removeAttribute(DOM_ATTRIBUTE);
            applyStorageScenario(storageScenario);
            applyMediaScenario(mediaScenario);

            // 初始化過程本身不得拋出例外（髒資料、localStorage 封鎖、無 matchMedia）
            const useColorMode = await importFreshHook();
            const { result, unmount } = renderHook(() => useColorMode());

            try {
              // 恆為系統固定預設值 "light"，不受儲存的髒資料或 prefers-color-scheme 影響
              expect(result.current.mode).toBe("light");
              assertInvariants(result.current.mode);
            } finally {
              unmount();
              storageThrows = false;
              window.matchMedia = originalMatchMedia;
              localStorage.clear();
            }
          },
        ),
        { numRuns: 100 },
      );
    } finally {
      uninstallStorageWrappers();
      window.matchMedia = originalMatchMedia;
    }
  });
});

describe("useColorMode property-based tests (preference isolation)", () => {
  const A11Y_STORAGE_KEY = "ai-butler-a11y";
  const A11Y_DOM_ATTRIBUTE = "data-a11y";

  /** 交錯的操作序列：色彩模式操作與無障礙開關操作 */
  type Op =
    | { kind: "setMode"; mode: ColorMode }
    | { kind: "toggleMode" }
    | { kind: "toggleA11y" };

  const opArb = fc.oneof(
    colorModeArb.map<Op>((mode) => ({ kind: "setMode", mode })),
    fc.constant<Op>({ kind: "toggleMode" }),
    fc.constant<Op>({ kind: "toggleA11y" }),
  );

  /** 重新載入兩個 hook 模組，使兩者的模組層級狀態都從當前 localStorage 重新解析 */
  async function importFreshHooks() {
    vi.resetModules();
    const colorMod = await import("./useColorMode");
    const a11yMod = await import("./useAccessibilityMode");
    return { useColorMode: colorMod.useColorMode, useAccessibilityMode: a11yMod.useAccessibilityMode };
  }

  function readA11ySnapshot() {
    return {
      stored: localStorage.getItem(A11Y_STORAGE_KEY),
      attribute: document.documentElement.getAttribute(A11Y_DOM_ATTRIBUTE),
    };
  }

  function readColorModeSnapshot() {
    return {
      stored: localStorage.getItem(STORAGE_KEY),
      attribute: document.documentElement.getAttribute(DOM_ATTRIBUTE),
    };
  }

  /**
   * Property 4: 模式切換不影響其他既有偏好設定
   *
   * **Validates: Requirements 5.1, 5.2, 5.4**
   */
  it("Property 4: 模式切換不影響其他既有偏好設定", async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.boolean(),
        colorModeArb,
        fc.array(opArb, { minLength: 1, maxLength: 8 }),
        async (initialA11y, initialMode, ops) => {
          localStorage.clear();
          document.documentElement.removeAttribute(DOM_ATTRIBUTE);
          document.documentElement.removeAttribute(A11Y_DOM_ATTRIBUTE);
          localStorage.setItem(A11Y_STORAGE_KEY, String(initialA11y));
          localStorage.setItem(STORAGE_KEY, initialMode);

          const { useColorMode, useAccessibilityMode } = await importFreshHooks();
          const { result, unmount } = renderHook(() => ({
            color: useColorMode(),
            a11y: useAccessibilityMode(),
          }));

          try {
            // 兩套偏好各自從自己的 key 正確解析，互不干擾
            expect(result.current.color.mode).toBe(initialMode);
            expect(result.current.a11y.enabled).toBe(initialA11y);

            let expectedMode = initialMode;
            let expectedA11y = initialA11y;

            for (const op of ops) {
              if (op.kind === "toggleA11y") {
                // 無障礙偏好變更 → 色彩模式（記憶體、localStorage、data-color-mode）皆不得改動
                const colorBefore = readColorModeSnapshot();

                act(() => {
                  result.current.a11y.toggle();
                });
                expectedA11y = !expectedA11y;

                expect(result.current.a11y.enabled).toBe(expectedA11y);
                expect(readColorModeSnapshot()).toEqual(colorBefore);
                expect(result.current.color.mode).toBe(expectedMode);
              } else {
                // 色彩模式變更 → 無障礙偏好（記憶體、localStorage、data-a11y）皆不得改動
                const a11yBefore = readA11ySnapshot();

                act(() => {
                  if (op.kind === "toggleMode") {
                    result.current.color.toggle();
                  } else {
                    result.current.color.setMode(op.mode);
                  }
                });
                expectedMode = op.kind === "toggleMode" ? other(expectedMode) : op.mode;

                expect(result.current.color.mode).toBe(expectedMode);
                assertInvariants(result.current.color.mode);
                expect(readA11ySnapshot()).toEqual(a11yBefore);
                expect(result.current.a11y.enabled).toBe(expectedA11y);
              }
            }

            // 序列結束後，兩套偏好仍各自維持自己的最終值
            expect(result.current.color.mode).toBe(expectedMode);
            expect(localStorage.getItem(STORAGE_KEY)).toBe(expectedMode);
            expect(result.current.a11y.enabled).toBe(expectedA11y);
            expect(localStorage.getItem(A11Y_STORAGE_KEY)).toBe(String(expectedA11y));
            expect(document.documentElement.getAttribute(A11Y_DOM_ATTRIBUTE)).toBe(
              String(expectedA11y),
            );
          } finally {
            unmount();
          }
        },
      ),
      { numRuns: 100 },
    );
  });
});
