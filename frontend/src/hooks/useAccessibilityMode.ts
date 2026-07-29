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
