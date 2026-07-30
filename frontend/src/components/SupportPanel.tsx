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
    <section className="flex h-[min(82dvh,720px)] w-full max-w-md flex-col overflow-hidden rounded-[32px] bg-white shadow-[0_32px_90px_rgba(15,23,42,0.28)]">
      <header className="flex items-center justify-between border-b border-slate-200 px-5 py-4">
        <div>
          <p className="text-sm font-semibold text-brand">客服中心</p>
          <h2 className="text-lg font-black text-slate-900">常見問題快速解答</h2>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="關閉客服視窗"
          className="flex h-10 w-10 items-center justify-center rounded-full bg-slate-100 text-slate-500 transition hover:bg-slate-200 hover:text-slate-700"
        >
          <ServiceIcon type="close" size={18} />
        </button>
      </header>

      <div className="min-h-0 flex-1 overflow-y-auto px-5 py-5">
        <div className="flex flex-col gap-4">
          <div className="max-w-[88%] rounded-[24px] rounded-bl-md bg-brand-soft px-4 py-3 text-sm leading-7 text-slate-700">
            你好，我是客服小幫手。先試試看常見問題，如果還是沒解決，我們再幫你轉真人客服。
          </div>

          <div className="rounded-[24px] border border-slate-200 bg-slate-50 px-4 py-3">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">
              目前上下文
            </p>
            <div className="mt-2 space-y-1 text-sm text-slate-600">
              <p>頁面：{pageLabelForSupport(currentPageId)}</p>
              {serviceName && <p>服務：{serviceName}</p>}
              {requestId && <p>案件編號：{requestId}</p>}
            </div>
          </div>

          <div>
            <p className="mb-3 text-sm font-semibold text-slate-500">快速選項</p>
            <div className="grid gap-3">
              {SUPPORT_FAQS.map((faq) => {
                const active = faq.id === selectedFaqId;
                return (
                  <button
                    key={faq.id}
                    type="button"
                    onClick={() => setSelectedFaqId(faq.id)}
                    className={`rounded-[22px] border px-4 py-4 text-left transition ${
                      active
                        ? "border-brand bg-brand-soft text-slate-900"
                        : "border-slate-200 bg-white text-slate-700 hover:border-brand/40 hover:bg-slate-50"
                    }`}
                  >
                    <div className="flex items-start gap-3">
                      <span
                        className={`mt-0.5 flex h-9 w-9 flex-none items-center justify-center rounded-2xl ${
                          active ? "bg-brand text-white" : "bg-slate-100 text-slate-500"
                        }`}
                      >
                        <ServiceIcon type="chat" size={18} />
                      </span>
                      <div>
                        <p className="font-bold">{faq.question}</p>
                        <p className="mt-1 text-sm text-slate-500">點擊查看制式解答</p>
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {selectedFaq && (
            <>
              <div className="ml-auto max-w-[82%] rounded-[24px] rounded-br-md bg-slate-900 px-4 py-3 text-sm leading-7 text-white">
                {selectedFaq.question}
              </div>
              <div className="max-w-[88%] rounded-[24px] rounded-bl-md bg-brand-soft px-4 py-3 text-sm leading-7 text-slate-700">
                {selectedFaq.answer}
              </div>
            </>
          )}
        </div>
      </div>

      <div className="border-t border-slate-200 bg-white px-5 py-4">
        <button
          type="button"
          onClick={handleTransfer}
          className="w-full rounded-2xl bg-brand px-4 py-4 text-base font-bold text-white shadow-[0_16px_36px_rgba(15,76,129,0.24)] transition hover:bg-brand-dark"
        >
          {selectedFaq ? "這題沒解決，轉真人客服" : "直接轉真人客服"}
        </button>
        <p className="mt-3 text-center text-xs leading-6 text-slate-400">
          送出時會自動帶入目前頁面與案件資訊，減少重複輸入。
        </p>
      </div>
    </section>
  );
}
