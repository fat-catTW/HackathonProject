import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AntiFraudTicker } from "./AntiFraudTicker";

describe("AntiFraudTicker", () => {
  it("renders the reminders inside a labelled region", () => {
    render(<AntiFraudTicker />);

    const region = screen.getByRole("region", { name: "防詐騙提醒" });
    expect(within(region).getAllByText(/165 反詐騙專線/)).not.toHaveLength(0);
  });

  it("hides the duplicated copy from screen readers so each tip is announced once", () => {
    render(<AntiFraudTicker />);

    const lists = screen.getByRole("region", { name: "防詐騙提醒" }).querySelectorAll("ul");
    expect(lists).toHaveLength(2);
    // 第二份只是為了讓捲動接縫看起來連續，內容跟第一份一模一樣。
    expect(lists[0].getAttribute("aria-hidden")).toBeNull();
    expect(lists[1].getAttribute("aria-hidden")).toBe("true");
    expect(lists[1].textContent).toBe(lists[0].textContent);
  });
});
