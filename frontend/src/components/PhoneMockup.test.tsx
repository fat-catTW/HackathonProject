import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { PhoneMockup } from "./PhoneMockup";

describe("PhoneMockup", () => {
  it("renders the frame with pure CSS: no iframe and no image asset", () => {
    const { container } = render(
      <PhoneMockup>
        <div>服務卡</div>
      </PhoneMockup>,
    );

    expect(container.querySelectorAll("iframe")).toHaveLength(0);
    expect(container.querySelectorAll("img")).toHaveLength(0);
    expect(container.querySelectorAll("svg")).toHaveLength(0);
  });

  it("renders children inside the screen area", () => {
    render(
      <PhoneMockup>
        <button type="button">預約</button>
      </PhoneMockup>,
    );

    expect(screen.getByRole("button", { name: "預約" })).toBeInTheDocument();
  });

  it("keeps every decorative part aria-hidden and non-interactive", () => {
    const { container } = render(<PhoneMockup>內容</PhoneMockup>);
    const decorations = container.querySelectorAll("span");

    expect(decorations.length).toBeGreaterThan(0);
    decorations.forEach((span) => {
      expect(span).toHaveAttribute("aria-hidden");
      expect(span.classList.contains("pointer-events-none")).toBe(true);
    });
  });

  it("merges the caller className onto the frame root", () => {
    const { container } = render(<PhoneMockup className="rotate-2">內容</PhoneMockup>);
    const root = container.firstElementChild as HTMLElement;

    expect(root.classList.contains("rotate-2")).toBe(true);
    expect(root.classList.contains("relative")).toBe(true);
  });
});
