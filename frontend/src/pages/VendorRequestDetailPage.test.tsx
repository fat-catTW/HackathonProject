import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "../api/client";
import { actOnVendorRequest, getVendorRequest } from "../api/vendor";
import type { VendorRequestDetail } from "../types/vendor";
import { VendorRequestDetailPage } from "./VendorRequestDetailPage";

vi.mock("../api/vendor", () => ({
  getVendorRequest: vi.fn(),
  actOnVendorRequest: vi.fn(),
}));

const PENDING: VendorRequestDetail = {
  request_id: "REQ-20260801-001",
  service_id: "air_conditioner_cleaning",
  service_name: "冷氣清洗",
  status: "SUBMITTED",
  status_label: "等待廠商確認",
  customer_name: "Vincent",
  version: 1,
  available_actions: ["accept", "reject"],
  fields: [{ id: "phone", label: "聯絡電話", value: "0912345678" }],
  created_at: "2026-08-01T09:00:00+08:00",
  updated_at: "2026-08-01T09:00:00+08:00",
};

const CONFIRMED: VendorRequestDetail = {
  ...PENDING,
  status: "CONFIRMED",
  status_label: "已確認",
  version: 2,
  available_actions: [],
};

function renderPage() {
  return render(
    <MemoryRouter initialEntries={[`/vendor/requests/${PENDING.request_id}`]}>
      <Routes>
        <Route path="/vendor/requests/:requestId" element={<VendorRequestDetailPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("VendorRequestDetailPage 接單／拒單", () => {
  beforeEach(() => {
    vi.mocked(getVendorRequest).mockResolvedValue(PENDING);
    vi.mocked(actOnVendorRequest).mockReset();
  });

  it("接單時帶上畫面看到的版本，成功後換成新狀態並收掉按鈕", async () => {
    const user = userEvent.setup();
    vi.mocked(actOnVendorRequest).mockResolvedValue({ ...CONFIRMED, success: true });
    renderPage();

    await user.click(await screen.findByText("接下這張單"));

    expect(actOnVendorRequest).toHaveBeenCalledWith(PENDING.request_id, "accept", 1);
    expect(await screen.findByText("已確認")).toBeInTheDocument();
    expect(screen.queryByText("接下這張單")).not.toBeInTheDocument();
    expect(screen.queryByText("婉拒這張單")).not.toBeInTheDocument();
  });

  it("婉拒需要二次確認", async () => {
    const user = userEvent.setup();
    vi.mocked(actOnVendorRequest).mockResolvedValue({
      ...CONFIRMED,
      status: "REJECTED",
      status_label: "廠商已婉拒",
      success: true,
    });
    renderPage();

    await user.click(await screen.findByText("婉拒這張單"));
    expect(actOnVendorRequest).not.toHaveBeenCalled();

    await user.click(screen.getByText("婉拒"));
    expect(actOnVendorRequest).toHaveBeenCalledWith(PENDING.request_id, "reject", 1);
    expect(await screen.findByText("廠商已婉拒")).toBeInTheDocument();
  });

  it("案件已被別人改過時顯示提示，並換成後端回報的現況", async () => {
    const user = userEvent.setup();
    vi.mocked(actOnVendorRequest).mockRejectedValue(
      new ApiError(
        "REQUEST_STATUS_CONFLICT",
        "案件目前是「已取消」，無法接單。",
        undefined,
        {
          ...CONFIRMED,
          status: "CANCELLED",
          status_label: "已取消",
          code: "REQUEST_STATUS_CONFLICT",
        },
      ),
    );
    renderPage();

    await user.click(await screen.findByText("接下這張單"));

    expect(await screen.findByText("案件目前是「已取消」，無法接單。")).toBeInTheDocument();
    expect(screen.getByText("已取消")).toBeInTheDocument();
    expect(screen.queryByText("接下這張單")).not.toBeInTheDocument();
  });
});
