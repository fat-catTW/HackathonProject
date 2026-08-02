import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { HomePage } from "./HomePage";
import type { DailyGreeting } from "../api/greeting";
import * as greetingApi from "../api/greeting";
import * as onboardingApi from "../api/onboarding";

vi.mock("../api/greeting");
vi.mock("../api/onboarding");

const CARD: DailyGreeting = {
  date: "2026-08-01",
  weekday: "星期六",
  date_label: "8 月 1 日 星期六",
  push_time: "07:00",
  period: "morning",
  greeting: "早安，王小明",
  headline: "今天有 1 件事要提醒你",
  message: "今天有安排，出門前記得再確認一次時間。",
  items: [
    {
      id: "REQ-RESV",
      kind: "today",
      service_id: "restaurant_reservation",
      title: "今天 18:00 餐廳訂位",
      detail: "22世紀風味館 · 已確認",
      action_label: "查看詳情",
      action_path: "/requests/REQ-RESV",
    },
  ],
  suggestions: [],
};

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(new Date(2026, 7, 1, 7, 0, 0));
  localStorage.clear();
  sessionStorage.clear();
  sessionStorage.setItem("assistant_token", "demo-token");
  sessionStorage.setItem("assistant_name", "王小明");
  vi.mocked(greetingApi.fetchDailyGreeting).mockResolvedValue(CARD);
  // 已完成新手導引：導引是全螢幕的，沒關掉的話問候卡不該（也不會）跳出來。
  vi.mocked(onboardingApi.fetchOnboardingStatus).mockResolvedValue({
    completed: true,
    version: 99,
  });
});

afterEach(() => {
  vi.useRealTimers();
  vi.resetModules();
});

function renderHome() {
  return render(
    <MemoryRouter>
      <HomePage />
    </MemoryRouter>,
  );
}

describe("HomePage 每日問候卡", () => {
  it("pops the greeting card as soon as the app is opened", async () => {
    renderHome();

    // 規格上這是早上 7 點的推播；Demo 版沒有排程，改成一進首頁就送到眼前。
    const dialog = await screen.findByRole("dialog", { name: "今日問候" });
    expect(dialog).toHaveTextContent("早安，王小明");
    expect(dialog).toHaveTextContent("今天 18:00 餐廳訂位");
  });

  it("closes on 知道了 and does not come back on the next visit that day", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    const { unmount } = renderHome();
    await screen.findByRole("dialog", { name: "今日問候" });

    await user.click(screen.getByText("知道了"));
    await waitFor(() =>
      expect(screen.queryByRole("dialog", { name: "今日問候" })).not.toBeInTheDocument(),
    );

    unmount();
    renderHome();
    await waitFor(() => expect(screen.getByText("熱門服務")).toBeInTheDocument());
    expect(screen.queryByRole("dialog", { name: "今日問候" })).not.toBeInTheDocument();
  });

  it("renders the home page normally when the greeting cannot be loaded", async () => {
    vi.mocked(greetingApi.fetchDailyGreeting).mockRejectedValue(new Error("offline"));
    renderHome();

    await waitFor(() => expect(greetingApi.fetchDailyGreeting).toHaveBeenCalled());
    expect(screen.queryByRole("dialog", { name: "今日問候" })).not.toBeInTheDocument();
    expect(screen.getByText("熱門服務")).toBeInTheDocument();
  });
});
