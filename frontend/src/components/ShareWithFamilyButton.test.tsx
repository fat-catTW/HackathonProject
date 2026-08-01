import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi, afterEach } from "vitest";
import { ShareWithFamilyButton } from "./ShareWithFamilyButton";

describe("ShareWithFamilyButton", () => {
  afterEach(() => {
    // @ts-expect-error test cleanup of a browser API that may not exist by default
    delete navigator.share;
    // @ts-expect-error test cleanup
    delete navigator.clipboard;
  });

  it("calls navigator.share when available", () => {
    const shareMock = vi.fn().mockResolvedValue(undefined);
    navigator.share = shareMock;

    render(<ShareWithFamilyButton text="水果訂好了，餐廳也訂好了。" />);
    fireEvent.click(screen.getByRole("button", { name: "分享給家人" }));

    expect(shareMock).toHaveBeenCalledWith({
      title: "AI 管家任務完成通知",
      text: "水果訂好了，餐廳也訂好了。",
    });
  });

  it("falls back to clipboard copy when navigator.share is unavailable", async () => {
    const writeTextMock = vi.fn().mockResolvedValue(undefined);
    // happy-dom defines navigator.clipboard as a getter-only accessor, so a
    // direct assignment throws; redefine the property instead.
    Object.defineProperty(navigator, "clipboard", {
      value: { writeText: writeTextMock },
      configurable: true,
    });

    render(<ShareWithFamilyButton text="水果訂好了。" />);
    fireEvent.click(screen.getByRole("button", { name: "分享給家人" }));

    expect(writeTextMock).toHaveBeenCalledWith("水果訂好了。");
    expect(await screen.findByText(/已複製訊息/)).toBeInTheDocument();
  });
});
