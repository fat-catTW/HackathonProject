import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { TimeSlotSelector } from "./TimeSlotSelector";

describe("TimeSlotSelector", () => {
  it("renders lunch and dinner buttons", () => {
    render(<TimeSlotSelector slot={null} specificTime={null} onSlotChange={() => {}} onTimeChange={() => {}} />);
    expect(screen.getByText("午餐（11:00–14:00）")).toBeInTheDocument();
    expect(screen.getByText("晚餐（17:00–21:00）")).toBeInTheDocument();
  });

  it("calls onSlotChange when a slot is picked", async () => {
    const user = userEvent.setup();
    const onSlotChange = vi.fn();
    render(<TimeSlotSelector slot={null} specificTime={null} onSlotChange={onSlotChange} onTimeChange={() => {}} />);
    await user.click(screen.getByText("午餐（11:00–14:00）"));
    expect(onSlotChange).toHaveBeenCalledWith("LUNCH");
  });

  it("shows 30-minute time options only after a slot is picked", () => {
    render(<TimeSlotSelector slot="LUNCH" specificTime={null} onSlotChange={() => {}} onTimeChange={() => {}} />);
    expect(screen.getByText("11:00")).toBeInTheDocument();
    expect(screen.getByText("13:30")).toBeInTheDocument();
    expect(screen.queryByText("14:00")).not.toBeInTheDocument();
  });

  it("calls onTimeChange when a specific time is picked", async () => {
    const user = userEvent.setup();
    const onTimeChange = vi.fn();
    render(<TimeSlotSelector slot="DINNER" specificTime={null} onSlotChange={() => {}} onTimeChange={onTimeChange} />);
    await user.click(screen.getByText("18:00"));
    expect(onTimeChange).toHaveBeenCalledWith("18:00");
  });
});
