import { useEffect } from "react";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
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

const originalSpeechSynthesis = window.speechSynthesis;
const originalUtterance = window.SpeechSynthesisUtterance;
let speakMock: ReturnType<typeof vi.fn>;
let cancelMock: ReturnType<typeof vi.fn>;

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
  clinic_recommendation: null,
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
  localStorage.clear();
  speakMock = vi.fn();
  cancelMock = vi.fn();
  Object.defineProperty(window, "speechSynthesis", {
    value: { speak: speakMock, cancel: cancelMock, speaking: false },
    writable: true,
    configurable: true,
  });
  const MockUtterance = class {
    text: string;
    lang: string = "";
    onend: (() => void) | null = null;
    onerror: (() => void) | null = null;
    constructor(text: string) {
      this.text = text;
    }
  };
  Object.defineProperty(window, "SpeechSynthesisUtterance", {
    value: MockUtterance,
    writable: true,
    configurable: true,
  });
  vi.mocked(clientApi.getToken).mockReturnValue("demo-user-token");
  resetButlerConversation();
  vi.mocked(chatApi.createSession).mockResolvedValue({
    session_id: "sess-1",
    created_at: "2026-08-01T00:00:00Z",
  });
  vi.mocked(chatApi.sendMessage).mockResolvedValue(BASE_RESPONSE);
});

afterEach(() => {
  Object.defineProperty(window, "speechSynthesis", { value: originalSpeechSynthesis, configurable: true });
  Object.defineProperty(window, "SpeechSynthesisUtterance", { value: originalUtterance, configurable: true });
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

  it("does not read AI replies aloud by default", async () => {
    const user = userEvent.setup();
    renderPanel(buildController());

    await sendText(user, "幫我填");

    await waitFor(() => expect(chatApi.sendMessage).toHaveBeenCalled());
    expect(speakMock).not.toHaveBeenCalled();
  });

  it("reads the latest AI reply aloud when enabled", async () => {
    const user = userEvent.setup();
    renderPanel(buildController());

    await user.click(await screen.findByRole("switch", { name: "朗讀 AI 回覆" }));
    await sendText(user, "幫我填");

    await waitFor(() => expect(speakMock).toHaveBeenCalledTimes(1));
    const utterance = speakMock.mock.calls[0][0];
    expect(utterance.text).toBe(BASE_RESPONSE.reply);
    expect(utterance.lang).toBe("zh-TW");
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

/**
 * 開對話失敗時的行為。
 *
 * 這組測試守的是一個真的發生過的事故：AWS 那邊的 AgentCore Memory 掛掉，
 * POST /api/sessions 一路回 500，而前端不分青紅皂白 navigate("/login")，
 * 登入頁看到人還登著又把他彈回首頁——使用者只看到畫面閃一下就回到首頁，
 * 沒有任何錯誤訊息，完全無從得知發生什麼事，也查不出原因。
 */
describe("ButlerPanel 連線失敗", () => {
  /** 顯示目前路徑，讓測試能斷言有沒有被導走。 */
  function LocationProbe() {
    const { pathname } = useLocation();
    return <span data-testid="path">{pathname}</span>;
  }

  function renderAt(initialPath = "/new") {
    render(
      <FormAgentProvider stepDelayMs={0}>
        <MemoryRouter initialEntries={[initialPath]}>
          <ButlerPanel currentPageId="assistant" />
          <LocationProbe />
        </MemoryRouter>
      </FormAgentProvider>,
    );
  }

  it("stays put and explains itself when the backend is down", async () => {
    vi.mocked(chatApi.createSession).mockRejectedValue(
      new clientApi.ApiError("INTERNAL_ERROR", "HTTP 500"),
    );

    renderAt();

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("現在連不上 AI 管家");
    // 沒有被偷偷導走——這正是「閃退回首頁」的根源。
    expect(screen.getByTestId("path")).toHaveTextContent("/new");
  });

  it("blocks the composer instead of silently swallowing what the user types", async () => {
    vi.mocked(chatApi.createSession).mockRejectedValue(
      new clientApi.ApiError("INTERNAL_ERROR", "HTTP 500"),
    );

    renderAt();
    await screen.findByRole("alert");

    expect(screen.getByLabelText("輸入需求")).toBeDisabled();
    expect(screen.getByRole("button", { name: "送出" })).toBeDisabled();
  });

  it("recovers through 重新連線 once the backend is back", async () => {
    const user = userEvent.setup();
    vi.mocked(chatApi.createSession).mockRejectedValueOnce(
      new clientApi.ApiError("INTERNAL_ERROR", "HTTP 500"),
    );

    renderAt();
    await screen.findByRole("alert");

    await user.click(screen.getByRole("button", { name: "重新連線" }));

    await waitFor(() => expect(screen.queryByRole("alert")).not.toBeInTheDocument());
    expect(screen.getByLabelText("輸入需求")).toBeEnabled();
  });

  it("still sends the user to login when the session really is unauthorised", async () => {
    // api/client 收到 401 時會清掉 token，所以「token 不見了」就是後端說未授權。
    vi.mocked(chatApi.createSession).mockRejectedValue(
      new clientApi.ApiError("UNAUTHORIZED", "Invalid token."),
    );
    vi.mocked(clientApi.getToken).mockReturnValue(null);

    renderAt();

    await waitFor(() => expect(screen.getByTestId("path")).toHaveTextContent("/login"));
  });
});
