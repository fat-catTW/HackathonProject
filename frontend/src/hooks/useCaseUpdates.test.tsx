import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { clearAuth, setAuth } from "../api/client";
import type { RequestListItem, RequestStatus } from "../types/request";

vi.mock("../api/requests");

function item(
  request_id: string,
  service_name: string,
  status: RequestStatus,
): RequestListItem {
  return {
    request_id,
    service_name,
    status,
    status_label: status,
    created_at: "2026-08-02T01:00:00Z",
    updated_at: "2026-08-02T01:00:00Z",
  };
}

/**
 * 每個案例都要一份乾淨的 module 狀態：待跳佇列與「上次看到的狀態」快照都放在
 * module 層（見 useCaseUpdates 的註解），沿用上一個案例的殘留會互相污染。
 */
async function loadHook() {
  vi.resetModules();
  const requestsApi = await import("../api/requests");
  const hook = await import("./useCaseUpdates");
  const listRequests = vi.mocked(requestsApi.listRequests);
  // automock 的 vi.fn() 在 resetModules 之後仍是同一個，呼叫次數會跨案例累加。
  listRequests.mockClear();
  return { listRequests, ...hook };
}

type UseCaseUpdates = Awaited<ReturnType<typeof loadHook>>["useCaseUpdates"];

function Probe({ useCaseUpdates }: { useCaseUpdates: UseCaseUpdates }) {
  const { update, dismiss } = useCaseUpdates();
  if (!update) return <p>沒有通知</p>;
  return (
    <div>
      <p>{`${update.serviceName} / ${update.status}`}</p>
      <button type="button" onClick={dismiss}>
        關掉
      </button>
    </div>
  );
}

/** 掛上 Probe 並跑完第一次輪詢（建立基準快照）。 */
async function mount(useCaseUpdates: UseCaseUpdates) {
  render(<Probe useCaseUpdates={useCaseUpdates} />);
  await act(async () => {});
}

/** 快轉到下一次輪詢並等回應處理完。 */
async function nextPoll(intervalMs: number) {
  await act(async () => {
    vi.advanceTimersByTime(intervalMs);
  });
}

function shownUpdate() {
  return screen.queryByText(/ \/ /)?.textContent ?? null;
}

beforeEach(() => {
  vi.useFakeTimers();
  sessionStorage.clear();
  setAuth("resident-token", "王小明");
});

afterEach(() => {
  vi.useRealTimers();
  clearAuth();
});

