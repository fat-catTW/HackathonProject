import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { DailyGreetingCard } from "./DailyGreetingCard";
import type { DailyGreeting } from "../api/greeting";

const navigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return { ...actual, useNavigate: () => navigate };
});

const CARD: DailyGreeting = {
  date: "2026-08-01",
  weekday: "星期六",
  date_label: "8 月 1 日 星期六",
  push_time: "07:00",
  period: "morning",
  greeting: "早安，王小明",
  headline: "今天有 2 件事要提醒你",
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
    {
      id: "REQ-DRAFT",
      kind: "action_needed",
      service_id: "home_cleaning",
      title: "還沒送出的居家清潔",
      detail: "填到一半的需求還留著，要接著完成嗎？",
      action_label: "繼續完成",
      action_path: "/requests/REQ-DRAFT",
    },
  ],
  suggestions: [
    { service_id: "air_conditioner_cleaning", label: "預約冷氣清洗", prompt: "我想預約冷氣清洗" },
  ],
};

function renderCard(card: DailyGreeting = CARD, onDismiss = vi.fn()) {
  navigate.mockClear();
  render(
    <MemoryRouter>
      <DailyGreetingCard card={card} onDismiss={onDismiss} />
    </MemoryRouter>,
  );
  return { onDismiss };
}

describe("DailyGreetingCard", () => {
  it("shows the greeting, the date and what the day looks like", () => {
    renderCard();

    expect(screen.getByRole("dialog", { name: "今日問候" })).toBeInTheDocument();
    expect(screen.getByText("早安，王小明")).toBeInTheDocument();
    expect(screen.getByText("8 月 1 日 星期六")).toBeInTheDocument();
    expect(screen.getByText("今天有 2 件事要提醒你")).toBeInTheDocument();
    expect(screen.getByText("今天 18:00 餐廳訂位")).toBeInTheDocument();
    expect(screen.getByText("22世紀風味館 · 已確認")).toBeInTheDocument();
  });

  it("tells the user this is the 07:00 daily push", () => {
    renderCard();

    expect(screen.getByText(/每天 07:00 為你整理/)).toBeInTheDocument();
  });

  it("opens the case behind a reminder and closes the card on the way", async () => {
    const user = userEvent.setup();
    const { onDismiss } = renderCard();

    await user.click(screen.getByText("今天 18:00 餐廳訂位"));

    expect(navigate).toHaveBeenCalledWith("/requests/REQ-RESV");
    // 導頁前先記下「今天看過了」，否則回到首頁又會再跳一次同一張卡。
    expect(onDismiss).toHaveBeenCalledTimes(1);
  });

  it("hands a suggestion straight to the butler as an opening message", async () => {
    const user = userEvent.setup();
    renderCard();

    await user.click(screen.getByText("預約冷氣清洗"));

    expect(navigate).toHaveBeenCalledWith("/new", {
      state: { autoMessage: "我想預約冷氣清洗" },
    });
  });

  it("closes from the acknowledge button, the close icon and the backdrop", async () => {
    const user = userEvent.setup();
    const { onDismiss } = renderCard();

    await user.click(screen.getByText("知道了"));
    await user.click(screen.getByRole("button", { name: "關閉" }));
    await user.click(screen.getByRole("button", { name: "關閉今日問候" }));

    expect(onDismiss).toHaveBeenCalledTimes(3);
  });

  it("stays useful on a day with nothing scheduled", () => {
    renderCard({
      ...CARD,
      headline: "今天沒有待辦，輕鬆一點",
      message: "今天沒有待辦，想到什麼隨時跟我說，我幫你安排。",
      items: [],
    });

    expect(screen.getByText("今天沒有待辦，輕鬆一點")).toBeInTheDocument();
    expect(screen.getByText("預約冷氣清洗")).toBeInTheDocument();
  });
});
