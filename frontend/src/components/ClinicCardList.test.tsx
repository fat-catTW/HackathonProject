import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ClinicCardList } from "./ClinicCardList";
import type { ClinicInfo } from "../types/clinic";

const clinics: ClinicInfo[] = [
  { id: "c1", name: "王耳鼻喉科診所", specialties: ["耳鼻喉科"], address: "台中市西屯區文心路100號", phone: "04-1111111", is_open_now: true },
  { id: "c2", name: "西屯家醫科診所", specialties: ["家醫科"], address: "台中市西屯區台灣大道99號", phone: "04-2222222", is_open_now: false },
];

describe("ClinicCardList", () => {
  it("renders every clinic's name and open/closed status", () => {
    render(
      <ClinicCardList clinics={clinics} selectedId={null} recommendedId={null} recommendReason={null} onSelect={vi.fn()} />,
    );
    expect(screen.getByText("王耳鼻喉科診所")).toBeInTheDocument();
    expect(screen.getByText(/現在有看診/)).toBeInTheDocument();
    expect(screen.getByText(/目前休診/)).toBeInTheDocument();
  });

  it("marks the AI-recommended clinic and shows its reason", () => {
    render(
      <ClinicCardList clinics={clinics} selectedId={null} recommendedId="c1" recommendReason="距離最近" onSelect={vi.fn()} />,
    );
    expect(screen.getByText("AI 推薦")).toBeInTheDocument();
    expect(screen.getByText("距離最近")).toBeInTheDocument();
  });

  it("calls onSelect with the clinic id when a card is clicked", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(
      <ClinicCardList clinics={clinics} selectedId={null} recommendedId={null} recommendReason={null} onSelect={onSelect} />,
    );
    await user.click(screen.getByText("西屯家醫科診所"));
    expect(onSelect).toHaveBeenCalledWith("c2");
  });
});
