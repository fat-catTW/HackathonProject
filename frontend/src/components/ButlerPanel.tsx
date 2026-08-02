import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { sendMessage } from "../api/chat";
import { ApiError, getToken } from "../api/client";
import type { ChatEvent } from "../types/request";
import { buildFieldRows } from "../utils/fieldLabels";
import { BottomNav } from "./BottomNav";
import { ChatMessage } from "./ChatMessage";
import { FieldPanel } from "./FieldPanel";
import { GlassPanel } from "./GlassPanel";
import { Mascot } from "./Mascot";
import { ServiceIcon } from "./ServiceIcon";
import { Toast } from "./Toast";
import { VoiceButton } from "./VoiceButton";
import { useFormAgent } from "../hooks/useFormAgent";
import {
  appendButlerEvent,
  ensureButlerSession,
  resetButlerConversation,
  saveButlerTurn,
  useButlerConversation,
} from "../hooks/useButlerConversation";
import { useSpeechRecognition } from "../hooks/useSpeechRecognition";
import { useSpeechSynthesis } from "../hooks/useSpeechSynthesis";
import type { SpeechLanguage } from "../api/speech";

const REPLY_SPEECH_STORAGE_KEY = "ai-butler-read-replies";

interface ButlerPanelProps {
  autoMessage?: string;
  onClose?: () => void;
  overlay?: boolean;
  currentPageId?: string;
}

