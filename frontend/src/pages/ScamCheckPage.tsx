import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { checkScamMessage, type ScamCheckResult } from "../api/scamCheck";
import { BottomNav } from "../components/BottomNav";
import { ServiceIcon } from "../components/ServiceIcon";

export function ScamCheckPage() {
  const navigate = useNavigate();
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ScamCheckResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit() {
    if (!message.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const r = await checkScamMessage(message.trim());
      setResult(r);
    } catch {
      setError("目前無法判斷這則訊息，請稍後再試。");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto min-h-dvh max-w-md bg-[var(--color-canvas)] px-5 pb-32 pt-8">
      <div className="mb-6 flex items-center gap-3">
        <button
          type="button"
          onClick={() => navigate(-1)}
          aria-label="返回"
          className="flex h-11 w-11 items-center justify-center rounded-full bg-[var(--color-surface)] text-[var(--color-foreground)] shadow-sm"
        >
          <ServiceIcon type="back" size={20} />
        </button>
        <h1 className="text-2xl font-black text-[var(--color-foreground)]">詐騙訊息辨識</h1>
      </div>

      <p className="mb-4 text-[var(--color-muted-foreground)]">
        收到看起來怪怪的簡訊或訊息嗎？貼上來，我幫你看看安不安全。
      </p>

      <label htmlFor="scam-message-input" className="mb-2 block text-sm font-bold text-[var(--color-foreground)]">
        貼上可疑訊息
      </label>
      <textarea
        id="scam-message-input"
        aria-label="貼上可疑訊息"
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        rows={5}
        className="w-full rounded-2xl border-2 border-[var(--color-border)] bg-[var(--color-surface)] p-4 text-[var(--color-foreground)] outline-none focus:border-[var(--color-primary)]"
      />

      <button
        type="button"
        onClick={() => void handleSubmit()}
        disabled={loading || !message.trim()}
        className="mt-4 w-full rounded-2xl bg-[var(--color-primary)] py-4.5 text-lg font-bold text-[var(--color-on-primary)] disabled:opacity-40"
      >
        幫我看看
      </button>

      {error && <p className="mt-4 text-[var(--color-danger)]">{error}</p>}

      {result && (
        <div className="mt-6 rounded-3xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5 shadow-sm">
          <p className="text-lg font-black text-[var(--color-foreground)]">{result.category}</p>
          <p className="mt-2 leading-relaxed text-[var(--color-foreground)]">{result.explanation}</p>
        </div>
      )}

      <BottomNav />
    </main>
  );
}
