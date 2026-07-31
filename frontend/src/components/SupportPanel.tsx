import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { SUPPORT_FAQS } from "../data/supportFaq";
import { buildSupportRequestPrefill, pageLabelForSupport } from "../utils/support";
import { ServiceIcon } from "./ServiceIcon";

interface SupportPanelProps {
  currentPageId: string;
  onClose?: () => void;
  requestId?: string;
  serviceName?: string;
}

export function SupportPanel({
  currentPageId,
  onClose,
  requestId,
  serviceName,
}: SupportPanelProps) {
  const navigate = useNavigate();
  const [selectedFaqId, setSelectedFaqId] = useState<string | null>(null);

  const selectedFaq = useMemo(
    () => SUPPORT_FAQS.find((item) => item.id === selectedFaqId) ?? null,
    [selectedFaqId],
  );

  function handleTransfer() {
    navigate("/services/customer_support", {
      state: {
        supportPrefill: buildSupportRequestPrefill({
          currentPageId,
          requestId,
          serviceName,
          faqQuestion: selectedFaq?.question,
        }),
      },
    });
    onClose?.();
  }

  return (
    <section className="flex h-[min(82dvh,720px)] w-full max-w-md flex-col overflow-hidden rounded-[32px] border border-[var(--color-border)] bg-[var(--color-surface)] shadow-2xl">
      <header className="flex items-center justify-between border-b border-[var(--color-border)] px-5 py-4">
        <div>
          <p className="text-sm font-semibold text-[var(--color-primary)]">客服中心</p>
          <h2 className="text-lg font-black text-[var(--color-foreground)]">常見問題快速解答</h2>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="關閉客服視窗"
          className="flex h-10 w-10 items-center justify-center rounded-full bg-[var(--color-canvas)] text-[var(--color-muted-foreground)] transition hover:text-[var(--color-foreground)]"
        >
          <ServiceIcon type="close" size={18} />
        </button>
      </header>

      <div className="min-h-0 flex-1 overflow-y-auto px-5 py-5">
        <div className="flex flex-col gap-4">
          <div className="max-w-[88%] rounded-[24px] rounded-bl-md bg-[var(--color-primary-soft)] px-4 py-3 text-sm leading-7 text-[var(--color-foreground)]">
            你好，我是客服小幫手。先試試看常見問題，如果還是沒解決，我們再幫你轉真人客服。
          </div>

          <div className="rounded-[24px] border border-[var(--color-border)] bg-[var(--color-canvas)] px-4 py-3">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--color-muted-foreground)]">
              目前上下文
            </p>
            <div className="mt-2 space-y-1 text-sm text-[var(--color-muted-foreground)]">
              <p>頁面：{pageLabelForSupport(currentPageId)}</p>
              {serviceName && <p>服務：{serviceName}</p>}
              {requestId && <p>案件編號：{requestId}</p>}
            </div>
          </div>

          <div>
            <p className="mb-3 text-sm font-semibold text-[var(--color-muted-foreground)]">
              快速選項
            </p>
            <div className="grid gap-3">
              {SUPPORT_FAQS.map((faq) => {
                const active = faq.id === selectedFaqId;
                return (
                  <button
                    key={faq.id}
                    type="button"
                    onClick={() => setSelectedFaqId(faq.id)}
                    className={`rounded-[22px] border px-4 py-4 text-left text-[var(--color-foreground)] transition ${
                      active
                        ? "border-[var(--color-primary)] bg-[var(--color-primary-soft)]"
                        : "border-[var(--color-border)] bg-[var(--color-surface)] hover:border-[var(--color-primary)] hover:bg-[var(--color-canvas)]"
                    }`}
                  >
                    <div className="flex items-start gap-3">
                      <span
                        className={`mt-0.5 flex h-9 w-9 flex-none items-center justify-center rounded-2xl ${
                          active
                            ? "bg-[var(--color-primary)] text-[var(--color-on-primary)]"
                            : "bg-[var(--color-canvas)] text-[var(--color-muted-foreground)]"
                        }`}
                      >
                        <ServiceIcon type="chat" size={18} />
                      </span>
                      <div>
                        <p className="font-bold">{faq.question}</p>
                        <p className="mt-1 text-sm text-[var(--color-muted-foreground)]">
                          點擊查看制式解答
                        </p>
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {selectedFaq && (
            <>
              {/* 使用者訊息泡泡沿用 ChatMessage 的既有慣例：主色底 + on-primary 文字 */}
              <div className="ml-auto max-w-[82%] rounded-[24px] rounded-br-md bg-[var(--color-primary)] px-4 py-3 text-sm leading-7 text-[var(--color-on-primary)]">
                {selectedFaq.question}
              </div>
              <div className="max-w-[88%] rounded-[24px] rounded-bl-md bg-[var(--color-primary-soft)] px-4 py-3 text-sm leading-7 text-[var(--color-foreground)]">
                {selectedFaq.answer}
              </div>
            </>
          )}
        </div>
      </div>

      <div className="border-t border-[var(--color-border)] bg-[var(--color-surface)] px-5 py-4">
        <button
          type="button"
          onClick={handleTransfer}
          className="w-full rounded-2xl bg-[var(--color-primary)] px-4 py-4 text-base font-bold text-[var(--color-on-primary)] shadow-lg transition hover:bg-[var(--color-primary-hover)]"
        >
          {selectedFaq ? "這題沒解決，轉真人客服" : "直接轉真人客服"}
        </button>
        <p className="mt-3 text-center text-xs leading-6 text-[var(--color-muted-foreground)]">
          送出時會自動帶入目前頁面與案件資訊，減少重複輸入。
        </p>
      </div>
    </section>
  );
}
