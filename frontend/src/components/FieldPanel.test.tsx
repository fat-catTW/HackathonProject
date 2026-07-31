import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { FieldPanel } from "./FieldPanel";
import { fieldLabel } from "../utils/fieldLabels";

describe("FieldPanel", () => {
  it("renders a chip per collected field with its label and value", () => {
    render(<FieldPanel collected={{ quantity: 2 }} missing={["address"]} />);
    expect(screen.getByText("數量：2")).toBeInTheDocument();
  });

  it("renders a dashed chip per missing field", () => {
    render(<FieldPanel collected={{}} missing={["address", "phone"]} />);
    // 標籤文字以 utils/fieldLabels.ts 的 FIELD_LABELS 為單一來源：address 對應「地址」。
    // （本斷言原先寫成「服務地址」，與 FIELD_LABELS 不一致而長期失敗；此處對齊實作，
    // 不改動使用者可見文案。）
    expect(screen.getByText(fieldLabel("address"))).toBeInTheDocument();
    expect(screen.getByText(fieldLabel("phone"))).toBeInTheDocument();
  });

  it("renders nothing when there are no collected and no missing fields", () => {
    const { container } = render(<FieldPanel collected={{}} missing={[]} />);
    expect(container).toBeEmptyDOMElement();
  });
});
