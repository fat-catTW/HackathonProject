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
  getVendorRequest: vi.fn(),
  actOnVendorRequest: vi.fn(),
  revealVendorContact: vi.fn(),
}));

vi.mock("../api/vendorTags", () => ({
  listVendorCaseTags: vi.fn(async () => ({ tags: {} })),
  getVendorCaseTags: vi.fn(),
  saveVendorCaseTags: vi.fn(),
}));

import { VendorRequestsPage } from "./VendorRequestsPage";
import * as vendorApi from "../api/vendor";
import * as vendorTagsApi from "../api/vendorTags";

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
  vi.mocked(vendorTagsApi.listVendorCaseTags).mockResolvedValue({ tags: {} });
});

function categoryGroup() {
  return within(screen.getByRole("group", { name: "服務種類篩選" }));
}

function tagGroup() {
  return within(screen.getByRole("group", { name: "標籤篩選" }));
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

describe("VendorRequestsPage 案件標籤", () => {
  const TAGS = { "REQ-1001": ["急件", "待報價"], "REQ-1003": ["急件"] };

  beforeEach(() => {
    vi.mocked(vendorTagsApi.listVendorCaseTags).mockResolvedValue({ tags: TAGS });
  });

  it("shows each case's tags on its card", async () => {
    renderPage();
    const card = (await screen.findByText("REQ-1001")).closest("a") as HTMLElement;

    expect(within(card).getByText("急件")).toBeInTheDocument();
    expect(within(card).getByText("待報價")).toBeInTheDocument();
  });

  it("offers one filter chip per tag in use, counting the cases that carry it", async () => {
    renderPage();
    await waitFor(() => expect(screen.getByRole("group", { name: "標籤篩選" })).toBeInTheDocument());

    expect(tagGroup().getByRole("button", { name: /急件/ })).toHaveTextContent("2");
    expect(tagGroup().getByRole("button", { name: /待報價/ })).toHaveTextContent("1");
    // 沒人貼過的預設標籤不佔位置，避免點下去是空的。
    expect(tagGroup().queryByRole("button", { name: /大型案件/ })).not.toBeInTheDocument();
  });

  it("filters the list down to the cases carrying the selected tag", async () => {
    const user = userEvent.setup();
    renderPage();
    await waitFor(() => expect(screen.getByRole("group", { name: "標籤篩選" })).toBeInTheDocument());

    await user.click(tagGroup().getByRole("button", { name: /待報價/ }));

    expect(screen.getByText("REQ-1001")).toBeInTheDocument();
    expect(screen.queryByText("REQ-1002")).not.toBeInTheDocument();
    expect(screen.queryByText("REQ-1003")).not.toBeInTheDocument();
  });

  it("combines the tag filter with the service category filter", async () => {
    const user = userEvent.setup();
    renderPage();
    await waitFor(() => expect(screen.getByRole("group", { name: "標籤篩選" })).toBeInTheDocument());

    await user.click(tagGroup().getByRole("button", { name: /急件/ }));
    await user.click(categoryGroup().getByRole("button", { name: /居家清潔/ }));

    // 急件有 1001／1003，居家清潔有 1002／1003，兩個條件同時成立的只有 1003。
    expect(screen.getByText("REQ-1003")).toBeInTheDocument();
    expect(screen.queryByText("REQ-1001")).not.toBeInTheDocument();
    expect(screen.queryByText("REQ-1002")).not.toBeInTheDocument();
  });

  it("finds cases by typing a tag into the search box", async () => {
    const user = userEvent.setup();
    renderPage();
    await waitFor(() => expect(screen.getByText("REQ-1001")).toBeInTheDocument());

    await user.type(screen.getByLabelText("搜尋案件編號、客戶或服務"), "待報價");

    expect(screen.getByText("REQ-1001")).toBeInTheDocument();
    expect(screen.queryByText("REQ-1003")).not.toBeInTheDocument();
  });

  it("falls back to a tagless list when the tag lookup fails, instead of failing the whole page", async () => {
    vi.mocked(vendorTagsApi.listVendorCaseTags).mockRejectedValue(new Error("boom"));
    renderPage();

    expect(await screen.findByText("REQ-1001")).toBeInTheDocument();
    expect(screen.queryByRole("group", { name: "標籤篩選" })).not.toBeInTheDocument();
  });
});
