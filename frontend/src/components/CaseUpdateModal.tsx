import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { CASE_UPDATE_COPY, type CaseUpdate, type CaseUpdateCopy } from "../hooks/useCaseUpdates";
import { serviceIconType } from "../utils/serviceIcons";
import { Mascot } from "./Mascot";
import { ServiceIcon } from "./ServiceIcon";

interface Props {
  update: CaseUpdate;
  /** 關掉這一則；佇列裡還有下一則的話會接著跳。 */
  onDismiss: () => void;
}

/**
 * 三種語氣各自的語意色 Token 與圖示。全部走 Token，Light/Dark 共用同一份 className
 * （Requirement 6.6）。
 */
const TONE: Record<CaseUpdateCopy["tone"], { soft: string; ink: string }> = {
  success: { soft: "var(--color-success-soft)", ink: "var(--color-success)" },
  warning: { soft: "var(--color-warning-soft)", ink: "var(--color-warning)" },
  info: { soft: "var(--color-info-soft)", ink: "var(--color-info)" },
};

/**
 * 案件有進度時跳出來的通知卡。
 *
 * 視覺刻意跟每日問候卡（DailyGreetingCard）同一家族——柔光漸層卡頭加上管家吉祥物，
 * 讓使用者一眼認得「這是我的管家來說話」，而不是某個不知道哪來的系統視窗。這一點
 * 對高齡使用者特別重要：分不出來的彈窗，第一個反應是「我是不是被詐騙了」。
 */
export function CaseUpdateModal({ update, onDismiss }: Props) {
  const navigate = useNavigate();
  const copy = CASE_UPDATE_COPY[update.status];
  const tone = TONE[copy.tone];

  // 卡片蓋住整個畫面時，底下的頁面不該還能捲動（比照 HomePage 的問候卡處理）。
  useEffect(() => {
    const { body } = document;
    const previousOverflow = body.style.overflow;
    body.style.overflow = "hidden";
    return () => {
      body.style.overflow = previousOverflow;
    };
  }, []);

  function viewCase() {
    onDismiss();
    navigate(`/requests/${update.requestId}`);
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="案件進度通知"
      className="fixed inset-0 z-[70] flex items-center justify-center px-4 py-6"
    >
      <button
        type="button"
        aria-label="關閉通知"
        onClick={onDismiss}
        className="absolute inset-0 bg-[var(--color-scrim)]"
      />

      <div className="relative w-full max-w-md overflow-hidden rounded-[28px] bg-[var(--color-surface)] shadow-2xl">
        <header
          className="relative overflow-hidden px-6 pb-6 pt-7 text-[var(--color-on-primary)]"
          style={{
            backgroundImage: `
              radial-gradient(55% 45% at 85% 5%, rgba(255,255,255,0.5) 0%, transparent 70%),
              radial-gradient(70% 60% at 8% 105%, var(--color-secondary) 0%, transparent 70%),
              linear-gradient(165deg, var(--color-primary-accent) 0%, var(--color-primary) 100%)
            `,
          }}
        >
          <Mascot
            size={120}
            tone="inverted"
            className="pointer-events-none absolute -bottom-6 -right-5 opacity-[0.16]"
          />
          <div className="relative flex items-center justify-between gap-3">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-white/25 px-3 py-1.5 text-xs font-bold">
              <ServiceIcon type="logo" size={14} />
              管家通知
            </span>
            <button
              type="button"
              onClick={onDismiss}
              aria-label="關閉"
              className="flex h-9 w-9 items-center justify-center rounded-full bg-white/25 transition hover:bg-white/35 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-on-primary)]"
            >
              <ServiceIcon type="close" size={18} />
            </button>
          </div>
          <h2 className="relative mt-4 text-2xl font-black leading-tight">{copy.title}</h2>
        </header>

        <div className="px-5 py-5">
          <div className="flex items-start gap-3 rounded-2xl bg-[var(--color-canvas)] p-4">
            <span
              aria-hidden
              className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full"
              style={{ background: tone.soft, color: tone.ink }}
            >
              <ServiceIcon type={serviceIconType(update.serviceName)} size={22} />
            </span>
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <span
                  className="rounded-full px-2 py-0.5 text-[11px] font-bold"
                  style={{ background: tone.soft, color: tone.ink }}
                >
                  {copy.badge}
                </span>
                <span className="truncate text-sm font-extrabold text-[var(--color-foreground)]">
                  {update.serviceName}
                </span>
              </div>
              <p className="mt-1.5 text-sm font-semibold leading-6 text-[var(--color-muted-foreground)]">
                {copy.message(update.serviceName, update.quoteAmount)}
              </p>
            </div>
          </div>

          <div className="mt-5 flex gap-3">
            <button
              type="button"
              onClick={onDismiss}
              className="flex-1 rounded-2xl border-2 border-[var(--color-border)] py-3.5 text-base font-bold text-[var(--color-muted-foreground)] transition hover:text-brand focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand"
            >
              知道了
            </button>
            <button
              type="button"
              onClick={viewCase}
              className="flex-1 rounded-2xl bg-brand py-3.5 text-base font-black text-[var(--color-on-primary)] transition hover:opacity-90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand"
            >
              查看案件
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
