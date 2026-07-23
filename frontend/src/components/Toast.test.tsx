import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { Toast } from "./Toast";

describe("Toast", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders nothing when text is null", () => {
    const { container } = render(<Toast text={null} onHide={() => {}} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("renders the given text", () => {
    render(<Toast text="案件已成功建立" onHide={() => {}} />);
    expect(screen.getByText("案件已成功建立")).toBeInTheDocument();
  });

  it("calls onHide after the duration elapses", () => {
    vi.useFakeTimers();
    const onHide = vi.fn();
    render(<Toast text="已取消" onHide={onHide} durationMs={1000} />);
    expect(onHide).not.toHaveBeenCalled();
    vi.advanceTimersByTime(1000);
    expect(onHide).toHaveBeenCalledTimes(1);
  });
});
