import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "../api/client";
import { actOnVendorRequest, getVendorRequest, revealVendorContact } from "../api/vendor";
import type { VendorRequestDetail } from "../types/vendor";
import { VendorRequestDetailPage } from "./VendorRequestDetailPage";

vi.mock("../api/vendor", () => ({
  getVendorRequest: vi.fn(),
  actOnVendorRequest: vi.fn(),
  revealVendorContact: vi.fn(),
  listVendorRequests: vi.fn(),
}));

vi.mock("../api/vendorTags", () => ({
  getVendorCaseTags: vi.fn(async (requestId: string) => ({ request_id: requestId, tags: [] })),
  saveVendorCaseTags: vi.fn(async (requestId: string, tags: string[]) => ({
    success: true,
    request_id: requestId,
    tags,
  })),
  listVendorCaseTags: vi.fn(async () => ({ tags: {} })),
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
  fields: [
    { id: "preferred_date", label: "希望到府日期", value: "2026-08-01", masked: false },
    { id: "phone", label: "聯絡電話", value: "0912***678", masked: true },
  ],
  has_contact: true,
  contact_access_log: [],
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
    vi.mocked(revealVendorContact).mockReset();
  });

  it("接單時帶上畫面看到的版本，成功後換成新狀態並收掉按鈕", async () => {
    const user = userEvent.setup();
    vi.mocked(actOnVendorRequest).mockResolvedValue({ ...CONFIRMED, success: true });
    renderPage();

    await user.click(await screen.findByText("接單"));

    expect(actOnVendorRequest).toHaveBeenCalledWith(PENDING.request_id, "accept", 1);
    expect(await screen.findByText("已確認")).toBeInTheDocument();
    expect(screen.queryByText("接單")).not.toBeInTheDocument();
    expect(screen.queryByText("婉拒")).not.toBeInTheDocument();
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

    // Click the first "婉拒" button (action button) to trigger the modal
    const rejectButtons = await screen.findAllByText("婉拒");
    await user.click(rejectButtons[0]);
    expect(actOnVendorRequest).not.toHaveBeenCalled();

    // Click the second "婉拒" button (confirm button in modal)
    const allRejectButtons = screen.getAllByText("婉拒");
    await user.click(allRejectButtons[1]);
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

    await user.click(await screen.findByText("接單"));

    expect(await screen.findByText("案件目前是「已取消」，無法接單。")).toBeInTheDocument();
    expect(screen.getByText("已取消")).toBeInTheDocument();
    expect(screen.queryByText("接單")).not.toBeInTheDocument();
  });
});

describe("VendorRequestDetailPage 聯絡資訊", () => {
  beforeEach(() => {
    vi.mocked(getVendorRequest).mockResolvedValue(PENDING);
    vi.mocked(actOnVendorRequest).mockReset();
    vi.mocked(revealVendorContact).mockReset();
  });

  it("預設只顯示遮罩值，解密後換成完整內容並列出存取紀錄", async () => {
    const user = userEvent.setup();
    vi.mocked(revealVendorContact).mockResolvedValue({
      success: true,
      request_id: PENDING.request_id,
      contact: [{ id: "phone", label: "聯絡電話", value: "0912345678" }],
      contact_access_log: [
        { at: "2026-08-01T10:30:00+08:00", viewer_name: "潔家家事服務", fields: ["聯絡電話"] },
      ],
    });
    renderPage();

    expect(await screen.findByText("0912***678")).toBeInTheDocument();
    expect(screen.queryByText("0912345678")).not.toBeInTheDocument();

    await user.click(screen.getByText("顯示完整聯絡資訊"));

    expect(revealVendorContact).toHaveBeenCalledWith(PENDING.request_id);
    expect(await screen.findByText("0912345678")).toBeInTheDocument();
    expect(screen.queryByText("0912***678")).not.toBeInTheDocument();
    // 解鎖後按鈕收起來，並把這次檢視列進存取紀錄。
    expect(screen.queryByText("顯示完整聯絡資訊")).not.toBeInTheDocument();
    expect(screen.getByText(/潔家家事服務 檢視了/)).toBeInTheDocument();
  });

  it("解密失敗時保留遮罩並顯示錯誤", async () => {
    const user = userEvent.setup();
    vi.mocked(revealVendorContact).mockRejectedValue(
      new ApiError("CONTACT_LOG_UNAVAILABLE", "無法寫入存取紀錄，請稍後再試。"),
    );
    renderPage();

    await user.click(await screen.findByText("顯示完整聯絡資訊"));

    expect(await screen.findByRole("alert")).toHaveTextContent("無法寫入存取紀錄，請稍後再試。");
    expect(screen.getByText("0912***678")).toBeInTheDocument();
  });

  it("沒有聯絡欄位的案件不顯示聯絡資訊區塊", async () => {
    vi.mocked(getVendorRequest).mockResolvedValue({
      ...PENDING,
      fields: PENDING.fields.filter((f) => !f.masked),
      has_contact: false,
    });
    renderPage();

    expect(await screen.findByText("服務內容")).toBeInTheDocument();
    expect(screen.queryByText("聯絡資訊")).not.toBeInTheDocument();
  });
});

describe("VendorRequestDetailPage AI 需求摘要", () => {
  beforeEach(() => {
    vi.mocked(getVendorRequest).mockReset();
  });

  it("有摘要時顯示在服務名稱下方", async () => {
    vi.mocked(getVendorRequest).mockResolvedValue({
      ...PENDING,
      ai_summary: "清洗 2 台壁掛式冷氣，8/1 上午到府",
    });
    renderPage();

    expect(await screen.findByText("AI 摘要")).toBeInTheDocument();
    expect(screen.getByText("清洗 2 台壁掛式冷氣，8/1 上午到府")).toBeInTheDocument();
  });

  it("外送／商城後台與舊案件沒有摘要欄位時整列不顯示", async () => {
    // 這兩種來源的明細 API 根本不回 ai_summary，畫面不該冒出一個空的「AI 摘要」列。
    vi.mocked(getVendorRequest).mockResolvedValue(PENDING);
    renderPage();

    expect(await screen.findByText("服務內容")).toBeInTheDocument();
    expect(screen.queryByText("AI 摘要")).not.toBeInTheDocument();
  });
});
