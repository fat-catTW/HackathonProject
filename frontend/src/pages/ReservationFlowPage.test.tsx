import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { ReservationFlowPage } from "./ReservationFlowPage";
import * as reservationsApi from "../api/reservations";

vi.mock("../api/reservations");

const restaurants = [
  { id: "r001", name: "22世紀風味館 信義旗艦店", brand: "b", address: "台北市信義區松高路12號3樓", phone: "02-2723-0022", cuisine: "c", supports_booking_api: true },
];

function renderPage() {
  return render(
    <MemoryRouter>
      <ReservationFlowPage />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.mocked(reservationsApi.listRestaurants).mockResolvedValue(restaurants);
});

describe("ReservationFlowPage", () => {
  it("shows only the restaurant selection step first", async () => {
    renderPage();
    expect(await screen.findByText("22世紀風味館 信義旗艦店")).toBeInTheDocument();
    expect(screen.queryByLabelText("用餐日期")).not.toBeInTheDocument();
  });

  it("advances to the date step after picking a restaurant, and preserves the pick when going back", async () => {
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByText("22世紀風味館 信義旗艦店"));
    await user.click(screen.getByText("下一步"));

    expect(screen.getByLabelText("用餐日期")).toBeInTheDocument();
    expect(screen.queryByText("22世紀風味館 信義旗艦店")).not.toBeInTheDocument();

    await user.click(screen.getByText("上一步"));
    // RestaurantCard's accessible name concatenates name + address + phone (Task 12,
    // pre-existing component), so match by prefix rather than exact restaurant name.
    expect(screen.getByRole("button", { name: /^22世紀風味館 信義旗艦店/ })).toHaveAttribute("aria-pressed", "true");
  });

  it("disables the submit button immediately after clicking it to block double submission", async () => {
    vi.mocked(reservationsApi.submitReservation).mockImplementation(
      () => new Promise(() => {}), // never resolves, simulate in-flight request
    );
    const user = userEvent.setup();
    renderPage();

    await user.click(await screen.findByText("22世紀風味館 信義旗艦店"));
    await user.click(screen.getByText("下一步"));
    await user.type(screen.getByLabelText("用餐日期"), "2026-08-01");
    await user.click(screen.getByText("下一步"));
    await user.click(screen.getByText("午餐（11:00–14:00）"));
    await user.click(screen.getByText("12:00"));
    await user.click(screen.getByText("下一步"));
    await user.click(screen.getByText("下一步")); // people, default 2
    await user.type(screen.getByLabelText("聯絡人姓名"), "王大明");
    await user.type(screen.getByLabelText("聯絡電話"), "0912345678");
    await user.click(screen.getByText("下一步"));
    await user.click(screen.getByText("否，一般訂位即可"));
    await user.click(screen.getByText("下一步"));

    const confirmButton = screen.getByText("確認送出");
    await user.click(confirmButton);

    expect(screen.getByRole("button", { name: /訂位處理中/ })).toBeDisabled();
  });
});
