import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { PremiumToggle } from "./PremiumToggle";

describe("PremiumToggle", () => {
  it("renders both options with explanatory text", () => {
    render(<PremiumToggle value={null} onChange={() => {}} />);
    expect(screen.getByText("是，我要指定/高級訂位")).toBeInTheDocument();
    expect(screen.getByText("否，一般訂位即可")).toBeInTheDocument();
    expect(screen.getByText(/專人為您安排指定餐廳或特殊座位需求/)).toBeInTheDocument();
  });

  it("calls onChange(true) for premium option", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<PremiumToggle value={null} onChange={onChange} />);
    await user.click(screen.getByText("是，我要指定/高級訂位"));
    expect(onChange).toHaveBeenCalledWith(true);
  });

  it("calls onChange(false) for standard option", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<PremiumToggle value={null} onChange={onChange} />);
    await user.click(screen.getByText("否，一般訂位即可"));
    expect(onChange).toHaveBeenCalledWith(false);
  });
});
