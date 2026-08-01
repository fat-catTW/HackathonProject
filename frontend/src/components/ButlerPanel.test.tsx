import { useEffect } from "react";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter, useLocation } from "react-router-dom";
import { ButlerPanel } from "./ButlerPanel";
import { resetButlerConversation } from "../hooks/useButlerConversation";
import { FormAgentProvider, useFormAgent, type FormAgentController } from "../hooks/useFormAgent";
import type { ChatResponse } from "../types/request";
import * as chatApi from "../api/chat";
import * as clientApi from "../api/client";

vi.mock("../api/chat");
vi.mock("../api/client", async (importOriginal) => ({
  ...(await importOriginal<typeof clientApi>()),
  getToken: vi.fn(() => "demo-user-token"),
}));

const BASE_RESPONSE: ChatResponse = {
  session_id: "sess-1",
  reply: "好，我直接幫你填「冷氣清洗」。",
  service_id: "air_conditioner_cleaning",
  service_name: "冷氣清洗",
  collected_fields: {},
  missing_fields: [],
  form_actions: [],
  request_id: null,
  status: "COLLECTING_INFORMATION",
  redirect_path: null,
  redirect_requires_confirmation: false,
  task_cards: null,
  restaurant_cards: null,
  share_text: null,
};

function buildController(): FormAgentController {
  return {
    serviceId: "air_conditioner_cleaning",
    hasField: () => true,
    focusField: vi.fn(),
    fillField: vi.fn(),
    getValues: () => ({ quantity: "2" }),
  };
}

/** 站在表單頁上的 AI 管家：表單已註冊，面板以覆蓋層開著。 */
function FormPageWithButler({
  controller,
  onClose,
}: {
  controller: FormAgentController;
  onClose: () => void;
}) {
  const { register } = useFormAgent();
  useEffect(() => register(controller), [register, controller]);
  return (
    <ButlerPanel
      overlay
      currentPageId="service_form_air_conditioner_cleaning"
      onClose={onClose}
    />
  );
}

function renderPanel(controller: FormAgentController, onClose = vi.fn()) {
  render(
    <FormAgentProvider stepDelayMs={0}>
      <MemoryRouter>
        <FormPageWithButler controller={controller} onClose={onClose} />
      </MemoryRouter>
    </FormAgentProvider>,
  );
  return { onClose };
}

async function sendText(user: ReturnType<typeof userEvent.setup>, text: string) {
  await screen.findByLabelText("輸入需求");
  await user.type(screen.getByLabelText("輸入需求"), text);
  await user.click(screen.getByRole("button", { name: "送出" }));
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(clientApi.getToken).mockReturnValue("demo-user-token");
  resetButlerConversation();
  vi.mocked(chatApi.createSession).mockResolvedValue({
    session_id: "sess-1",
    created_at: "2026-08-01T00:00:00Z",
  });
  vi.mocked(chatApi.sendMessage).mockResolvedValue(BASE_RESPONSE);
});

describe("ButlerPanel 代操表單", () => {
  it("sends the on-screen form snapshot with every message", async () => {
    const user = userEvent.setup();
    renderPanel(buildController());

    await sendText(user, "幫我填");

    await waitFor(() =>
      expect(chatApi.sendMessage).toHaveBeenCalledWith(
        "sess-1",
        "幫我填",
        "service_form_air_conditioner_cleaning",
        { service_id: "air_conditioner_cleaning", values: { quantity: "2" } },
      ),
    );
  });

  it("closes itself and drives the form when the agent returns fill actions", async () => {
    const user = userEvent.setup();
    const controller = buildController();
    vi.mocked(chatApi.sendMessage).mockResolvedValue({
      ...BASE_RESPONSE,
      form_actions: [
        {
          type: "fill",
          field_id: "phone",
          label: "聯絡電話",
          value: "0912345678",
          display_value: "0912345678",
          note: null,
        },
      ],
    });
    const { onClose } = renderPanel(controller);

    await sendText(user, "幫我填");

    // 面板要先收起來，使用者才看得到表單被逐格填寫
    await waitFor(() => expect(onClose).toHaveBeenCalled(), { timeout: 3000 });
    await waitFor(() => expect(controller.fillField).toHaveBeenCalledWith("phone", "0912345678"));
  });

  it("navigates to the target form first, then fills it", async () => {
    const user = userEvent.setup();
    const controller = buildController();
    vi.mocked(chatApi.sendMessage).mockResolvedValue({
      ...BASE_RESPONSE,
      redirect_path: "/services/air_conditioner_cleaning",
      form_actions: [
        {
          type: "fill",
          field_id: "quantity",
          label: "冷氣數量",
          value: "2",
          display_value: "2 台",
          note: null,
        },
      ],
    });

    // 表單頁在導頁之後才掛載，代填佇列必須撐過這次換頁
    function LateRegisteredForm() {
      const { register } = useFormAgent();
      const location = useLocation();
      const onForm = location.pathname === "/services/air_conditioner_cleaning";
      useEffect(() => {
        if (!onForm) return;
        return register(controller);
      }, [register, onForm]);
      return null;
    }

    render(
      <FormAgentProvider stepDelayMs={0}>
        <MemoryRouter initialEntries={["/home"]}>
          <LateRegisteredForm />
          <ButlerPanel overlay currentPageId="home" onClose={vi.fn()} />
        </MemoryRouter>
      </FormAgentProvider>,
    );

    await sendText(user, "幫我填冷氣清洗");

    await waitFor(() => expect(controller.fillField).toHaveBeenCalledWith("quantity", "2"), {
      timeout: 3000,
    });
  });

  it("starts a fresh conversation when a different account signs in", async () => {
    const user = userEvent.setup();
    renderPanel(buildController());

    await sendText(user, "幫我填");
    await screen.findByText("好，我直接幫你填「冷氣清洗」。");

    // 換人登入：上一位的對話與聯絡資訊不能留在畫面上
    vi.mocked(clientApi.getToken).mockReturnValue("another-user-token");
    cleanup();
    renderPanel(buildController());

    expect(await screen.findByText(/我是 AI 管家/)).toBeInTheDocument();
    expect(screen.queryByText("好，我直接幫你填「冷氣清洗」。")).not.toBeInTheDocument();
  });

  it("keeps the conversation when the panel is closed and reopened", async () => {
    const user = userEvent.setup();
    const { unmount } = render(
      <FormAgentProvider stepDelayMs={0}>
        <MemoryRouter>
          <ButlerPanel overlay currentPageId="service_form_air_conditioner_cleaning" />
        </MemoryRouter>
      </FormAgentProvider>,
    );

    await sendText(user, "幫我填");
    await screen.findByText("好，我直接幫你填「冷氣清洗」。");
    unmount();

    render(
      <FormAgentProvider stepDelayMs={0}>
        <MemoryRouter>
          <ButlerPanel overlay currentPageId="service_form_air_conditioner_cleaning" />
        </MemoryRouter>
      </FormAgentProvider>,
    );

    expect(await screen.findByText("好，我直接幫你填「冷氣清洗」。")).toBeInTheDocument();
    // 重新掛載不該再開一個新 session
    expect(chatApi.createSession).toHaveBeenCalledTimes(1);
  });
});
