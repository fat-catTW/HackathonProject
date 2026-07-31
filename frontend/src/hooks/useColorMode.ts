import { useCallback, useSyncExternalStore } from "react";

export type ColorMode = "light" | "dark";

export interface UseColorModeResult {
  /** 目前生效的模式 */
  mode: ColorMode;
  /** 直接指定模式並持久化 */
  setMode: (mode: ColorMode) => void;
  /** 在 light/dark 間切換並持久化 */
  toggle: () => void;
}

const STORAGE_KEY = "ai-butler-color-mode";
const DOM_ATTRIBUTE = "data-color-mode";
/** 系統固定預設值，刻意不依賴 prefers-color-scheme */
const DEFAULT_MODE: ColorMode = "light";

const listeners = new Set<() => void>();

function isColorMode(value: unknown): value is ColorMode {
  return value === "light" || value === "dark";
}

function readStoredMode(): ColorMode {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    return isColorMode(stored) ? stored : DEFAULT_MODE;
  } catch {
    return DEFAULT_MODE;
  }
}

function writeStoredMode(mode: ColorMode) {
  try {
    localStorage.setItem(STORAGE_KEY, mode);
  } catch {
    /* ignore write failures (private browsing, quota) */
  }
}

function applyToDocument(mode: ColorMode) {
  if (typeof document !== "undefined") {
    document.documentElement.setAttribute(DOM_ATTRIBUTE, mode);
  }
}

let currentMode: ColorMode = readStoredMode();
applyToDocument(currentMode);

function notify() {
  listeners.forEach((fn) => fn());
}

function commit(mode: ColorMode) {
  const changed = mode !== currentMode;
  currentMode = mode;
  writeStoredMode(mode);
  applyToDocument(mode);
  if (changed) notify();
}

export function useColorMode(): UseColorModeResult {
  const mode = useSyncExternalStore(
    (cb) => {
      listeners.add(cb);
      return () => listeners.delete(cb);
    },
    () => currentMode,
  );

  const setMode = useCallback((next: ColorMode) => {
    if (!isColorMode(next)) return;
    commit(next);
  }, []);

  const toggle = useCallback(() => {
    commit(currentMode === "light" ? "dark" : "light");
  }, []);

  return { mode, setMode, toggle };
}
