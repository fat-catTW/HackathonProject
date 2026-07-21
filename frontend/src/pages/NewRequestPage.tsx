import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { createSession, sendMessage } from "../api/chat";
import { ChatMessage } from "../components/ChatMessage";
import { FormSummary } from "../components/FormSummary";
import { VoiceButton } from "../components/VoiceButton";
import { useSpeechRecognition } from "../hooks/useSpeechRecognition";
import type { ChatEvent } from "../types/request";

export function NewRequestPage() {
  const navigate = useNavigate();
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [events, setEvents] = useState<ChatEvent[]>([
    { role: "ASSISTANT", content: "您好！請告訴我需要什麼生活服務，例如「我要洗兩台冷氣」。" },
  ]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [serviceName, setServiceName] = useState<string | null>(null);
  const [collected, setCollected] = useState<Record<string, string | number>>({});
  const [missing, setMissing] = useState<string[]>([]);
  const [requestId, setRequestId] = useState<string | null>(null);
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
      if (r.request_id) setRequestId(r.request_id);
    } catch {
      setEvents((prev) => [
        ...prev,
        { role: "ASSISTANT", content: "抱歉，訊息傳送失敗，請再試一次。" },
      ]);
    } finally {
      setSending(false);
    }
  }

  const speech = useSpeechRecognition((text) => void send(text));

  return (
    <main className="mx-auto flex min-h-dvh max-w-md flex-col px-5 pb-6 pt-6">
      <header className="flex items-center justify-between">
        <h1 className="text-xl font-black">{serviceName ?? "新的服務需求"}</h1>
        <Link to="/" className="rounded-full px-3 py-1.5 text-sm text-gray-400 hover:text-ink">
          取消
        </Link>
      </header>

      <div className="mt-4">
        <FormSummary serviceName={serviceName} collected={collected} missing={missing} />
      </div>

      <div className="mt-4 flex-1 space-y-3 overflow-y-auto">
        {events.map((e, i) => (
          <ChatMessage key={i} event={e} />
        ))}
        {sending && <p className="text-sm text-gray-400">管家思考中⋯</p>}
        <div ref={bottomRef} />
      </div>

      {requestId ? (
        <button
          type="button"
          onClick={() => navigate(`/requests/${requestId}`)}
          className="mt-4 w-full rounded-2xl bg-pine px-6 py-4 text-lg font-bold text-white hover:bg-pine-dark"
        >
          查看案件 {requestId}
        </button>
      ) : (
        <>
          {speech.error && (
            <p className="mt-2 text-sm text-red-500" role="alert">
              {speech.error}
            </p>
          )}
          {!speech.supported && (
            <p className="mt-2 text-sm text-gray-400">
              此瀏覽器不支援語音輸入（建議使用 Chrome/Edge），請改用文字輸入。
            </p>
          )}
          <form
            className="mt-4 flex items-center gap-3"
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
              className="min-w-0 flex-1 rounded-2xl border border-pine-soft bg-white px-4 py-3.5 outline-none focus:border-pine"
            />
            <button
              type="submit"
              disabled={sending || !input.trim()}
              className="rounded-2xl bg-pine px-5 py-3.5 font-bold text-white disabled:opacity-40"
            >
              送出
            </button>
          </form>
        </>
      )}
    </main>
  );
}
