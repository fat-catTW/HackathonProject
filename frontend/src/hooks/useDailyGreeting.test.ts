import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { DailyGreeting } from "../api/greeting";

const fetchDailyGreeting = vi.fn();
vi.mock("../api/greeting", () => ({ fetchDailyGreeting: (d: string) => fetchDailyGreeting(d) }));

const CARD: DailyGreeting = {
  date: "2026-08-01",
  weekday: "星期六",
  date_label: "8 月 1 日 星期六",
  push_time: "07:00",
  period: "morning",
  greeting: "早安，王小明",
  headline: "今天沒有待辦，輕鬆一點",
  message: "想到什麼隨時跟我說。",
  items: [],
  suggestions: [],
};

const SEEN_KEY = "ai-butler-daily-greeting-seen";

async function importFreshHook() {
  vi.resetModules();
  return (await import("./useDailyGreeting")).useDailyGreeting;
}

beforeEach(() => {
  // 只假造 Date（不動 setTimeout，waitFor 才能正常跑）：這組測試全都在
  // 「卡片上的日期 vs 已看過的日期」上打轉，日期不能跟著跑測試的當天飄。
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(new Date(2026, 7, 1, 7, 0, 0));
  localStorage.clear();
  sessionStorage.clear();
  sessionStorage.setItem("assistant_token", "demo-token");
  fetchDailyGreeting.mockReset().mockResolvedValue(CARD);
});

afterEach(() => {
  vi.useRealTimers();
});

describe("useDailyGreeting", () => {
  it("fetches today's card with the device's local date and shows it", async () => {
    const useDailyGreeting = await importFreshHook();
    const { result } = renderHook(() => useDailyGreeting());

    await waitFor(() => expect(result.current.card).toEqual(CARD));
    // 用裝置當地日期，不是 UTC：台灣半夜 0–8 點用 UTC 會退回前一天。
    expect(fetchDailyGreeting).toHaveBeenCalledWith("2026-08-01");
    expect(result.current.shouldShow).toBe(true);
  });

  it("only pops once a day — dismissing it keeps it shut on the next visit", async () => {
    const useDailyGreeting = await importFreshHook();
    const first = renderHook(() => useDailyGreeting());
    await waitFor(() => expect(first.result.current.shouldShow).toBe(true));

    act(() => first.result.current.dismiss());
    expect(first.result.current.shouldShow).toBe(false);
    expect(localStorage.getItem(SEEN_KEY)).toBe("2026-08-01");

    // 重新載入 App（模組重載）後，同一天不該再跳一次。
    const useDailyGreetingAgain = await importFreshHook();
    const second = renderHook(() => useDailyGreetingAgain());
    await waitFor(() => expect(second.result.current.card).toEqual(CARD));
    expect(second.result.current.shouldShow).toBe(false);
  });

  it("pops again once the date rolls over", async () => {
    localStorage.setItem(SEEN_KEY, "2026-07-31");
    const useDailyGreeting = await importFreshHook();
    const { result } = renderHook(() => useDailyGreeting());

    await waitFor(() => expect(result.current.shouldShow).toBe(true));
  });

  it("reopen() brings today's card back after it was dismissed", async () => {
    localStorage.setItem(SEEN_KEY, CARD.date);
    const useDailyGreeting = await importFreshHook();
    const { result } = renderHook(() => useDailyGreeting());
    await waitFor(() => expect(result.current.card).toEqual(CARD));
    expect(result.current.shouldShow).toBe(false);

    act(() => result.current.reopen());
    expect(result.current.shouldShow).toBe(true);

    act(() => result.current.dismiss());
    expect(result.current.shouldShow).toBe(false);
  });

  it("stays quiet when logged out", async () => {
    sessionStorage.clear();
    const useDailyGreeting = await importFreshHook();
    const { result } = renderHook(() => useDailyGreeting());

    expect(fetchDailyGreeting).not.toHaveBeenCalled();
    expect(result.current.shouldShow).toBe(false);
  });

  it("fails silently — a broken greeting must not block the home page", async () => {
    fetchDailyGreeting.mockRejectedValue(new Error("offline"));
    const useDailyGreeting = await importFreshHook();
    const { result } = renderHook(() => useDailyGreeting());

    await waitFor(() => expect(fetchDailyGreeting).toHaveBeenCalled());
    expect(result.current.card).toBeNull();
    expect(result.current.shouldShow).toBe(false);
  });
});
