import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { MyServicesPage } from "./MyServicesPage";
import * as requestsApi from "../api/requests";
import type { RequestListItem } from "../types/request";

vi.mock("../api/requests");

const ITEMS: RequestListItem[] = [
  {
    request_id: "REQ-1",
    service_name: "水電修繕",
    status: "SUBMITTED",
    status_label: "已送出",
    created_at: "2026-07-30T01:00:00Z",
    updated_at: "2026-07-30T01:00:00Z",
  },
  {
    request_id: "REQ-2",
    service_name: "居家清潔",
    status: "CONFIRMED",
    status_label: "已確認",
    created_at: "2026-07-29T01:00:00Z",
    updated_at: "2026-07-29T01:00:00Z",
  },
  {
    request_id: "REQ-3",
    service_name: "居家清潔",
    status: "COMPLETED",
    status_label: "已完成",
    created_at: "2026-07-28T01:00:00Z",
    updated_at: "2026-07-28T01:00:00Z",
  },
  {
    request_id: "REQ-4",
    service_name: "冷氣清洗",
    status: "COMPLETED",
    status_label: "已完成",
    created_at: "2026-07-27T01:00:00Z",
    updated_at: "2026-07-27T01:00:00Z",
  },
];

function renderPage() {
  return render(
    <MemoryRouter>
      <MyServicesPage />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.mocked(requestsApi.listRequests).mockResolvedValue({ items: ITEMS });
});

describe("MyServicesPage 分類與搜尋", () => {
  it("hides the filter bar entirely when there are 3 or fewer requests", async () => {
    vi.mocked(requestsApi.listRequests).mockResolvedValue({ items: ITEMS.slice(0, 3) });
    renderPage();
    await waitFor(() => expect(screen.getByText("水電修繕")).toBeInTheDocument());
    expect(screen.queryByLabelText("搜尋服務名稱")).not.toBeInTheDocument();
  });

  it("shows a category chip per distinct service plus an 全部 chip with the total count", async () => {
    renderPage();
    await waitFor(() => expect(screen.getAllByText("居家清潔").length).toBeGreaterThan(0));

    const allChip = screen.getByRole("button", { name: /全部/ });
    expect(allChip).toHaveTextContent("4");

    const cleaningChip = screen.getByRole("button", { name: /居家清潔/ });
    expect(cleaningChip).toHaveTextContent("2");
  });

  it("filters the list when a category chip is clicked", async () => {
    const user = userEvent.setup();
    renderPage();
    await waitFor(() => expect(screen.getAllByText("居家清潔").length).toBeGreaterThan(0));

    await user.click(screen.getByRole("button", { name: /冷氣清洗/ }));

    expect(screen.getByRole("link", { name: /冷氣清洗/ })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /水電修繕/ })).not.toBeInTheDocument();
    expect(screen.queryAllByRole("link", { name: /居家清潔/ })).toHaveLength(0);
  });

  it("filters the list by search text on service name", async () => {
    const user = userEvent.setup();
    renderPage();
    await waitFor(() => expect(screen.getAllByText("居家清潔").length).toBeGreaterThan(0));

    await user.type(screen.getByLabelText("搜尋服務名稱"), "水電");

    expect(screen.getByRole("link", { name: /水電修繕/ })).toBeInTheDocument();
    expect(screen.queryAllByRole("link", { name: /居家清潔/ })).toHaveLength(0);
    expect(screen.queryByRole("link", { name: /冷氣清洗/ })).not.toBeInTheDocument();
  });

  it("shows an empty-state message when no request matches the filters", async () => {
    const user = userEvent.setup();
    renderPage();
    await waitFor(() => expect(screen.getAllByText("居家清潔").length).toBeGreaterThan(0));

    await user.type(screen.getByLabelText("搜尋服務名稱"), "不存在的服務");

    expect(screen.getByText(/找不到符合的服務案件/)).toBeInTheDocument();
  });
});
