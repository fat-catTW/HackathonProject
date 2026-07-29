import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ReservationSummaryCard } from "./ReservationSummaryCard";

const data = {
  restaurantName: "22世紀風味館 信義旗艦店",
  date: "2026-08-01",
  timeSlot: "午餐",
  specificTime: "12:30",
  people: 4,
  contactName: "王大明",
  phone: "0912345678",
  isPremium: false,
};

describe("ReservationSummaryCard", () => {
  it("renders every field with its label", () => {
    render(<ReservationSummaryCard data={data} onConfirm={() => {}} onEdit={() => {}} submitting={false} />);
    expect(screen.getByText(data.restaurantName)).toBeInTheDocument();
    expect(screen.getByText(data.contactName)).toBeInTheDocument();
    expect(screen.getByText(data.phone)).toBeInTheDocument();
    expect(screen.getByText("4")).toBeInTheDocument();
  });

  it("calls onConfirm on submit click", async () => {
    const user = userEvent.setup();
    const onConfirm = vi.fn();
    render(<ReservationSummaryCard data={data} onConfirm={onConfirm} onEdit={() => {}} submitting={false} />);
    await user.click(screen.getByText("確認送出"));
    expect(onConfirm).toHaveBeenCalledTimes(1);
  });

  it("calls onEdit on back click", async () => {
    const user = userEvent.setup();
    const onEdit = vi.fn();
    render(<ReservationSummaryCard data={data} onConfirm={() => {}} onEdit={onEdit} submitting={false} />);
    await user.click(screen.getByText("返回修改"));
    expect(onEdit).toHaveBeenCalledTimes(1);
  });

  it("disables the confirm button and shows a loading label while submitting", () => {
    render(<ReservationSummaryCard data={data} onConfirm={() => {}} onEdit={() => {}} submitting />);
    expect(screen.getByText("訂位處理中，請稍候")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /訂位處理中/ })).toBeDisabled();
  });
});
