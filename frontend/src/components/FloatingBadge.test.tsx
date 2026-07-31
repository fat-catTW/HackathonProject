import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { FloatingBadge } from "./FloatingBadge";

/** ServiceIcon 是 `<svg>`（以 viewBox 辨識）；Mascot 現在是 `<img>`（以 src 辨識）。 */
const SERVICE_ICON_VIEWBOX = "0 0 24 24";
const MASCOT_SRC = "/images/ai-orb-icon.png";

function viewBoxes(container: HTMLElement) {
  return Array.from(container.querySelectorAll("svg")).map((svg) => svg.getAttribute("viewBox"));
}

describe("FloatingBadge", () => {
  it("composes GlassPanel and never blocks touch targets underneath", () => {
    const { container } = render(<FloatingBadge label="居家清潔" />);
    const root = container.firstElementChild as HTMLElement;

    expect(root.classList.contains("glass-panel")).toBe(true);
    expect(root.classList.contains("pointer-events-none")).toBe(true);
  });

  describe('variant="icon"', () => {
    it("is the default variant and renders a ServiceIcon when icon is given", () => {
      const { container } = render(<FloatingBadge label="居家清潔" icon="cleaning" caption="已確認" />);

      expect(viewBoxes(container)).toEqual([SERVICE_ICON_VIEWBOX]);
      expect(screen.getByText("居家清潔")).toBeInTheDocument();
      expect(screen.getByText("已確認")).toBeInTheDocument();
    });

    it("falls back to the Mascot when no icon is given", () => {
      const { container } = render(<FloatingBadge label="AI 管家" variant="icon" />);

      expect(viewBoxes(container)).toEqual([]);
      expect(container.querySelector(`img[src="${MASCOT_SRC}"]`)).not.toBeNull();
    });
  });

  describe('variant="avatar"', () => {
    it("renders the avatar image when avatarSrc is provided", () => {
      render(
        <FloatingBadge
          label="到府服務人員"
          variant="avatar"
          avatarSrc="/avatars/helper.jpg"
          avatarName="Mei Chen"
        />,
      );

      const img = screen.getByRole("img", { name: "Mei Chen" });
      expect(img).toHaveAttribute("src", "/avatars/helper.jpg");
      expect(screen.queryByTestId("floating-badge-initials")).not.toBeInTheDocument();
    });

    it("falls back to initials when the avatar image fails to load", () => {
      render(
        <FloatingBadge
          label="到府服務人員"
          variant="avatar"
          avatarSrc="/avatars/broken.jpg"
          avatarName="Mei Chen"
        />,
      );

      const img = screen.getByRole("img", { name: "Mei Chen" });
      fireEvent.error(img);

      // 破圖的 <img> 被移除，改以姓名縮寫色塊呈現，不留空白區塊。
      expect(screen.queryByRole("img", { name: "Mei Chen" })).not.toBeInTheDocument();
      expect(screen.getByTestId("floating-badge-initials")).toHaveTextContent("MC");
    });

    it("builds initials from a latin name and from a CJK name", () => {
      const latin = render(<FloatingBadge label="服務人員" variant="avatar" avatarName="Mei Chen" />);
      expect(screen.getByTestId("floating-badge-initials")).toHaveTextContent("MC");
      latin.unmount();

      render(<FloatingBadge label="長輩使用者" variant="avatar" avatarName="王小明" />);
      expect(screen.getByTestId("floating-badge-initials")).toHaveTextContent("王小");
    });

    it("falls back to the Mascot when neither avatarSrc nor avatarName is given", () => {
      const { container } = render(<FloatingBadge label="長輩使用者" variant="avatar" />);

      expect(screen.queryByTestId("floating-badge-initials")).not.toBeInTheDocument();
      expect(viewBoxes(container)).toEqual([]);
      expect(container.querySelector(`img[src="${MASCOT_SRC}"]`)).not.toBeNull();
    });
  });
});
