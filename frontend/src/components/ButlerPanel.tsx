import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { createSession, sendMessage } from "../api/chat";
import type { ChatEvent } from "../types/request";
import { buildFieldRows, type CollectedFieldValue } from "../utils/fieldLabels";
import { ChatMessage } from "./ChatMessage";
import { FieldPanel } from "./FieldPanel";
import { ServiceIcon } from "./ServiceIcon";
import { Toast } from "./Toast";
import { VoiceButton } from "./VoiceButton";
import { useSpeechRecognition } from "../hooks/useSpeechRecognition";

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
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [events, setEvents] = useState<ChatEvent[]>([
    {
      role: "ASSISTANT",
      content: "您好，我是 AI 管家。請直接告訴我您想申請什麼服務，例如冷氣清洗、居家清潔或水電修繕。",
    },
  ]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [serviceName, setServiceName] = useState<string | null>(null);
  const [collected, setCollected] = useState<Record<string, CollectedFieldValue>>({});
  const [missing, setMissing] = useState<string[]>([]);
  const [status, setStatus] = useState<string>("COLLECTING_INFORMATION");
  const [toastText, setToastText] = useState<string | null>(null);
  const autoSentRef = useRef(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    createSession()
      .then((r) => setSessionId(r.session_id))
      .catch(() => navigate("/login"));
  }, [navigate]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [events]);

  async function send(text: string) {
    const message = text.trim();
    if (!message || !sessionId || sending) return;

    setInput("");
    setSending(true);
    setEvents((prev) => [...prev, { role: "USER", content: message }]);

    try {
      const r = await sendMessage(sessionId, message, currentPageId);
      setEvents((prev) => [...prev, { role: "ASSISTANT", content: r.reply }]);
      setServiceName(r.service_name);
      setCollected(r.collected_fields);
      setMissing(r.missing_fields);
      setStatus(r.status);

      if (r.request_id) {
        setToastText("服務案件已建立，正在帶你前往明細頁。");
        setTimeout(() => {
          onClose?.();
          navigate(`/requests/${r.request_id}`);
        }, 900);
      }
    } catch {
      setEvents((prev) => [
        ...prev,
        { role: "ASSISTANT", content: "剛剛連線有點問題，請再描述一次需求，我會繼續幫你整理。" },
      ]);
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

  const speech = useSpeechRecognition((text) => void send(text));
  const isConfirming = status === "AWAITING_USER_CONFIRMATION" && missing.length === 0;
  const closeLabel = overlay ? "關閉" : "返回";

  function handleClose() {
    if (onClose) {
      onClose();
      return;
    }
    navigate("/home");
  }

  return (
    <section
      className={
        overlay
          ? "mx-auto flex h-dvh w-full max-w-md flex-col overflow-hidden bg-[#0b1220]/92 backdrop-blur-xl sm:h-[88dvh] sm:max-h-[88dvh] sm:rounded-[32px] sm:border sm:border-white/10 sm:shadow-[0_40px_120px_rgba(0,0,0,0.48)]"
          : "mx-auto flex h-dvh max-w-md flex-col overflow-hidden bg-canvas"
      }
    >
      <header
        className={`shrink-0 flex items-center justify-between border-b px-5 py-4.5 ${
          overlay ? "border-white/10 bg-white/[0.06] text-white" : "border-gray-200 bg-white"
        }`}
      >
        <button
          type="button"
          onClick={handleClose}
          className={`flex items-center gap-1.5 text-base font-semibold ${
            overlay ? "text-white/75" : "text-gray-500"
          }`}
        >
          <ServiceIcon type={overlay ? "close" : "back"} size={20} />
          {closeLabel}
        </button>
        <div className={`text-base font-black ${overlay ? "text-white" : "text-ink"}`}>
          {serviceName ?? "AI 管家"}
        </div>
        <div className="w-12" />
      </header>

      {isConfirming ? (
        <div className={`min-h-0 flex-1 overflow-y-auto p-6 ${overlay ? "text-white" : ""}`}>
          <div className="flex flex-col gap-5">
            <div
              className={`flex items-start gap-3.5 rounded-2xl border p-4.5 ${
                overlay ? "border-brand/20 bg-brand/20 text-white" : "border-brand-soft bg-brand-soft"
              }`}
            >
              <ServiceIcon
                type="info"
                size={24}
                className={`flex-none ${overlay ? "text-white" : "text-brand"}`}
              />
              <div className="text-sm leading-relaxed">
                <strong className="font-extrabold">請確認以下申請內容。</strong>
                <br />
                如果內容沒問題，按下確認送出即可；如果想修改，也可以回到對話再補充。
              </div>
            </div>

            <div
              className={`rounded-3xl border p-6 shadow-sm ${
                overlay ? "border-white/10 bg-white text-ink" : "border-gray-200 bg-white"
              }`}
            >
              <div className="mb-5 flex items-center gap-3.5 border-b border-gray-100 pb-5">
                <span className="flex h-13 w-13 items-center justify-center rounded-2xl bg-brand-soft text-brand">
                  <ServiceIcon type="chat" size={26} />
                </span>
                <span className="text-xl font-extrabold">{serviceName}</span>
              </div>
              {buildFieldRows(collected).map((row) => (
                <div key={row.key} className="flex justify-between gap-4 py-2.5 text-base">
                  <span className="text-gray-500">{row.label}</span>
                  <span className="text-right font-bold">{row.value}</span>
                </div>
              ))}
            </div>

            <button
              type="button"
              onClick={() => void send("確認送出")}
              disabled={sending}
              className="w-full rounded-2xl bg-brand py-5 text-lg font-bold text-white disabled:opacity-40"
            >
              確認送出
            </button>
            <button
              type="button"
              onClick={() => {
                setStatus("COLLECTING_INFORMATION");
                setMissing(["_edit"]);
              }}
              className={`w-full rounded-2xl border-2 py-4.5 text-base font-bold ${
                overlay ? "border-white/20 bg-white/10 text-white" : "border-gray-200 bg-white text-gray-500"
              }`}
            >
              返回修改
            </button>
          </div>
        </div>
      ) : (
        <>
          <div className={`min-h-0 flex-1 overflow-y-auto p-5 ${overlay ? "bg-transparent" : ""}`}>
            <div className="space-y-3.5">
              {events.map((e, i) => (
                <ChatMessage key={i} event={e} />
              ))}
              {sending && (
                <p className={`text-sm ${overlay ? "text-white/55" : "text-gray-400"}`}>
                  AI 管家整理中…
                </p>
              )}
              <div ref={bottomRef} />
            </div>
          </div>

          <div className="shrink-0">
            <FieldPanel collected={collected} missing={missing.filter((m) => m !== "_edit")} />
          </div>

          <form
            className={`shrink-0 flex items-center gap-3 border-t p-4 ${
              overlay ? "border-white/10 bg-black/20 backdrop-blur" : "border-gray-200 bg-white"
            }`}
            onSubmit={(e) => {
              e.preventDefault();
              void send(input);
            }}
          >
            <VoiceButton
              listening={speech.listening}
              supported={speech.supported}
              onStart={speech.start}
              onStop={speech.stop}
            />
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={
                speech.listening ? "正在聆聽，請直接說出需求" : "輸入需求，或描述你想預約的服務"
              }
              aria-label="輸入需求"
              className="min-w-0 flex-1 rounded-2xl border-2 border-gray-200 bg-white px-4 py-3.5 outline-none focus:border-brand"
            />
            <button
              type="submit"
              disabled={sending || !input.trim()}
              className="rounded-2xl bg-brand px-5 py-3.5 font-bold text-white disabled:opacity-40"
            >
              送出
            </button>
          </form>
        </>
      )}

      <Toast text={toastText} onHide={() => setToastText(null)} />
    </section>
  );
}
