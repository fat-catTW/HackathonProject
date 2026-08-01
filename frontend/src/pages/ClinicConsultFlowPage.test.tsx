import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { ClinicConsultFlowPage } from "./ClinicConsultFlowPage";
import * as clinicsApi from "../api/clinics";

vi.mock("../api/clinics");

const clinics = [
  {
    id: "c1",
    name: "王耳鼻喉科診所",
    specialties: ["耳鼻喉科"],
    address: "台中市西屯區文心路100號",
    phone: "04-1111111",
    is_open_now: true,
  },
];

function renderPage() {
  return render(
    <MemoryRouter>
      <ClinicConsultFlowPage />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(clinicsApi.triageSymptom).mockResolvedValue({
    specialty: "耳鼻喉科",
    advisory: "聽起來像是感冒了，要多喝溫水喔！",
    clinics,
    recommended_clinic_id: "c1",
    recommend_reason: "距離近且目前有看診",
  });
  vi.mocked(clinicsApi.submitClinicAppointment).mockResolvedValue({
    success: true,
    request_id: "REQ-1",
    status: "CONFIRMED",
  });
  vi.mocked(clinicsApi.getCrossSellRecommendations).mockResolvedValue({
    recommendations: [{ product_id: "P039", name: "蜂蜜潤喉糖", reason: "適合喉嚨不適" }],
    fallback_used: false,
  });
});

describe("ClinicConsultFlowPage", () => {
  it("walks through symptom entry to clinic recommendation", async () => {
    const user = userEvent.setup();
    renderPage();

    const input = screen.getByLabelText("症狀描述");
    await user.type(input, "我一直咳嗽，喉嚨很癢");
    await user.click(screen.getByRole("button", { name: "送出" }));

    expect(await screen.findByText(/聽起來像是感冒了/)).toBeInTheDocument();
    expect(screen.getByText("王耳鼻喉科診所")).toBeInTheDocument();
    expect(screen.getByText("AI 推薦")).toBeInTheDocument();
  });

  it("submits the appointment and shows the cross-sell + family-share step", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByLabelText("症狀描述"), "我一直咳嗽，喉嚨很癢");
    await user.click(screen.getByRole("button", { name: "送出" }));
    await screen.findByText("王耳鼻喉科診所");

    await user.click(screen.getByText("王耳鼻喉科診所"));
    await user.click(screen.getByRole("button", { name: "下一步" }));

    const dateInput = screen.getByLabelText("看診日期");
    await user.type(dateInput, "2026-08-02");
    await user.type(screen.getByLabelText("看診時間"), "15:00");
    await user.click(screen.getByRole("button", { name: "下一步" }));

    await user.type(screen.getByLabelText("聯絡人姓名"), "王添財");
    await user.type(screen.getByLabelText("聯絡電話"), "0912345678");
    await user.click(screen.getByRole("button", { name: "下一步" }));

    await user.click(screen.getByRole("button", { name: "確認掛號" }));

    await waitFor(() => expect(clinicsApi.submitClinicAppointment).toHaveBeenCalledTimes(1));
    expect(await screen.findByText(/適合喉嚨不適/)).toBeInTheDocument();
    expect(screen.getByText("蜂蜜潤喉糖")).toBeInTheDocument();
    expect(screen.getByText(/爸爸今天有點咳嗽/)).toBeInTheDocument();
    expect(screen.getByText(/8月2日 下午3點/)).toBeInTheDocument();
  });

  it("still advances past summary when appointment succeeds but cross-sell fails", async () => {
    vi.mocked(clinicsApi.getCrossSellRecommendations).mockRejectedValue(
      new Error("cross-sell service unavailable"),
    );
    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByLabelText("症狀描述"), "我一直咳嗽，喉嚨很癢");
    await user.click(screen.getByRole("button", { name: "送出" }));
    await screen.findByText("王耳鼻喉科診所");

    await user.click(screen.getByText("王耳鼻喉科診所"));
    await user.click(screen.getByRole("button", { name: "下一步" }));

    await user.type(screen.getByLabelText("看診日期"), "2026-08-02");
    await user.type(screen.getByLabelText("看診時間"), "15:00");
    await user.click(screen.getByRole("button", { name: "下一步" }));

    await user.type(screen.getByLabelText("聯絡人姓名"), "王添財");
    await user.type(screen.getByLabelText("聯絡電話"), "0912345678");
    await user.click(screen.getByRole("button", { name: "下一步" }));

    await user.click(screen.getByRole("button", { name: "確認掛號" }));

    await waitFor(() => expect(clinicsApi.submitClinicAppointment).toHaveBeenCalledTimes(1));
    // Should advance to the result step (family-share text renders there), not stay stuck
    // on the summary screen with a false booking-failure error.
    expect(await screen.findByText(/爸爸今天有點咳嗽/)).toBeInTheDocument();
    expect(screen.getByText(/8月2日 下午3點/)).toBeInTheDocument();
    expect(screen.queryByText("掛號未成功送出，請重新嘗試")).not.toBeInTheDocument();

    // Confirm no duplicate appointment submission occurs, even after the cross-sell
    // rejection settles.
    expect(clinicsApi.submitClinicAppointment).toHaveBeenCalledTimes(1);
  });

  it("shows an empty-state message and a working back button when no clinics are found", async () => {
    vi.mocked(clinicsApi.triageSymptom).mockResolvedValue({
      specialty: "耳鼻喉科",
      advisory: "聽起來像是感冒了，要多喝溫水喔！",
      clinics: [],
      recommended_clinic_id: null,
      recommend_reason: null,
    });
    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByLabelText("症狀描述"), "我一直咳嗽，喉嚨很癢");
    await user.click(screen.getByRole("button", { name: "送出" }));

    expect(
      await screen.findByText(/目前這個地區沒有找到符合的診所，請返回調整症狀或地區/),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "上一步" }));

    expect(await screen.findByLabelText("症狀描述")).toBeInTheDocument();
  });
});
