import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ClinicSummaryCard } from "./ClinicSummaryCard";

const data = {
  clinicName: "王耳鼻喉科診所",
  clinicAddress: "台中市西屯區文心路100號",
  date: "2026-08-02",
  time: "15:00",
  symptomNote: "咳嗽、喉嚨癢",
  contactName: "王添財",
  phone: "0912345678",
};

describe("ClinicSummaryCard", () => {
  it("renders every field from the summary data", () => {
    render(<ClinicSummaryCard data={data} onConfirm={vi.fn()} onEdit={vi.fn()} submitting={false} />);
    expect(screen.getByText("王耳鼻喉科診所")).toBeInTheDocument();
    expect(screen.getByText("咳嗽、喉嚨癢")).toBeInTheDocument();
    expect(screen.getByText("王添財")).toBeInTheDocument();
  });

  it("calls onConfirm when the confirm button is clicked", async () => {
    const user = userEvent.setup();
    const onConfirm = vi.fn();
    render(<ClinicSummaryCard data={data} onConfirm={onConfirm} onEdit={vi.fn()} submitting={false} />);
    await user.click(screen.getByRole("button", { name: "確認掛號" }));
    expect(onConfirm).toHaveBeenCalledTimes(1);
  });

  it("disables both buttons while submitting", () => {
    render(<ClinicSummaryCard data={data} onConfirm={vi.fn()} onEdit={vi.fn()} submitting={true} />);
    expect(screen.getByRole("button", { name: /掛號處理中/ })).toBeDisabled();
    expect(screen.getByRole("button", { name: "返回修改" })).toBeDisabled();
  });
});