describe("useCaseUpdates", () => {
  it("stays quiet on the first poll — it only learns where each case currently stands", async () => {
    const { useCaseUpdates, listRequests } = await loadHook();
    // 一進 App 就有一張已確認的案件，是之前就確認過的，不該現在才通知。
    listRequests.mockResolvedValue({ items: [item("REQ-1", "冷氣清潔", "CONFIRMED")] });

    await mount(useCaseUpdates);

    expect(screen.getByText("沒有通知")).toBeInTheDocument();
  });

  it("pops a notification when the vendor accepts a case", async () => {
    const { useCaseUpdates, listRequests, POLL_INTERVAL_MS } = await loadHook();
    listRequests.mockResolvedValue({ items: [item("REQ-1", "冷氣清潔", "SUBMITTED")] });
    await mount(useCaseUpdates);

    listRequests.mockResolvedValue({ items: [item("REQ-1", "冷氣清潔", "CONFIRMED")] });
    await nextPoll(POLL_INTERVAL_MS);

    expect(shownUpdate()).toBe("冷氣清潔 / CONFIRMED");
  });

  it("pops a notification when the vendor turns a case down", async () => {
    const { useCaseUpdates, listRequests, POLL_INTERVAL_MS } = await loadHook();
    listRequests.mockResolvedValue({ items: [item("REQ-1", "水電維修", "PENDING_PROVIDER")] });
    await mount(useCaseUpdates);

    listRequests.mockResolvedValue({ items: [item("REQ-1", "水電維修", "REJECTED")] });
    await nextPoll(POLL_INTERVAL_MS);

    expect(shownUpdate()).toBe("水電維修 / REJECTED");
  });

  it("does not pop for a case the resident just created", async () => {
    const { useCaseUpdates, listRequests, POLL_INTERVAL_MS } = await loadHook();
    listRequests.mockResolvedValue({ items: [] });
    await mount(useCaseUpdates);

    // 剛送出的單，以及當下就成立的即時訂單：都是住戶自己剛做完的事。
    listRequests.mockResolvedValue({
      items: [item("REQ-1", "居家清潔", "SUBMITTED"), item("REQ-2", "商城購物", "CONFIRMED")],
    });
    await nextPoll(POLL_INTERVAL_MS);

    expect(screen.getByText("沒有通知")).toBeInTheDocument();
  });

  it("ignores status changes that are not worth interrupting anyone for", async () => {
    const { useCaseUpdates, listRequests, POLL_INTERVAL_MS } = await loadHook();
    listRequests.mockResolvedValue({ items: [item("REQ-1", "居家清潔", "DRAFT")] });
    await mount(useCaseUpdates);

    // 住戶自己按的取消，不需要再回頭通知他一次。
    listRequests.mockResolvedValue({ items: [item("REQ-1", "居家清潔", "CANCELLED")] });
    await nextPoll(POLL_INTERVAL_MS);

    expect(screen.getByText("沒有通知")).toBeInTheDocument();
  });

  it("shows one card at a time and queues the rest", async () => {
    const { useCaseUpdates, listRequests, POLL_INTERVAL_MS } = await loadHook();
    listRequests.mockResolvedValue({
      items: [item("REQ-1", "冷氣清潔", "SUBMITTED"), item("REQ-2", "水電維修", "SUBMITTED")],
    });
    await mount(useCaseUpdates);

    listRequests.mockResolvedValue({
      items: [item("REQ-1", "冷氣清潔", "CONFIRMED"), item("REQ-2", "水電維修", "REJECTED")],
    });
    await nextPoll(POLL_INTERVAL_MS);
    expect(shownUpdate()).toBe("冷氣清潔 / CONFIRMED");

    fireEvent.click(screen.getByRole("button", { name: "關掉" }));
    expect(shownUpdate()).toBe("水電維修 / REJECTED");

    fireEvent.click(screen.getByRole("button", { name: "關掉" }));
    expect(screen.getByText("沒有通知")).toBeInTheDocument();
  });

  it("does not report the same change twice on later polls", async () => {
    const { useCaseUpdates, listRequests, POLL_INTERVAL_MS } = await loadHook();
    listRequests.mockResolvedValue({ items: [item("REQ-1", "冷氣清潔", "SUBMITTED")] });
    await mount(useCaseUpdates);

    listRequests.mockResolvedValue({ items: [item("REQ-1", "冷氣清潔", "CONFIRMED")] });
    await nextPoll(POLL_INTERVAL_MS);
    fireEvent.click(screen.getByRole("button", { name: "關掉" }));

    await nextPoll(POLL_INTERVAL_MS);

    expect(screen.getByText("沒有通知")).toBeInTheDocument();
  });

  it("shrugs off a failed poll and picks the change up on the next one", async () => {
    const { useCaseUpdates, listRequests, POLL_INTERVAL_MS } = await loadHook();
    listRequests.mockResolvedValue({ items: [item("REQ-1", "冷氣清潔", "SUBMITTED")] });
    await mount(useCaseUpdates);

    listRequests.mockRejectedValueOnce(new Error("network down"));
    await nextPoll(POLL_INTERVAL_MS);
    expect(screen.getByText("沒有通知")).toBeInTheDocument();

    listRequests.mockResolvedValue({ items: [item("REQ-1", "冷氣清潔", "CONFIRMED")] });
    await nextPoll(POLL_INTERVAL_MS);

    expect(shownUpdate()).toBe("冷氣清潔 / CONFIRMED");
  });

  it("does not poll at all when nobody is logged in", async () => {
    clearAuth();
    const { useCaseUpdates, listRequests, POLL_INTERVAL_MS } = await loadHook();
    listRequests.mockResolvedValue({ items: [] });

    await mount(useCaseUpdates);
    await nextPoll(POLL_INTERVAL_MS);

    expect(listRequests).not.toHaveBeenCalled();
  });
});
