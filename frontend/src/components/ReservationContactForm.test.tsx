import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ReservationContactForm } from "./ReservationContactForm";

describe("ReservationContactForm", () => {
  it("renders current name and phone", () => {
    render(<ReservationContactForm name="王大明" phone="0912345678" onNameChange={() => {}} onPhoneChange={() => {}} />);
    expect(screen.getByLabelText("聯絡人姓名")).toHaveValue("王大明");
    expect(screen.getByLabelText("聯絡電話")).toHaveValue("0912345678");
  });

  it("calls onNameChange and onPhoneChange", async () => {
    const user = userEvent.setup();
    const onNameChange = vi.fn();
    render(<ReservationContactForm name="" phone="" onNameChange={onNameChange} onPhoneChange={() => {}} />);
    await user.type(screen.getByLabelText("聯絡人姓名"), "王");
    expect(onNameChange).toHaveBeenCalled();
  });

  it("shows the error message when provided", () => {
    render(
      <ReservationContactForm
        name=""
        phone="123"
        onNameChange={() => {}}
        onPhoneChange={() => {}}
        error="請輸入正確的手機號碼格式（09 開頭，共 10 碼）"
      />,
    );
    expect(screen.getByText("請輸入正確的手機號碼格式（09 開頭，共 10 碼）")).toBeInTheDocument();
  });
});
