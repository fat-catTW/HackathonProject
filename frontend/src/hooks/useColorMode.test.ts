import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

async function importFreshHook() {
  vi.resetModules();
  const mod = await import("./useColorMode");
  return mod.useColorMode;
}

beforeEach(() => {
  localStorage.clear();
  document.documentElement.removeAttribute("data-color-mode");
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("useColorMode", () => {
  it("defaults to light when localStorage has no saved preference", async () => {
    const useColorMode = await importFreshHook();
    const { result } = renderHook(() => useColorMode());

    expect(result.current.mode).toBe("light");
    expect(document.documentElement.getAttribute("data-color-mode")).toBe("light");
  });

  it("reads a previously saved mode on load", async () => {
    localStorage.setItem("ai-butler-color-mode", "dark");
    const useColorMode = await importFreshHook();
    const { result } = renderHook(() => useColorMode());

    expect(result.current.mode).toBe("dark");
    expect(document.documentElement.getAttribute("data-color-mode")).toBe("dark");
  });

  it("falls back to light when the saved value is not a valid mode", async () => {
    localStorage.setItem("ai-butler-color-mode", "solarized");
    const useColorMode = await importFreshHook();
    const { result } = renderHook(() => useColorMode());

    expect(result.current.mode).toBe("light");
    expect(document.documentElement.getAttribute("data-color-mode")).toBe("light");
  });

  it("setMode() applies the mode, persists it, and updates the data-color-mode attribute", async () => {
    const useColorMode = await importFreshHook();
    const { result } = renderHook(() => useColorMode());

    act(() => {
      result.current.setMode("dark");
    });

    expect(result.current.mode).toBe("dark");
    expect(localStorage.getItem("ai-butler-color-mode")).toBe("dark");
    expect(document.documentElement.getAttribute("data-color-mode")).toBe("dark");

    act(() => {
      result.current.setMode("light");
    });

    expect(result.current.mode).toBe("light");
    expect(localStorage.getItem("ai-butler-color-mode")).toBe("light");
    expect(document.documentElement.getAttribute("data-color-mode")).toBe("light");
  });

  it("toggle() flips between light and dark, persisting each change", async () => {
    const useColorMode = await importFreshHook();
    const { result } = renderHook(() => useColorMode());
    expect(result.current.mode).toBe("light");

    act(() => {
      result.current.toggle();
    });

    expect(result.current.mode).toBe("dark");
    expect(localStorage.getItem("ai-butler-color-mode")).toBe("dark");
    expect(document.documentElement.getAttribute("data-color-mode")).toBe("dark");

    act(() => {
      result.current.toggle();
    });

    expect(result.current.mode).toBe("light");
    expect(localStorage.getItem("ai-butler-color-mode")).toBe("light");
    expect(document.documentElement.getAttribute("data-color-mode")).toBe("light");
  });

  it("falls back to light when reading localStorage throws", async () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("localStorage blocked");
    });

    const useColorMode = await importFreshHook();
    const { result } = renderHook(() => useColorMode());

    expect(result.current.mode).toBe("light");
    expect(document.documentElement.getAttribute("data-color-mode")).toBe("light");
  });

  it("keeps working from in-memory state when writing to localStorage throws", async () => {
    const useColorMode = await importFreshHook();
    const { result } = renderHook(() => useColorMode());

    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("quota exceeded");
    });

    expect(() => {
      act(() => {
        result.current.setMode("dark");
      });
    }).not.toThrow();

    expect(result.current.mode).toBe("dark");
    expect(document.documentElement.getAttribute("data-color-mode")).toBe("dark");
  });

  it("initialises with the default mode when matchMedia is unavailable", async () => {
    const originalMatchMedia = window.matchMedia;
    // @ts-expect-error simulate a browser without matchMedia support
    delete window.matchMedia;

    try {
      const useColorMode = await importFreshHook();
      const { result } = renderHook(() => useColorMode());

      expect(window.matchMedia).toBeUndefined();
      expect(result.current.mode).toBe("light");
      expect(document.documentElement.getAttribute("data-color-mode")).toBe("light");
    } finally {
      window.matchMedia = originalMatchMedia;
    }
  });
});
