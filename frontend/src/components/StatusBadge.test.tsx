import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { StatusBadge } from "./StatusBadge";

/** 取得徽章根元素的 className 字串。 */
function renderBadge(status: string, label: string): string {
  const { container } = render(<StatusBadge status={status} label={label} />);
  const badge = container.firstElementChild;
  expect(badge).toBeTruthy();
  return badge!.className;
}

describe("StatusBadge", () => {
  it("renders the VERIFIED status with its label", () => {
    render(<StatusBadge status="VERIFIED" label="已核銷" />);
    expect(screen.getByText("已核銷")).toBeInTheDocument();
  });

  it("falls back to the neutral token styling for unknown status", () => {
    const className = renderBadge("SOMETHING_NEW", "未知");
    expect(className).toContain("bg-[var(--color-canvas)]");
    expect(className).toContain("text-[var(--color-muted-foreground)]");
  });

  // Requirement 16.5：狀態同時以顏色與文字標籤傳達，不單靠顏色
  it("keeps the pill shape and pairs the colour dot with a text label", () => {
    const { container } = render(<StatusBadge status="CONFIRMED" label="已確認" />);
    const badge = container.firstElementChild!;
    expect(badge.className).toContain("rounded-full");
    expect(screen.getByText("已確認")).toBeInTheDocument();
    // 圓點為裝飾性、對輔助技術隱藏，語意由 label 承擔
    const dot = badge.querySelector("[aria-hidden]");
    expect(dot).toBeTruthy();
    expect(dot!.className).toContain("bg-current");
  });

  // Requirement 6.6：元件顏色一律引用語意狀態色 Token，不寫死色碼／固定色階
  it.each([
    ["SUBMITTED", "warning"],
    ["PENDING_PROVIDER", "warning"],
    ["CONFIRMED", "success"],
    ["IN_PROGRESS", "success"],
    ["COMPLETED", "info"],
    ["VERIFIED", "info"],
    ["FAILED", "danger"],
  ])("styles %s with the %s status tokens", (status, token) => {
    const className = renderBadge(status, "狀態");
    expect(className).toContain(`bg-[var(--color-${token}-soft)]`);
    expect(className).toContain(`text-[var(--color-${token})]`);
  });

  it("uses no hardcoded palette colours for any status", () => {
    const statuses = [
      "SUBMITTED",
      "PENDING_PROVIDER",
      "CONFIRMED",
      "IN_PROGRESS",
      "COMPLETED",
      "VERIFIED",
      "CANCELLED",
      "FAILED",
      "SOMETHING_NEW",
    ];
    for (const status of statuses) {
      const className = renderBadge(status, "狀態");
      expect(className).not.toMatch(/(?:bg|text)-(?:gray|slate|red|green|amber|blue)-\d{2,3}/);
      expect(className).not.toMatch(/#[0-9a-fA-F]{3,8}/);
    }
  });
});
