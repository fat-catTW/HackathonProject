import { useState } from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { ServiceFormPage } from "./ServiceFormPage";
import { FormAgentProvider, useFormAgent } from "../hooks/useFormAgent";
import type { FormAction } from "../types/request";
import * as servicesApi from "../api/services";

vi.mock("../api/services");

const ACTIONS: FormAction[] = [
  {
    type: "fill",
    field_id: "quantity",
    label: "冷氣數量",
    value: "2",
    display_value: "2 台",
    note: null,
  },
  {
    type: "fill",
    field_id: "air_conditioner_type",
    label: "冷氣機種",
    value: "壁掛式",
    display_value: "壁掛式",
    note: null,
  },
  {
    type: "fill",
    field_id: "antibacterial_film_addon",
    label: "是否加購日本抗菌膜",
    value: "NO",
    display_value: "不需要",
    note: null,
  },
  {
    type: "fill",
    field_id: "preferred_date",
    label: "服務日期",
    value: "2026-08-10",
    display_value: "2026-08-10",
    note: null,
  },
  {
    type: "fill",
    field_id: "preferred_time_slot",
    label: "服務時間",
    value: "15:00",
    display_value: "15:00",
    note: null,
  },
  {
    type: "fill",
    field_id: "address",
    label: "服務地址",
    value: "台南市東區大學路一段 168 號",
    display_value: "台南市東區大學路一段 168 號",
    note: "沿用你上次填的資料",
  },
  {
    type: "fill",
    field_id: "phone",
    label: "聯絡電話",
    value: "0912345678",
    display_value: "0912345678",
    note: "沿用你上次填的資料",
  },
];

/** 代替 AI 管家面板：把 Agent 回傳的 form_actions 丟給表單，並可讀出要送給 Agent 的表單快照。 */
function AgentRunner({ actions = ACTIONS }: { actions?: FormAction[] }) {
  const { run, getFormContext } = useFormAgent();
  const [snapshot, setSnapshot] = useState("null");
  return (
    <>
      <button type="button" onClick={() => void run(actions, "air_conditioner_cleaning")}>
        模擬 AI 代填
      </button>
      <button type="button" onClick={() => setSnapshot(JSON.stringify(getFormContext()))}>
        讀取表單快照
      </button>
      <p data-testid="snapshot">{snapshot}</p>
    </>
  );
}

