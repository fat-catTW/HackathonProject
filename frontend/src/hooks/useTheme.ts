import { useCallback, useSyncExternalStore } from "react";

export interface ThemeDef {
  id: string;
  name: string;
  brand: string;
  brandDark: string;
  brandSoft: string;
  mascotHighlight: string;
}

export const THEMES: ThemeDef[] = [
  {
    id: "ocean",
    name: "深海藍",
    brand: "#0F4C81",
    brandDark: "#0A3A63",
    brandSoft: "#EAF1F8",
    mascotHighlight: "#F2A93B",
  },
  {
    id: "meadow",
    name: "暖夕綠",
    brand: "#2E9E5B",
    brandDark: "#1F6E3F",
    brandSoft: "#E5F4EB",
    mascotHighlight: "#F4C77A",
  },
  {
    id: "apricot",
    name: "暖陽杏",
    brand: "#D97A46",
    brandDark: "#B85F32",
    brandSoft: "#FBEEE1",
    mascotHighlight: "#FCE2C8",
  },
  {
    id: "blush",
    name: "淡粉泡泡",
    brand: "#B85C78",
    brandDark: "#8F435C",
    brandSoft: "#FBEAF0",
    mascotHighlight: "#F6D8C9",
  },
  {
    id: "twilight",
    name: "曙靖低光",
    brand: "#3B4A6B",
    brandDark: "#2B3550",
    brandSoft: "#E7EAF1",
    mascotHighlight: "#F2A93B",
  },
];

const DEFAULT_THEME_ID = THEMES[0].id;
const STORAGE_KEY = "ai-butler-theme";
const listeners = new Set<() => void>();

function readStoredId(): string {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored && THEMES.some((t) => t.id === stored) ? stored : DEFAULT_THEME_ID;
  } catch {
    return DEFAULT_THEME_ID;
  }
}

function applyToDocument(id: string) {
  if (typeof document !== "undefined") {
    document.documentElement.setAttribute("data-theme", id);
  }
}

let currentId = readStoredId();
applyToDocument(currentId);

function notify() {
  listeners.forEach((fn) => fn());
}

export function useTheme() {
  const themeId = useSyncExternalStore(
    (cb) => {
      listeners.add(cb);
      return () => listeners.delete(cb);
    },
    () => currentId,
  );

  const setTheme = useCallback((id: string) => {
    if (!THEMES.some((t) => t.id === id) || id === currentId) return;
    currentId = id;
    try {
      localStorage.setItem(STORAGE_KEY, id);
    } catch {
      /* ignore write failures (private browsing, quota) */
    }
    applyToDocument(id);
    notify();
  }, []);

  return {
    themeId,
    theme: THEMES.find((t) => t.id === themeId) ?? THEMES[0],
    themes: THEMES,
    setTheme,
  };
}
