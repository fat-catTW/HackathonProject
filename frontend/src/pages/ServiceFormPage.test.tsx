import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { ServiceFormPage } from "./ServiceFormPage";
import * as servicesApi from "../api/services";

vi.mock("../api/services");

function renderPage(serviceId = "plumbing_repair") {
  return render(
    <MemoryRouter initialEntries={[`/services/${serviceId}`]}>
      <Routes>
        <Route path="/services/:serviceId" element={<ServiceFormPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.mocked(servicesApi.createServiceRequest).mockResolvedValue({
    success: true,
    request_id: "REQ-001",
    status: "SUBMITTED",
    message: "ok",
  });
});

describe("ServiceFormPage", () => {
  it("submits service address as one combined string", async () => {
    const user = userEvent.setup();
    renderPage("plumbing_repair");

    await user.selectOptions(await screen.findByLabelText("叫修工項"), "水管");
    await user.type(screen.getByLabelText("問題描述"), "廚房水槽下方漏水");
    await user.type(screen.getByLabelText("服務日期"), "2026-08-10");
    await user.selectOptions(screen.getByLabelText("服務時間"), "09:00");
    await user.selectOptions(screen.getByLabelText("服務地址縣市"), "台北市");
    await screen.findByRole("option", { name: "大安區" });
    await user.selectOptions(screen.getByLabelText("服務地址鄉鎮市區"), "大安區");
    await user.type(screen.getByLabelText("服務地址詳細地址"), "大學路一段 168 號");
    await user.type(screen.getByLabelText("聯絡電話"), "0912345678");
    await user.click(screen.getByRole("button", { name: "送出服務需求" }));

    await waitFor(() => {
      expect(servicesApi.createServiceRequest).toHaveBeenCalledWith(
        "plumbing_repair",
        expect.objectContaining({
          address: "台北市大安區大學路一段 168 號",
        }),
      );
    });
  });
});
