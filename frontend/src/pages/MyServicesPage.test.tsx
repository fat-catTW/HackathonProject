import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { MyServicesPage, sortRequests } from "./MyServicesPage";
import * as requestsApi from "../api/requests";
import type { RequestListItem, RequestStatus } from "../types/request";

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

function item(
  request_id: string,
  status: RequestStatus,
  updated_at: string,
): RequestListItem {
  return {
    request_id,
    service_name: "冷氣清洗",
    status,
    status_label: status,
    created_at: "2026-07-20T00:00:00+08:00",
    updated_at,
  };
}

describe("sortRequests", () => {
  it("剛被廠商接單的案件回到第一位，不會被一堆沒動靜的舊單蓋掉", () => {
    // 這就是實際踩到的情境：住戶名下 26 筆放著沒動的「等待廠商確認」，
    // 舊的排序把剛接單的那筆壓到第 27 位，看起來像消失了。
    const stale = Array.from({ length: 26 }, (_, i) =>
      item(`stale-${i}`, "SUBMITTED", "2026-07-25T00:00:00+08:00"),
    );
    const justAccepted = item("just-accepted", "CONFIRMED", "2026-07-31T21:36:20+08:00");

    const sorted = sortRequests([...stale, justAccepted]);

    expect(sorted[0].request_id).toBe("just-accepted");
  });

  it("不管走到哪一步，最近更新的排前面", () => {
    const sorted = sortRequests([
      item("waiting-old", "SUBMITTED", "2026-07-28T09:00:00+08:00"),
      item("running-new", "IN_PROGRESS", "2026-07-31T20:00:00+08:00"),
      item("waiting-mid", "AWAITING_QUOTE", "2026-07-30T12:00:00+08:00"),
    ]);
    expect(sorted.map((i) => i.request_id)).toEqual([
      "running-new",
      "waiting-mid",
      "waiting-old",
    ]);
  });

  it("已結案的沉到底部，就算它才剛更新", () => {
    const sorted = sortRequests([
      item("done", "COMPLETED", "2026-07-31T23:00:00+08:00"),
      item("rejected", "REJECTED", "2026-07-31T22:00:00+08:00"),
      item("waiting", "SUBMITTED", "2026-07-20T00:00:00+08:00"),
    ]);
    expect(sorted.map((i) => i.request_id)).toEqual(["waiting", "done", "rejected"]);
  });

  it("結案組內同樣最近的在前", () => {
    const sorted = sortRequests([
      item("cancelled-old", "CANCELLED", "2026-07-20T00:00:00+08:00"),
      item("completed-new", "COMPLETED", "2026-07-31T10:00:00+08:00"),
    ]);
    expect(sorted.map((i) => i.request_id)).toEqual(["completed-new", "cancelled-old"]);
  });

  it("用 updated_at 而不是 created_at", () => {
    const older = { ...item("recently-updated", "SUBMITTED", "2026-07-31T20:47:05+08:00") };
    const newer = { ...item("newly-created", "SUBMITTED", "2026-07-22T00:00:00+08:00") };
    newer.created_at = "2026-07-31T23:59:00+08:00";

    expect(sortRequests([newer, older]).map((i) => i.request_id)).toEqual([
      "recently-updated",
      "newly-created",
    ]);
  });

  it("時間字串壞掉不會把排序弄亂", () => {
    const sorted = sortRequests([
      item("broken", "SUBMITTED", "not-a-date"),
      item("good", "SUBMITTED", "2026-07-31T20:47:05+08:00"),
    ]);
    expect(sorted.map((i) => i.request_id)).toEqual(["good", "broken"]);
  });

  it("不改動傳進來的陣列", () => {
    const input = [
      item("a", "COMPLETED", "2026-07-31T10:00:00+08:00"),
      item("b", "SUBMITTED", "2026-07-31T10:00:00+08:00"),
    ];
    sortRequests(input);
    expect(input.map((i) => i.request_id)).toEqual(["a", "b"]);
  });
});
