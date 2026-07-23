import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { createSession, sendMessage } from "../api/chat";
import { ChatMessage } from "../components/ChatMessage";
import { FieldPanel } from "../components/FieldPanel";
import { ServiceIcon } from "../components/ServiceIcon";
import { Toast } from "../components/Toast";
import { VoiceButton } from "../components/VoiceButton";
import { useSpeechRecognition } from "../hooks/useSpeechRecognition";
import { buildFieldRows } from "../utils/fieldLabels";
import type { ChatEvent } from "../types/request";

export function NewRequestPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const autoMessage = (location.state as { autoMessage?: string } | null)?.autoMessage;

  const [sessionId, setSessionId] = useState<string | null>(null);
  const [events, setEvents] = useState<ChatEvent[]>([
    { role: "ASSISTANT", content: "您好！請告訴我需要什麼生活服務，例如「我要洗兩台冷氣」。" },
  ]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [serviceName, setServiceName] = useState<string | null>(null);
  const [collected, setCollected] = useState<Record<string, string | number>>({});
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
      const r = await sendMessage(sessionId, message);
      setEvents((prev) => [...prev, { role: "ASSISTANT", content: r.reply }]);
      setServiceName(r.service_name);
      setCollected(r.collected_fields);
      setMissing(r.missing_fields);
      setStatus(r.status);
      if (r.request_id) {
        setToastText("案件已成功建立");
        setTimeout(() => navigate(`/requests/${r.request_id}`), 900);
      }
    } catch {
      setEvents((prev) => [
        ...prev,
        { role: "ASSISTANT", content: "抱歉，訊息傳送失敗，請再試一次。" },
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

  return (
    <main className="mx-auto flex min-h-dvh max-w-md flex-col bg-canvas">
      <header className="flex items-center justify-between border-b border-gray-200 bg-white px-5 py-4.5">
        <button
          type="button"
          onClick={() => navigate("/home")}
          className="flex items-center gap-1.5 text-base font-semibold text-gray-500"
        >
          <ServiceIcon type="back" size={20} />
          取消
        </button>
        <div className="text-base font-black">{serviceName ?? "AI 服務助理"}</div>
        <div className="w-12" />
      </header>

      {isConfirming ? (
        <div className="flex flex-col gap-5 p-6">
          <div className="flex items-start gap-3.5 rounded-2xl border border-brand-soft bg-brand-soft p-4.5">
            <ServiceIcon type="info" size={24} className="flex-none text-brand" />
            <div className="text-sm leading-relaxed">
              <strong className="font-extrabold">請仔細核對以下資訊。</strong>
              在您按下「確認送出」之前，AI 不會建立正式的服務案件。
            </div>
          </div>
          <div className="rounded-3xl border border-gray-200 bg-white p-6 shadow-sm">
            <div className="mb-5 flex items-center gap-3.5 border-b border-gray-100 pb-5">
              <span className="flex h-13 w-13 items-center justify-center rounded-2xl bg-brand-soft text-brand">
                <ServiceIcon type="chat" size={26} />
              </span>
              <span className="text-xl font-extrabold">{serviceName}</span>
            </div>
            {buildFieldRows(collected).map((row) => (
              <div key={row.key} className="flex justify-between py-2.5 text-base">
                <span className="text-gray-500">{row.label}</span>
                <span className="text-right font-bold">{row.value}</span>
              </div>
            ))}
          </div>
          <button
            type="button"
            onClick={() => void send("確認")}
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
            className="w-full rounded-2xl border-2 border-gray-200 bg-white py-4.5 text-base font-bold text-gray-500"
          >
            返回修改
          </button>
        </div>
      ) : (
        <>
          <div className="flex-1 space-y-3.5 overflow-y-auto p-5">
            {events.map((e, i) => (
              <ChatMessage key={i} event={e} />
            ))}
            {sending && <p className="text-sm text-gray-400">管家思考中⋯</p>}
            <div ref={bottomRef} />
          </div>

          <FieldPanel collected={collected} missing={missing.filter((m) => m !== "_edit")} />

          <form
            className="flex items-center gap-3 border-t border-gray-200 bg-white p-4"
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
              placeholder={speech.listening ? "聆聽中⋯請說話" : "輸入訊息或按麥克風說話"}
              aria-label="輸入訊息"
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
    </main>
  );
}
