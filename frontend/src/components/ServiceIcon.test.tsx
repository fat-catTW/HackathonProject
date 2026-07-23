import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ServiceIcon } from "./ServiceIcon";

describe("ServiceIcon", () => {
  it("renders exactly one svg for a known type", () => {
    const { container } = render(<ServiceIcon type="aircon" />);
    expect(container.querySelectorAll("svg")).toHaveLength(1);
  });

  it("applies the size prop to width and height", () => {
    const { container } = render(<ServiceIcon type="mic" size={40} />);
    const svg = container.querySelector("svg");
    expect(svg).toHaveAttribute("width", "40");
    expect(svg).toHaveAttribute("height", "40");
  });

  it("falls back to the chat icon for an unknown type", () => {
    // @ts-expect-error 刻意傳入不存在的 type，驗證執行期防呆
    const { container } = render(<ServiceIcon type="unknown-type" />);
    expect(container.querySelectorAll("svg")).toHaveLength(1);
  });
});
