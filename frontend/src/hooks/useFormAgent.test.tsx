import { useEffect, useState } from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { FormAction } from "../types/request";
import { FormAgentProvider, useFormAgent, type FormAgentController } from "./useFormAgent";

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
    field_id: "phone",
    label: "聯絡電話",
    value: "0912345678",
    display_value: "0912345678",
    note: "沿用你上次填的資料",
  },
];

function buildController(overrides: Partial<FormAgentController> = {}): FormAgentController {
  return {
    serviceId: "air_conditioner_cleaning",
    hasField: () => true,
    focusField: vi.fn(),
    fillField: vi.fn(() => true),
    getValues: () => ({}),
    ...overrides,
  };
}

/** 假的表單頁：註冊 controller，並提供一顆按鈕觸發代填。 */
function FakeFormPage({
  controller,
  actions = ACTIONS,
  serviceId = "air_conditioner_cleaning",
}: {
  controller: FormAgentController;
  actions?: FormAction[];
  serviceId?: string | null;
}) {
  const { register, run, state, getFormContext } = useFormAgent();
  const [contextJson, setContextJson] = useState("null");

  useEffect(() => register(controller), [register, controller]);

  return (
    <div>
      <button type="button" onClick={() => void run(actions, serviceId)}>
        代填
      </button>
      <button type="button" onClick={() => setContextJson(JSON.stringify(getFormContext()))}>
        讀取表單快照
      </button>
      <p data-testid="active">{state.activeFieldId ?? "-"}</p>
      <p data-testid="filled">{state.filledFieldIds.join(",")}</p>
      <p data-testid="skipped">{state.skippedLabels.join(",")}</p>
      <p data-testid="running">{String(state.running)}</p>
      <p data-testid="context">{contextJson}</p>
    </div>
  );
}

