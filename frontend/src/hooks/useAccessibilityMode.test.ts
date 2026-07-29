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