function renderFormWithAgent(actions?: FormAction[], stepDelayMs = 0) {
  return render(
    <FormAgentProvider stepDelayMs={stepDelayMs}>
      <MemoryRouter initialEntries={["/services/air_conditioner_cleaning"]}>
        <Routes>
          <Route
            path="/services/:serviceId"
            element={
              <>
                <ServiceFormPage />
                <AgentRunner actions={actions} />
              </>
            }
          />
        </Routes>
      </MemoryRouter>
    </FormAgentProvider>,
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

describe("ServiceFormPage 被 AI 管家代操", () => {
  it("fills every field the agent sends, including split address parts", async () => {
    const user = userEvent.setup();
    renderFormWithAgent();

    await user.click(screen.getByRole("button", { name: "模擬 AI 代填" }));

    await waitFor(() => expect(screen.getByLabelText("聯絡電話")).toHaveValue("0912345678"));
    expect(screen.getByLabelText("冷氣數量")).toHaveValue(2);
    expect(screen.getByLabelText("冷氣機種")).toHaveValue("壁掛式");
    expect(screen.getByLabelText("是否加購日本抗菌膜")).toHaveValue("NO");
    expect(screen.getByLabelText("服務日期")).toHaveValue("2026-08-10");
    expect(screen.getByLabelText("服務時間")).toHaveValue("15:00");
    // 一整串地址要拆進三個控制項
    expect(screen.getByLabelText("服務地址縣市")).toHaveValue("台南市");
    expect(screen.getByLabelText("服務地址鄉鎮市區")).toHaveValue("東區");
    expect(screen.getByLabelText("服務地址詳細地址")).toHaveValue("大學路一段 168 號");
  });

  it("marks the filled fields so the user can see what the agent touched", async () => {
    const user = userEvent.setup();
    renderFormWithAgent();

    await user.click(screen.getByRole("button", { name: "模擬 AI 代填" }));

    await waitFor(() => expect(screen.getAllByText("AI 已填")).toHaveLength(ACTIONS.length));
  });

  it("highlights one field at a time while filling", async () => {
    const user = userEvent.setup();
    renderFormWithAgent(ACTIONS.slice(0, 2), 30);

    await user.click(screen.getByRole("button", { name: "模擬 AI 代填" }));

    await waitFor(() => expect(screen.getByText("AI 填寫中")).toBeInTheDocument());
    expect(document.querySelectorAll('[data-agent-state="filling"]')).toHaveLength(1);
    expect(screen.getByRole("status")).toHaveTextContent("AI 管家代填中");

    // 跑完之後高亮收掉，只留下「AI 已填」標記
    await waitFor(() => expect(screen.queryByText("AI 填寫中")).not.toBeInTheDocument());
    expect(screen.getAllByText("AI 已填")).toHaveLength(2);
  });

  it("keeps the form submittable with the values the agent filled in", async () => {
    const user = userEvent.setup();
    renderFormWithAgent();

    await user.click(screen.getByRole("button", { name: "模擬 AI 代填" }));
    await waitFor(() => expect(screen.getByLabelText("聯絡電話")).toHaveValue("0912345678"));

    await user.click(screen.getByRole("button", { name: "送出服務需求" }));

    await waitFor(() =>
      expect(servicesApi.createServiceRequest).toHaveBeenCalledWith(
        "air_conditioner_cleaning",
        expect.objectContaining({
          quantity: 2,
          air_conditioner_type: "壁掛式",
          antibacterial_film_addon: "NO",
          preferred_date: "2026-08-10",
          preferred_time_slot: "15:00",
          address: "台南市東區大學路一段 168 號",
          phone: "0912345678",
        }),
      ),
    );
  });

  it("refuses a select value that is not one of the options and says so", async () => {
    const user = userEvent.setup();
    renderFormWithAgent([
      {
        type: "fill",
        field_id: "air_conditioner_type",
        label: "冷氣機種",
        value: "水冷式",
        display_value: "水冷式",
        note: null,
      },
    ]);

    await user.click(screen.getByRole("button", { name: "模擬 AI 代填" }));

    // 填不進去就不能標「AI 已填」，而且要告訴使用者這格要自己選
    await waitFor(() => expect(screen.getByText(/需要你自己選一下/)).toBeInTheDocument());
    expect(screen.getByLabelText("冷氣機種")).toHaveValue("");
    expect(screen.queryByText("AI 已填")).not.toBeInTheDocument();
  });

  it("reports what is really on screen back to the agent", async () => {
    const user = userEvent.setup();
    renderFormWithAgent();

    await user.type(screen.getByLabelText("冷氣數量"), "3");
    await user.click(screen.getByRole("button", { name: "讀取表單快照" }));

    const payload = JSON.parse(screen.getByTestId("snapshot").textContent ?? "null");
    expect(payload.service_id).toBe("air_conditioner_cleaning");
    expect(payload.values.quantity).toBe("3");
    // 空欄位也要回報（空字串），Agent 才知道哪幾格還沒填、哪幾格被清掉
    expect(payload.values.phone).toBe("");
  });

  it("shows where a reused value came from", async () => {
    const user = userEvent.setup();
    renderFormWithAgent([
      {
        type: "fill",
        field_id: "phone",
        label: "聯絡電話",
        value: "0912345678",
        display_value: "0912345678",
        note: "沿用你上次填的資料",
      },
    ]);

    await user.click(screen.getByRole("button", { name: "模擬 AI 代填" }));

    await waitFor(() => expect(screen.getByText("沿用你上次填的資料")).toBeInTheDocument());
  });

  it("does not fill a field that is currently hidden by visibleWhen", async () => {
    const user = userEvent.setup();
    renderFormWithAgent([
      {
        type: "fill",
        field_id: "antibacterial_film_quantity",
        label: "日本抗菌膜數量",
        value: "3",
        display_value: "3 個",
        note: null,
      },
    ]);

    await user.click(screen.getByRole("button", { name: "模擬 AI 代填" }));

    await waitFor(() => expect(screen.getByText(/需要你自己選一下/)).toBeInTheDocument());
    expect(screen.queryByLabelText("日本抗菌膜數量")).not.toBeInTheDocument();
  });
});
