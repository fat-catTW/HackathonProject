import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ConfirmModal } from "./ConfirmModal";

describe("ConfirmModal", () => {
  it("renders nothing when closed", () => {
    const { container } = render(
      <ConfirmModal
        open={false}
        text="確定要取消嗎？"
        confirmLabel="確定取消"
        cancelLabel="再想想"
        onConfirm={() => {}}
        onCancel={() => {}}
      />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("shows the text and calls onConfirm/onCancel", async () => {
    const user = userEvent.setup();
    const onConfirm = vi.fn();
    const onCancel = vi.fn();
    render(
      <ConfirmModal
        open
        text="確定要取消這筆服務案件嗎？"
        confirmLabel="確定取消案件"
        cancelLabel="再想想"
        onConfirm={onConfirm}
        onCancel={onCancel}
      />,
    );
    expect(screen.getByText("確定要取消這筆服務案件嗎？")).toBeInTheDocument();
    await user.click(screen.getByText("確定取消案件"));
    expect(onConfirm).toHaveBeenCalledTimes(1);
    await user.click(screen.getByText("再想想"));
    expect(onCancel).toHaveBeenCalledTimes(1);
  });
});