export function ButlerPanel({
  autoMessage,
  onClose,
  overlay = false,
  currentPageId,
}: ButlerPanelProps) {
  const navigate = useNavigate();
  const formAgent = useFormAgent();
  const { sessionId, events, serviceName, collected, missing, status } = useButlerConversation();
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [speechLanguage, setSpeechLanguage] = useState<SpeechLanguage>("zh");
  const [readRepliesEnabled, setReadRepliesEnabled] = useState(() => {
    try {
      return localStorage.getItem(REPLY_SPEECH_STORAGE_KEY) === "true";
    } catch {
      return false;
    }
  });
  const [toastText, setToastText] = useState<string | null>(null);
  const [sessionError, setSessionError] = useState<string | null>(null);
  const autoSentRef = useRef(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const timersRef = useRef<ReturnType<typeof setTimeout>[]>([]);
  const {
    supported: replySpeechSupported,
    speak: speakReply,
    stop: stopReplySpeech,
  } = useSpeechSynthesis();

  /**
   * 開一段對話。失敗時要分清楚兩種情況，否則使用者只會看到畫面閃一下就回首頁：
   *
   * - **真的沒登入**：api/client 收到 401 時已經把 token 清掉了，所以「token 不見了」
   *   就是後端說未授權。這時導去登入頁是對的，LoginPage 也不會再把人彈回來。
   * - **其他失敗**（後端 500、AWS 憑證過期、斷網）：token 還好好的，導去登入頁只會被
   *   LoginPage 的「已登入就回首頁」立刻彈回去，使用者完全不知道發生什麼事——
   *   這正是 AgentCore Memory 掛掉那次，點任何管家入口都「閃退回首頁」的原因。
   *   留在原地把話說清楚，並給一個重試按鈕。
   */
  const startSession = useCallback(() => {
    setSessionError(null);
    return ensureButlerSession()
      .then(() => undefined)
      .catch(() => {
        if (!getToken()) {
          navigate("/login");
          return;
        }
        // 不轉述後端訊息：這條路上的錯誤本體是純文字的 "Internal Server Error"，
        // 對使用者來說等同亂碼，不如講清楚「哪裡壞了、還能做什麼」。
        setSessionError(
          "現在連不上 AI 管家，可能是網路或伺服器忙線。稍後再試一次，其他功能都還能正常使用。",
        );
      });
  }, [navigate]);

  useEffect(() => {
    // 換人登入時 ensureButlerSession 會把整段對話重來，畫面靠 store 訂閱自動跟上。
    void startSession();
  }, [startSession]);

  // 面板關掉（或換頁）之後不該再自己導頁——這些延遲只是為了讓使用者看完 Toast。
  useEffect(
    () => () => {
      timersRef.current.forEach(clearTimeout);
      timersRef.current = [];
    },
    [],
  );

  useEffect(() => {
    try {
      localStorage.setItem(REPLY_SPEECH_STORAGE_KEY, String(readRepliesEnabled));
    } catch {
      /* ignore write failures (private browsing, quota) */
    }
    if (!readRepliesEnabled) stopReplySpeech();
  }, [readRepliesEnabled, stopReplySpeech]);

  function later(run: () => void, delayMs: number) {
    timersRef.current.push(setTimeout(run, delayMs));
  }

  useEffect(() => {
    // block/inline: "nearest" 限制只捲動訊息串自己的 overflow-y-auto 容器，不加這兩個
    // 選項時 scrollIntoView 的預設對齊方式在某些情況下會連同外層（window）一起捲，
    // 剛好在這個元件「一掛載就有初始訊息」時最容易觸發——一進 AI 管家頁面（events 從
    // 空陣列變成有一筆訊息）就整個視窗跳走、把上面的返回鈕捲出畫面外。
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "nearest" });
  }, [events]);

  async function send(text: string) {
    const message = text.trim();
    if (!message || !sessionId || sending) return;

    setInput("");
    setSending(true);
    appendButlerEvent({ role: "USER", content: message });

    try {
      const r = await sendMessage(sessionId, message, currentPageId, formAgent.getFormContext());
      const showsRedirectButton = Boolean(r.redirect_path) && r.redirect_requires_confirmation;
      appendButlerEvent({
        role: "ASSISTANT",
        content: r.reply,
        redirectPath: showsRedirectButton ? r.redirect_path! : undefined,
        taskCards: r.task_cards ?? undefined,
        restaurantCards: r.restaurant_cards ?? undefined,
        shareText: r.share_text ?? undefined,
        clinicRecommendation: r.clinic_recommendation ?? undefined,
        redirectLabel:
          showsRedirectButton && r.product_recommendations?.length ? "前往商城選購 →" : undefined,
        productRecommendations: r.product_recommendations ?? undefined,
      });
      if (readRepliesEnabled && replySpeechSupported) {
        speakReply(r.reply);
      }
      saveButlerTurn({
        sessionId: r.session_id,
        serviceName: r.service_name,
        collected: r.collected_fields,
        missing: r.missing_fields,
        status: r.status,
      });

      if (r.request_id) {
        // 立刻重置，不要放在延遲裡：使用者在 Toast 跑完前自己關掉面板的話，
        // 這段對話就會永遠停在「已送出案件」的狀態，之後說「幫我填」只會得到頁面說明。
        resetButlerConversation();
        setToastText("服務案件已建立，正在帶你前往明細頁。");
        later(() => {
          onClose?.();
          navigate(`/requests/${r.request_id}`);
        }, 900);
      } else if (r.form_actions?.length) {
        // 代操表單：先把面板收起來（不然整張表單被蓋住），必要時導到表單頁，
        // 再交給 FormAgentProvider 逐格高亮填入。
        const actions = r.form_actions;
        const targetServiceId = r.service_id;
        const redirectPath = r.redirect_path;
        setToastText("AI 管家開始幫你填表單。");
        later(() => {
          onClose?.();
          if (redirectPath) navigate(redirectPath);
          void formAgent.run(actions, targetServiceId);
        }, 700);
      } else if (r.redirect_path && !r.redirect_requires_confirmation) {
        setToastText("正在帶你前往專屬頁面。");
        later(() => {
          onClose?.();
          navigate(r.redirect_path!);
        }, 900);
      }
    } catch (error) {
      if (error instanceof ApiError && error.code === "SESSION_NOT_FOUND") {
        // 後端重啟或 session 過期：換一段新對話，不要卡在一個永遠 404 的 session id。
        resetButlerConversation();
        void startSession();
        appendButlerEvent({
          role: "ASSISTANT",
          content: "剛剛的對話連線過期了，我已經重新開始一段對話，請再說一次你的需求。",
        });
      } else {
        appendButlerEvent({
          role: "ASSISTANT",
          content: "剛剛連線有點問題，請再描述一次需求，我會繼續幫你整理。",
        });
      }
    } finally {
      setSending(false);
    }
  }

  useEffect(() => {
    if (autoMessage && sessionId && !autoSentRef.current) {
      autoSentRef.current = true;
      void send(autoMessage);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoMessage, sessionId]);

  const speech = useSpeechRecognition((text) => void send(text), speechLanguage);
  const isConfirming = status === "AWAITING_USER_CONFIRMATION" && missing.length === 0;
  const closeLabel = overlay ? "關閉" : "返回";

  useEffect(() => {
    if (speech.error) setToastText(speech.error);
  }, [speech.error]);

  function handleClose() {
    if (onClose) {
      onClose();
      return;
    }
    navigate("/home");
  }

  return (
    /*
      Overlay 模式改吃 `.glass-panel`（GlassPanel 所封裝的同一組共用樣式），取代原本手寫的
      深藍黑半透明底 + backdrop-blur-xl + 白色半透明覆蓋層等內嵌色值（Requirement 9.4、13.7）。
      這裡直接套用 class 而非改用 <GlassPanel>，是為了保留 <section> 語意標籤並讓 DOM 結構
      與層數完全不變；Light/Dark 兩套玻璃參數與 @supports fallback 一律由 index.css 負責。

      非 overlay 模式為整頁呈現，用 `--color-canvas` 底 + 不透明卡片（Requirement 13.8）。
      因為兩模式的文字色都由 `--color-foreground` 提供，overlay 分支不再需要成對的
      白色文字覆寫。
    */
    <section
      className={
        overlay
          ? "glass-panel mx-auto flex h-dvh w-full max-w-md flex-col overflow-hidden text-[var(--color-foreground)] sm:h-[88dvh] sm:max-h-[88dvh] sm:rounded-[32px] sm:shadow-2xl"
          : "bg-blob-scene mx-auto flex h-dvh max-w-md flex-col overflow-hidden text-[var(--color-foreground)]"
      }
    >
      <header
        className={`relative shrink-0 flex items-center justify-between border-b border-[var(--color-border)] px-5 py-4.5 ${
          overlay ? "bg-transparent" : "bg-[var(--color-surface)]"
        }`}
      >
        <button
          type="button"
          onClick={handleClose}
          className="flex items-center gap-1.5 text-base font-semibold text-[var(--color-muted-foreground)]"
        >
          <ServiceIcon type={overlay ? "close" : "back"} size={20} />
          {closeLabel}
        </button>
        <div className="absolute left-1/2 top-1/2 flex -translate-x-1/2 -translate-y-1/2 items-center gap-2">
          <Mascot size={26} tone="brand" />
          <span className="text-base font-black text-[var(--color-foreground)]">
            {serviceName ?? "AI 管家"}
          </span>
        </div>
        <button
          type="button"
          role="switch"
          aria-checked={readRepliesEnabled}
          aria-label="朗讀 AI 回覆"
          disabled={!replySpeechSupported}
          onClick={() => setReadRepliesEnabled((enabled) => !enabled)}
          className="absolute right-5 top-1/2 flex -translate-y-1/2 items-center gap-1.5 rounded-lg px-1 py-1 text-left disabled:opacity-50"
        >
          <span className="text-xs font-bold text-[var(--color-muted-foreground)]">
            朗讀回覆
          </span>
          <span
            className={`relative h-5 w-9 shrink-0 rounded-full transition-colors ${
              readRepliesEnabled ? "bg-[var(--color-primary)]" : "bg-[var(--color-border)]"
            }`}
            aria-hidden
          >
            <span
              className={`absolute top-[3px] h-3.5 w-3.5 rounded-full bg-[var(--color-on-primary)] shadow-sm transition-transform ${
                readRepliesEnabled ? "translate-x-[18px]" : "translate-x-[3px]"
              }`}
            />
          </span>
        </button>
        <div className="w-12" />
      </header>

      {isConfirming ? (
        <div className="min-h-0 flex-1 overflow-y-auto p-6">
          <div className="flex flex-col gap-5">
            {/* 說明橫幅：資訊語意，用 info soft 底（該配對已由 contrast.test.ts 驗證） */}
            <div className="flex items-start gap-3.5 rounded-2xl border border-[var(--color-border)] bg-[var(--color-info-soft)] p-4.5">
              <ServiceIcon type="info" size={24} className="flex-none text-[var(--color-info)]" />
              <div className="text-sm leading-relaxed">
                <strong className="font-extrabold">請確認以下申請內容。</strong>
                <br />
                如果內容沒問題，按下確認送出即可；如果想修改，也可以回到對話再補充。
              </div>
            </div>

            {/* 最終確認摘要卡：流程終點的重點卡片，套 GlassPanel 強調（Requirement 13.6、15.1） */}
            <GlassPanel className="rounded-3xl p-6 shadow-sm">
              <div className="mb-5 flex items-center gap-3.5 border-b border-[var(--color-border)] pb-5">
                <span className="flex h-13 w-13 items-center justify-center rounded-2xl bg-[var(--color-primary-soft)] text-[var(--color-primary)]">
                  <ServiceIcon type="chat" size={26} />
                </span>
                <span className="text-xl font-extrabold">{serviceName}</span>
              </div>
              {buildFieldRows(collected).map((row) => (
                <div key={row.key} className="flex justify-between gap-4 py-2.5 text-base">
                  <span className="text-[var(--color-muted-foreground)]">{row.label}</span>
                  <span className="text-right font-bold">{row.value}</span>
                </div>
              ))}
            </GlassPanel>

            <button
              type="button"
              onClick={() => void send("確認送出")}
              disabled={sending}
              className="w-full rounded-2xl bg-[var(--color-primary)] py-5 text-lg font-bold text-[var(--color-on-primary)] disabled:opacity-40"
            >
              確認送出
            </button>
            <button
              type="button"
              onClick={() => saveButlerTurn({ status: "COLLECTING_INFORMATION", missing: ["_edit"] })}
              className="w-full rounded-2xl border-2 border-[var(--color-border)] py-4.5 text-base font-bold text-[var(--color-muted-foreground)]"
            >
              返回修改
            </button>
          </div>
        </div>
      ) : (
        <>
          <div className="min-h-0 flex-1 overflow-y-auto bg-transparent p-5">
            <div className="space-y-3.5">
              {events.map((e, i) => (
                <ChatMessage
                  key={i}
                  event={e}
                  onRedirectClick={(path) => {
                    onClose?.();
                    navigate(path);
                  }}
                  onRestaurantSelect={(name) => void send(name)}
                  onClinicContinue={(recommendation, clinicId) => {
                    onClose?.();
                    navigate("/services/clinic_appointment", {
                      state: {
                        symptomNote: recommendation.symptom_note,
                        city: recommendation.city,
                        district: recommendation.district,
                        advisory: recommendation.advisory,
                        clinics: recommendation.clinics,
                        recommendedClinicId: recommendation.recommended_clinic_id,
                        recommendReason: recommendation.recommend_reason,
                        selectedClinicId: clinicId,
                      },
                    });
                  }}
                />
              ))}
              {sending && (
                <p className="text-sm text-[var(--color-muted-foreground)]">AI 管家整理中…</p>
              )}
              {sessionError && (
                <div
                  role="alert"
                  className="flex items-start gap-3 rounded-2xl border border-[var(--color-border)] bg-[var(--color-warning-soft)] p-4"
                >
                  <ServiceIcon
                    type="warning"
                    size={22}
                    className="mt-0.5 flex-none text-[var(--color-warning)]"
                  />
                  <div className="min-w-0 flex-1">
                    <p className="text-sm leading-relaxed">{sessionError}</p>
                    <button
                      type="button"
                      onClick={() => void startSession()}
                      className="mt-3 inline-flex min-h-[40px] items-center rounded-full bg-[var(--color-primary)] px-4 text-sm font-bold text-[var(--color-on-primary)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]"
                    >
                      重新連線
                    </button>
                  </div>
                </div>
              )}
              <div ref={bottomRef} />
            </div>
          </div>

          <div className="shrink-0">
            <FieldPanel collected={collected} missing={missing.filter((m) => m !== "_edit")} />
          </div>

          <form
            className={`shrink-0 flex items-center gap-3 border-t border-[var(--color-border)] p-4 ${
              overlay ? "bg-transparent" : "bg-[var(--color-surface)]"
            }`}
            onSubmit={(e) => {
              e.preventDefault();
              void send(input);
            }}
          >
            <VoiceButton
              listening={speech.listening || speech.transcribing}
              supported={speech.supported}
              onStart={speech.start}
              onStop={speech.stop}
            />
            <select
              value={speechLanguage}
              onChange={(e) => setSpeechLanguage(e.target.value as SpeechLanguage)}
              disabled={speech.listening || speech.transcribing || sending}
              aria-label="語音語言"
              className="h-12 shrink-0 rounded-2xl border-2 border-[var(--color-border)] bg-[var(--color-surface)] px-2 text-sm font-bold text-[var(--color-foreground)] outline-none focus:border-[var(--color-primary)] disabled:opacity-50"
            >
              <option value="zh">中文</option>
              <option value="nan">台語</option>
            </select>
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={!!sessionError}
              placeholder={
                sessionError
                  ? "連線中斷，請先重新連線"
                  : speech.listening
                    ? "正在聆聽，請直接說出需求"
                    : "輸入需求，或描述你想預約的服務"
              }
              aria-label="輸入需求"
              className="min-w-0 flex-1 rounded-2xl border-2 border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-3.5 text-[var(--color-foreground)] outline-none placeholder:text-[var(--color-muted-foreground)] focus:border-[var(--color-primary)] disabled:opacity-60"
            />
            <button
              type="submit"
              disabled={sending || !input.trim() || !!sessionError}
              aria-label="送出"
              className="bg-bubble-user flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl text-[var(--color-on-primary)] disabled:opacity-40"
            >
              <ServiceIcon type="send" size={20} />
            </button>
          </form>
        </>
      )}

      {!overlay && <BottomNav variant="static" />}

      <Toast text={toastText} onHide={() => setToastText(null)} />
    </section>
  );
}
