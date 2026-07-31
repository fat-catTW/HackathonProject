import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Mascot } from "./Mascot";

/** 取出 Mascot 根 `<img>`。圖片為 `aria-hidden`，無法用 role 查詢。 */
function renderMascot(size?: number, className?: string) {
  const { container } = render(<Mascot size={size} className={className} />);
  const img = container.querySelector("img");
  if (!img) throw new Error("Mascot did not render an <img> element");
  return img;
}

describe("Mascot", () => {
  it("renders the shared AI orb icon from public/images", () => {
    const img = renderMascot();
    expect(img.getAttribute("src")).toBe("/images/ai-orb-icon.png");
    expect(img).toHaveAttribute("aria-hidden");
  });

  it("renders at the default size of 120 and honors an explicit size", () => {
    const defaultSize = renderMascot();
    expect(defaultSize.getAttribute("width")).toBe("120");
    expect(defaultSize.getAttribute("height")).toBe("120");

    const custom = renderMascot(48);
    expect(custom.getAttribute("width")).toBe("48");
    expect(custom.getAttribute("height")).toBe("48");
  });

  it("applies the className to the root img", () => {
    const img = renderMascot(undefined, "h-10 w-10 drop-shadow");
    expect(img.getAttribute("class")).toBe("h-10 w-10 drop-shadow");
  });

  it("ignores the deprecated tone prop and still renders the same icon", () => {
    const { container } = render(<Mascot tone="inverted" />);
    const img = container.querySelector("img");
    expect(img?.getAttribute("src")).toBe("/images/ai-orb-icon.png");
  });
});
