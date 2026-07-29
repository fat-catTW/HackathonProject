import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ReservationDatePicker } from "./ReservationDatePicker";

describe("ReservationDatePicker", () => {
  it("sets min to today and max to today+60 days", () => {
    const today = new Date(2026, 6, 29); // July 29, 2026 at local midnight
    render(<ReservationDatePicker value="" onChange={() => {}} today={today} />);
    const input = screen.getByLabelText("用餐日期") as HTMLInputElement;
    expect(input.min).toBe("2026-07-29");
    expect(input.max).toBe("2026-09-27");
  });

  it("calls onChange with the picked date", () => {
    const onChange = vi.fn();
    const today = new Date(2026, 6, 29); // July 29, 2026 at local midnight
    render(<ReservationDatePicker value="" onChange={onChange} today={today} />);
    const input = screen.getByLabelText("用餐日期") as HTMLInputElement;
    input.value = "2026-08-01";
    input.dispatchEvent(new Event("input", { bubbles: true }));
    expect(onChange).toHaveBeenCalledWith("2026-08-01");
  });
});
