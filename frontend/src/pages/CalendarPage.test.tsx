import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { CalendarPage } from "./CalendarPage";
import * as calendarApi from "../api/calendar";

describe("CalendarPage", () => {
  it("renders requests grouped by date", async () => {
    vi.spyOn(calendarApi, "getCalendar").mockResolvedValue({
      days: [
        {
          date: "2026-08-02",
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

    await waitFor(() => expect(screen.getByText("2026-08-02")).toBeInTheDocument());
    expect(screen.getByText("居家清潔")).toBeInTheDocument();
  });
});
