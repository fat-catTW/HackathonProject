import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { CalendarPage } from "./CalendarPage";
import * as calendarApi from "../api/calendar";

describe("CalendarPage", () => {
  it("renders the current month as a grid and shows requests on their date", async () => {
    const today = new Date();
    const todayKey = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(
      today.getDate(),
    ).padStart(2, "0")}`;

    vi.spyOn(calendarApi, "getCalendar").mockResolvedValue({
      days: [
        {
          date: todayKey,
          items: [
            {
              request_id: "REQ-1",
              service_name: "居家清潔",
              status: "SUBMITTED",
              status_label: "等待廠商確認",
            },
          ],
        },
      ],
    });

    render(
      <MemoryRouter>
        <CalendarPage />
      </MemoryRouter>,
    );

    await waitFor(() => expect(screen.getByText("居家清潔")).toBeInTheDocument());
    // 週標題列使用一~日排列，確認以週一為每列第一欄
    expect(screen.getByText("一")).toBeInTheDocument();
    expect(screen.getByText("日")).toBeInTheDocument();
  });

  it("navigates between months", async () => {
    vi.spyOn(calendarApi, "getCalendar").mockResolvedValue({ days: [] });
    const today = new Date();

    render(
      <MemoryRouter>
        <CalendarPage />
      </MemoryRouter>,
    );

    await waitFor(() => expect(screen.getByLabelText("下個月")).toBeInTheDocument());

    fireEvent.click(screen.getByLabelText("下個月"));

    const next = new Date(today.getFullYear(), today.getMonth() + 1, 1);
    expect(screen.getByText(`${next.getFullYear()}年${next.getMonth() + 1}月`)).toBeInTheDocument();
  });
});
