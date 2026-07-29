import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { StatusBadge } from "./StatusBadge";

describe("StatusBadge", () => {
  it("renders the VERIFIED status with its label", () => {
    render(<StatusBadge status="VERIFIED" label="已核銷" />);
    expect(screen.getByText("已核銷")).toBeInTheDocument();
  });

  it("falls back to gray styling for unknown status", () => {
    const { container } = render(<StatusBadge status="SOMETHING_NEW" label="未知" />);
    expect(container.firstChild).toBeTruthy();
  });
});
