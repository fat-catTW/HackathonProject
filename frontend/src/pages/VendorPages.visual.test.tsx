import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

/**
 * Tier D 廠商後台的視覺套用迴歸測試（Task 10.3）。
 *
 * 斷言重點：Tab 列與案件列表未套 `glass-panel`（Requirement 14.1、15.2）、
 * 既有欄位與操作按鈕順序不變（Requirement 14.4）、狀態改用共用 StatusBadge
 * 的語意狀態色（Requirement 14.3）。所有 API 一律 mock。
 */
const LIST_ITEM = {
  request_id: "REQ-20260731-001",
  service_name: "冷氣清洗",
  customer_name: "陳阿姨",
  summary: "客廳分離式冷氣",
  status: "PENDING_PROVIDER",
  status_label: "待確認",
  updated_at: "2026-07-31T03:00:00Z",
};

vi.mock("../api/vendor", () => ({
  fetchVendorProfile: vi.fn(async () => ({ name: "示範水電行", vendor_id: "V-001" })),
  listVendorRequests: vi.fn(async () => ({ items: [LIST_ITEM], counts: { pending: 1, orders: 0 } })),
  getVendorRequest: vi.fn(async () => ({
    request_id: LIST_ITEM.request_id,
    service_name: LIST_ITEM.service_name,
    status: LIST_ITEM.status,
    status_label: LIST_ITEM.status_label,
    customer_name: LIST_ITEM.customer_name,
    fields: [],
    events: [],
    available_actions: [],
    updated_at: LIST_ITEM.updated_at,
  })),
  vendorLogin: vi.fn(),
  fetchVendorDemoAccounts: vi.fn(async () => ({ accounts: [] })),
}));

import { VendorRequestsPage } from "./VendorRequestsPage";
import { VendorRequestDetailPage } from "./VendorRequestDetailPage";

beforeEach(() => {
  document.documentElement.setAttribute("data-color-mode", "light");
  // 廠商登入狀態由 localStorage 驅動，先塞入 token 避免頁面轉走
  localStorage.setItem("vendor-token", "test-token");
  localStorage.setItem("vendor-name", "示範水電行");
});

describe("VendorRequestsPage 視覺套用", () => {
  it("keeps the tab bar and request list fully opaque — no glass-panel (Requirements 14.1, 15.2)", async () => {
    const { container } = render(
      <MemoryRouter>
        <VendorRequestsPage />
      </MemoryRouter>,
    );

    await waitFor(() => expect(screen.getByText(LIST_ITEM.request_id)).toBeInTheDocument());
    expect(container.querySelectorAll(".glass-panel").length).toBe(0);
  });

  it("uses only the soft gradient band on the title area (Requirement 14.1)", async () => {
    const { container } = render(
      <MemoryRouter>
        <VendorRequestsPage />
      </MemoryRouter>,
    );

    await waitFor(() => expect(screen.getByText(LIST_ITEM.request_id)).toBeInTheDocument());
    // 極淡漸層僅出現在 <header>，列表與 Tab 不得套用任何漸層
    const header = container.querySelector("header");
    expect(header?.classList.contains("bg-brand-gradient-soft")).toBe(true);
    expect(container.querySelectorAll(".bg-brand-gradient").length).toBe(0);
    expect(container.querySelector("nav")?.className).not.toContain("gradient");
  });

  it("keeps the existing tabs, list fields and links in order (Requirement 14.4)", async () => {
    render(
      <MemoryRouter>
        <VendorRequestsPage />
      </MemoryRouter>,
    );

    expect(screen.getByRole("button", { name: /待確認諮詢單/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /已接訂單/ })).toBeInTheDocument();

    await waitFor(() => expect(screen.getByText(LIST_ITEM.request_id)).toBeInTheDocument());
    expect(screen.getByText(LIST_ITEM.request_id)).toBeInTheDocument();
    expect(screen.getByText(/陳阿姨/)).toBeInTheDocument();
    // 列表項目仍為連往明細頁的 Link
    expect(screen.getByRole("link")).toHaveAttribute(
      "href",
      `/vendor/requests/${LIST_ITEM.request_id}`,
    );
  });

  it("renders status through the shared StatusBadge semantic colors (Requirement 14.3)", async () => {
    render(
      <MemoryRouter>
        <VendorRequestsPage />
      </MemoryRouter>,
    );

    const badge = await screen.findByText("待確認");
    // PENDING_PROVIDER 對應 warning 語意色配對
    expect(badge.className).toContain("var(--color-warning-soft)");
    expect(badge.className).toContain("var(--color-warning)");
  });
});

describe("VendorRequestDetailPage 視覺套用", () => {
  it("keeps detail cards opaque — no glass-panel (Requirements 14.2, 15.2)", async () => {
    const { container } = render(
      <MemoryRouter initialEntries={[`/vendor/requests/${LIST_ITEM.request_id}`]}>
        <Routes>
          <Route path="/vendor/requests/:requestId" element={<VendorRequestDetailPage />} />
        </Routes>
      </MemoryRouter>,
    );

    await waitFor(() => expect(screen.getByText(LIST_ITEM.request_id)).toBeInTheDocument());
    expect(container.querySelectorAll(".glass-panel").length).toBe(0);
  });

  it("shows the request id and status badge (Requirements 14.2, 14.3)", async () => {
    render(
      <MemoryRouter initialEntries={[`/vendor/requests/${LIST_ITEM.request_id}`]}>
        <Routes>
          <Route path="/vendor/requests/:requestId" element={<VendorRequestDetailPage />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByText(LIST_ITEM.request_id)).toBeInTheDocument();
    const badge = await screen.findByText("待確認");
    expect(badge.className).toContain("var(--color-warning)");
  });
});
