import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { PeopleCounter } from "./PeopleCounter";

describe("PeopleCounter", () => {
  it("shows the current value", () => {
    render(<PeopleCounter value={2} onChange={() => {}} />);
    expect(screen.getByText("2")).toBeInTheDocument();
  });

  it("increments on plus click", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<PeopleCounter value={2} onChange={onChange} />);
    await user.click(screen.getByLabelText("增加人數"));
    expect(onChange).toHaveBeenCalledWith(3);
  });

  it("decrements on minus click", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<PeopleCounter value={2} onChange={onChange} />);
    await user.click(screen.getByLabelText("減少人數"));
    expect(onChange).toHaveBeenCalledWith(1);
  });

  it("disables minus button at the lower bound", () => {
    render(<PeopleCounter value={1} onChange={() => {}} />);
    expect(screen.getByLabelText("減少人數")).toBeDisabled();
  });

  it("disables plus button at the upper bound", () => {
    render(<PeopleCounter value={20} onChange={() => {}} />);
    expect(screen.getByLabelText("增加人數")).toBeDisabled();
  });
});