describe("FormAgentProvider", () => {
  it("runs each action against the registered form", async () => {
    const user = userEvent.setup();
    const controller = buildController();

    render(
      <FormAgentProvider stepDelayMs={0}>
        <FakeFormPage controller={controller} />
      </FormAgentProvider>,
    );

    await user.click(screen.getByRole("button", { name: "代填" }));

    await waitFor(() => expect(screen.getByTestId("filled")).toHaveTextContent("quantity,phone"));
    expect(controller.fillField).toHaveBeenNthCalledWith(1, "quantity", "2");
    expect(controller.fillField).toHaveBeenNthCalledWith(2, "phone", "0912345678");
    expect(controller.focusField).toHaveBeenCalledWith("quantity");
  });

  it("keeps the filled markers but stops running once the queue is done", async () => {
    const user = userEvent.setup();

    render(
      <FormAgentProvider stepDelayMs={0}>
        <FakeFormPage controller={buildController()} />
      </FormAgentProvider>,
    );

    await user.click(screen.getByRole("button", { name: "代填" }));

    await waitFor(() => expect(screen.getByTestId("running")).toHaveTextContent("false"));
    expect(screen.getByTestId("filled")).toHaveTextContent("quantity,phone");
    expect(screen.getByTestId("active")).toHaveTextContent("-");
  });

  it("skips fields the current form does not have", async () => {
    const user = userEvent.setup();
    const controller = buildController({ hasField: (fieldId) => fieldId !== "phone" });

    render(
      <FormAgentProvider stepDelayMs={0}>
        <FakeFormPage controller={controller} />
      </FormAgentProvider>,
    );

    await user.click(screen.getByRole("button", { name: "代填" }));

    await waitFor(() => expect(controller.fillField).toHaveBeenCalledTimes(1));
    expect(controller.fillField).toHaveBeenCalledWith("quantity", "2");
  });

  it("clears a field when the agent removes its value", async () => {
    const user = userEvent.setup();
    const controller = buildController();
    const clearAction: FormAction[] = [
      {
        type: "clear",
        field_id: "notes",
        label: "備註",
        value: "",
        display_value: "",
        note: null,
      },
    ];

    render(
      <FormAgentProvider stepDelayMs={0}>
        <FakeFormPage controller={controller} actions={clearAction} />
      </FormAgentProvider>,
    );

    await user.click(screen.getByRole("button", { name: "代填" }));

    await waitFor(() => expect(controller.fillField).toHaveBeenCalledWith("notes", ""));
  });

  it("waits for the target form to mount after a redirect", async () => {
    const user = userEvent.setup();
    const controller = buildController();

    /** 模擬「在別的頁面說幫我填 → 導頁 → 表單頁才掛載」。 */
    function LateForm() {
      const { run, state } = useFormAgent();
      const [mounted, setMounted] = useState(false);

      return (
        <div>
          <button
            type="button"
            onClick={() => void run(ACTIONS, "air_conditioner_cleaning")}
          >
            代填
          </button>
          <button type="button" onClick={() => setMounted(true)}>
            導頁
          </button>
          <p data-testid="filled">{state.filledFieldIds.join(",")}</p>
          {mounted && <Registrar controller={controller} />}
        </div>
      );
    }

    function Registrar({ controller: target }: { controller: FormAgentController }) {
      const { register } = useFormAgent();
      useEffect(() => register(target), [register, target]);
      return null;
    }

    render(
      <FormAgentProvider stepDelayMs={0}>
        <LateForm />
      </FormAgentProvider>,
    );

    await user.click(screen.getByRole("button", { name: "代填" }));
    expect(controller.fillField).not.toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: "導頁" }));

    await waitFor(() => expect(screen.getByTestId("filled")).toHaveTextContent("quantity,phone"));
  });

  it("does not run against a form belonging to another service", async () => {
    const user = userEvent.setup();
    const controller = buildController({ serviceId: "home_cleaning" });

    render(
      <FormAgentProvider stepDelayMs={0} controllerWaitMs={50}>
        <FakeFormPage controller={controller} serviceId="air_conditioner_cleaning" />
      </FormAgentProvider>,
    );

    await user.click(screen.getByRole("button", { name: "代填" }));

    await waitFor(() => expect(screen.getByTestId("running")).toHaveTextContent("false"));
    expect(controller.fillField).not.toHaveBeenCalled();
  });

  it("does not mark a field as filled when the form refuses the value", async () => {
    const user = userEvent.setup();
    // 例如下拉選單沒有這個選項：表單會拒填，畫面就不能說「AI 已填」。
    const controller = buildController({
      fillField: vi.fn((fieldId: string) => fieldId !== "phone"),
    });

    render(
      <FormAgentProvider stepDelayMs={0}>
        <FakeFormPage controller={controller} />
      </FormAgentProvider>,
    );

    await user.click(screen.getByRole("button", { name: "代填" }));

    await waitFor(() => expect(screen.getByTestId("running")).toHaveTextContent("false"));
    expect(screen.getByTestId("filled")).toHaveTextContent("quantity");
    expect(screen.getByTestId("filled")).not.toHaveTextContent("phone");
    expect(screen.getByTestId("skipped")).toHaveTextContent("聯絡電話");
  });

  it("survives the form re-registering mid-run (StrictMode remount)", async () => {
    const user = userEvent.setup();
    const controller = buildController();

    function RemountingForm() {
      const { register, run, state } = useFormAgent();
      const [generation, setGeneration] = useState(0);
      // 每次 generation 變動就等於「卸載再掛載一次」：cleanup 不該中止進行中的佇列。
      useEffect(() => register(controller), [register, generation]);

      return (
        <div>
          <button type="button" onClick={() => void run(ACTIONS, "air_conditioner_cleaning")}>
            代填
          </button>
          <button type="button" onClick={() => setGeneration((value) => value + 1)}>
            重新註冊
          </button>
          <p data-testid="filled">{state.filledFieldIds.join(",")}</p>
        </div>
      );
    }

    render(
      <FormAgentProvider stepDelayMs={20}>
        <RemountingForm />
      </FormAgentProvider>,
    );

    await user.click(screen.getByRole("button", { name: "代填" }));
    await user.click(screen.getByRole("button", { name: "重新註冊" }));

    await waitFor(() => expect(screen.getByTestId("filled")).toHaveTextContent("quantity,phone"));
  });

  it("stops immediately when the user cancels", async () => {
    const user = userEvent.setup();
    const controller = buildController();

    function CancellableForm() {
      const { register, run, cancel, state } = useFormAgent();
      useEffect(() => register(controller), [register]);
      return (
        <div>
          <button type="button" onClick={() => void run(ACTIONS, "air_conditioner_cleaning")}>
            代填
          </button>
          <button type="button" onClick={cancel}>
            停止
          </button>
          <p data-testid="running">{String(state.running)}</p>
        </div>
      );
    }

    render(
      <FormAgentProvider stepDelayMs={200}>
        <CancellableForm />
      </FormAgentProvider>,
    );

    await user.click(screen.getByRole("button", { name: "代填" }));
    await user.click(screen.getByRole("button", { name: "停止" }));

    await waitFor(() => expect(screen.getByTestId("running")).toHaveTextContent("false"));
    expect(controller.fillField).not.toHaveBeenCalledWith("phone", "0912345678");
  });

  it("sends every known field as form context, keeping blanks and dropping photos", async () => {
    const user = userEvent.setup();
    const controller = buildController({
      getValues: () => ({
        quantity: "2",
        // 使用者清空的欄位要照送空字串，Agent 才知道那格被刪掉了
        blank: "   ",
        issue_photo: "data:image/png;base64,AAAA",
        notes: "x".repeat(500),
      }),
    });

    render(
      <FormAgentProvider stepDelayMs={0}>
        <FakeFormPage controller={controller} />
      </FormAgentProvider>,
    );

    await user.click(screen.getByRole("button", { name: "讀取表單快照" }));

    const payload = JSON.parse(screen.getByTestId("context").textContent ?? "null");
    expect(payload.service_id).toBe("air_conditioner_cleaning");
    expect(payload.values.quantity).toBe("2");
    expect(payload.values.blank).toBe("");
    expect(payload.values.issue_photo).toBeUndefined();
    expect(payload.values.notes).toHaveLength(200);
  });
});
