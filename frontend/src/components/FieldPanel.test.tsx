import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { FieldPanel } from "./FieldPanel";

describe("FieldPanel", () => {
  it("renders a chip per collected field with its label and value", () => {
    render(<FieldPanel collected={{ quantity: 2 }} missing={["address"]} />);
    expect(screen.getByText("數量：2")).toBeInTheDocument();
  });

  it("renders a dashed chip per missing field", () => {
    render(<FieldPanel collected={{}} missing={["address", "phone"]} />);
    expect(screen.getByText("服務地址")).toBeInTheDocument();
    expect(screen.getByText("聯絡電話")).toBeInTheDocument();
  });

  it("renders nothing when there are no collected and no missing fields", () => {
    const { container } = render(<FieldPanel collected={{}} missing={[]} />);
    expect(container).toBeEmptyDOMElement();
  });
});
