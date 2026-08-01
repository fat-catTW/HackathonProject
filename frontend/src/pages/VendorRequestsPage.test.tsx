import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { VendorRequestItem } from "../types/vendor";

const ITEMS: VendorRequestItem[] = [
  {
    request_id: "REQ-1001",
    service_id: "plumbing_repair",
    service_name: "水電修繕",
    status: "PENDING_PROVIDER",
    status_label: "待確認",
    customer_name: "陳阿姨",
    summary: "廚房水龍頭漏水",
    version: 1,
    available_actions: ["accept", "reject"],
    created_at: "2026-07-30T01:00:00Z",
    updated_at: "2026-07-30T01:00:00Z",
  },
  {
    request_id: "REQ-1002",
    service_id: "home_cleaning",
    service_name: "居家清潔",
    status: "PENDING_PROVIDER",
    status_label: "待確認",
    customer_name: "林先生",
    summary: "客廳地板清潔",
    version: 1,
    available_actions: ["accept", "reject"],
    created_at: "2026-07-29T01:00:00Z",
    updated_at: "2026-07-29T01:00:00Z",
  },
  {
    request_id: "REQ-1003",
    service_id: "home_cleaning",
    service_name: "居家清潔",
    status: "PENDING_PROVIDER",
    status_label: "待確認",
    customer_name: "王小姐",
    summary: "浴室清潔",
    version: 1,
    available_actions: ["accept", "reject"],
    created_at: "2026-07-28T01:00:00Z",
    updated_at: "2026-07-28T01:00:00Z",
  },
];

vi.mock("../api/vendor", () => ({
  listVendorRequests: vi.fn(async () => ({
    items: ITEMS,
    counts: { pending: 3, orders: 0, all: 3 },
  })),
}));

import { VendorRequestsPage } from "./VendorRequestsPage";
import * as vendorApi from "../api/vendor";

function renderPage() {
  return render(
    <MemoryRouter>
      <VendorRequestsPage />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  localStorage.setItem("vendor-token", "test-token");
  localStorage.setItem("vendor-name", "示範水電行");
  vi.mocked(vendorApi.listVendorRequests).mockResolvedValue({
    items: ITEMS,
    counts: { pending: 3, orders: 0, all: 3 },
  });
});

function categoryGroup() {
  return within(screen.getByRole("group", { name: "服務種類篩選" }));
}

describe("VendorRequestsPage 分類與搜尋", () => {
  it("shows a service category chip per distinct service in the current tab, plus 全部", async () => {
    renderPage();
    await waitFor(() => expect(screen.getByText("REQ-1001")).toBeInTheDocument());

    const group = categoryGroup();
    expect(group.getByRole("button", { name: /全部/ })).toHaveTextContent("3");
    expect(group.getByRole("button", { name: /居家清潔/ })).toHaveTextContent("2");
    expect(group.getByRole("button", { name: /水電修繕/ })).toHaveTextContent("1");
  });

  it("filters the request list when a service category chip is clicked", async () => {
    const user = userEvent.setup();
    renderPage();
    await waitFor(() => expect(screen.getByText("REQ-1001")).toBeInTheDocument());

    await user.click(categoryGroup().getByRole("button", { name: /水電修繕/ }));

    expect(screen.getByText("REQ-1001")).toBeInTheDocument();
    expect(screen.queryByText("REQ-1002")).not.toBeInTheDocument();
    expect(screen.queryByText("REQ-1003")).not.toBeInTheDocument();
  });

  it("filters the request list by search text across service, customer and request id", async () => {
    const user = userEvent.setup();
    renderPage();
    await waitFor(() => expect(screen.getByText("REQ-1001")).toBeInTheDocument());

    await user.type(screen.getByLabelText("搜尋案件編號、客戶或服務"), "陳阿姨");

    expect(screen.getByText("REQ-1001")).toBeInTheDocument();
    expect(screen.queryByText("REQ-1002")).not.toBeInTheDocument();
  });

  it("resets the category filter back to 全部 when switching status tabs to one without that category", async () => {
    const user = userEvent.setup();
    vi.mocked(vendorApi.listVendorRequests).mockImplementation(async (scope) => {
      if (scope === "orders") {
        return { items: [ITEMS[0]], counts: { pending: 3, orders: 1, all: 4 } };
      }
      return { items: ITEMS, counts: { pending: 3, orders: 0, all: 3 } };
    });
    renderPage();
    await waitFor(() => expect(screen.getByText("REQ-1001")).toBeInTheDocument());

    await user.click(categoryGroup().getByRole("button", { name: /居家清潔/ }));
    expect(categoryGroup().getByRole("button", { name: /居家清潔/ })).toHaveAttribute(
      "aria-pressed",
      "true",
    );

    await user.click(screen.getByRole("button", { name: /已接訂單/ }));
    await waitFor(() =>
      expect(categoryGroup().queryByRole("button", { name: /居家清潔/ })).not.toBeInTheDocument(),
    );
    expect(categoryGroup().getByRole("button", { name: /全部/ })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });
});
