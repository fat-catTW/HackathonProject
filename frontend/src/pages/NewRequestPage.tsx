import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { createSession, sendMessage, updateFormDraft } from "../api/chat";
import { ChatMessage } from "../components/ChatMessage";
import { FormSummary } from "../components/FormSummary";
import { VoiceButton } from "../components/VoiceButton";
import { useSpeechRecognition } from "../hooks/useSpeechRecognition";
import type { ChatEvent, ChatResponse, FormDraft, FormSchema } from "../types/request";

export function NewRequestPage() {
  const navigate = useNavigate();
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [events, setEvents] = useState<ChatEvent[]>([
    {
      role: "ASSISTANT",
      content: "請告訴我你想申請哪一項服務，我會一邊幫你整理需求，一邊把表單填好。",
    },
  ]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [serviceName, setServiceName] = useState<string | null>(null);
  const [formSchema, setFormSchema] = useState<FormSchema | null>(null);
  const [formDraft, setFormDraft] = useState<FormDraft | null>(null);
  const [requestId, setRequestId] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    createSession()
      .then((response) => setSessionId(response.session_id))
      .catch(() => navigate("/login"));
  }, [navigate]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [events, formDraft]);

  function applyResponse(response: ChatResponse, appendReply = true) {
    if (appendReply && response.reply) {
      setEvents((current) => [...current, { role: "ASSISTANT", content: response.reply }]);
    }
    setServiceName(response.service_name);
    setFormSchema(response.form_schema);
    setFormDraft(response.form_draft);
    setRequestId(response.request_id);
  }

  async function send(text: string) {
    const message = text.trim();
    if (!message || !sessionId || sending) return;
    setInput("");
    setSending(true);
    setEvents((current) => [...current, { role: "USER", content: message }]);
    try {
      const response = await sendMessage(sessionId, message);
      applyResponse(response);
    } catch {
      setEvents((current) => [
        ...current,
        { role: "ASSISTANT", content: "目前無法送出這則訊息，請稍後再試一次。" },
      ]);
    } finally {
      setSending(false);
    }
  }

  async function handleFormApply(fields: Record<string, string | number | null>) {
    if (!sessionId || sending) return;
    setSending(true);
    try {
      const response = await updateFormDraft(sessionId, fields);
      applyResponse(response);
    } catch {
      setEvents((current) => [
        ...current,
        { role: "ASSISTANT", content: "表單更新失敗，請稍後再試一次。" },
      ]);
    } finally {
      setSending(false);
    }
  }

  async function handleConfirm() {
    await send("確認");
  }

  const speech = useSpeechRecognition((text) => void send(text));

  return (
    <main className="mx-auto flex min-h-dvh max-w-5xl flex-col px-4 pb-6 pt-6 md:px-6">
      <header className="flex items-center justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-pine">AI Service Butler</p>
          <h1 className="mt-2 text-2xl font-black text-ink">{serviceName ?? "AI 服務管家"}</h1>
        </div>
        <Link to="/" className="rounded-full px-3 py-1.5 text-sm text-gray-400 hover:text-ink">
          返回
        </Link>
      </header>

      <div className="mt-5 grid gap-5 lg:grid-cols-[1.2fr_0.8fr]">
        <section className="order-2 flex min-h-[55vh] flex-col rounded-[30px] border border-pine-soft bg-white/90 p-4 shadow-sm lg:order-1">
          <div className="flex-1 space-y-3 overflow-y-auto pr-1">
            {events.map((event, index) => (
              <ChatMessage key={index} event={event} />
            ))}
            {sending && <p className="text-sm text-gray-400">管家整理中...</p>}
            <div ref={bottomRef} />
          </div>

          {requestId ? (
            <button
              type="button"
              onClick={() => navigate(`/requests/${requestId}`)}
              className="mt-4 w-full rounded-2xl bg-pine px-6 py-4 text-base font-bold text-white hover:bg-pine-dark"
            >
              查看案件 {requestId}
            </button>
          ) : (
            <form
              className="mt-4 flex items-center gap-3"
              onSubmit={(event) => {
                event.preventDefault();
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
                onChange={(event) => setInput(event.target.value)}
                placeholder={speech.listening ? "正在聆聽，請直接說..." : "輸入訊息，或直接修改右邊表單"}
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
          )}
        </section>

        <div className="order-1 lg:order-2">
          <FormSummary
            formSchema={formSchema}
            formDraft={formDraft}
            sending={sending}
            onApply={handleFormApply}
            onConfirm={handleConfirm}
          />
        </div>
      </div>
    </main>
  );
}
