import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { GlassPanel } from "./GlassPanel";

describe("GlassPanel", () => {
  it("applies the glass-panel class so the shared 玻璃擬態 styles take effect", () => {
    const { container } = render(<GlassPanel>內容</GlassPanel>);
    const root = container.firstElementChild as HTMLElement;

    expect(root.tagName).toBe("DIV");
    expect(root.classList.contains("glass-panel")).toBe(true);
  });

  it("keeps glass-panel while merging the caller className", () => {
    const { container } = render(<GlassPanel className="rounded-2xl p-4">內容</GlassPanel>);
    const root = container.firstElementChild as HTMLElement;

    expect(root.classList.contains("glass-panel")).toBe(true);
    expect(root.classList.contains("rounded-2xl")).toBe(true);
    expect(root.classList.contains("p-4")).toBe(true);
  });

  it("renders children and spreads extra div attributes", () => {
    render(
      <GlassPanel data-testid="panel" aria-label="摘要">
        <p>摘要內容</p>
      </GlassPanel>,
    );

    const root = screen.getByTestId("panel");
    expect(root).toHaveAttribute("aria-label", "摘要");
    expect(screen.getByText("摘要內容")).toBeInTheDocument();
  });

  it("holds no hardcoded inline color, leaving Light/Dark parameters to CSS", () => {
    const { container } = render(<GlassPanel>內容</GlassPanel>);
    const root = container.firstElementChild as HTMLElement;

    expect(root.getAttribute("style")).toBeNull();
  });
});
