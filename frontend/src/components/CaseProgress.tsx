import type { RequestProgressStep } from "../types/request";

/**
 * 案件進度條（V8 服務進度追蹤）。
 *
 * 為什麼是垂直而不是水平：關卡最多六格，橫著排在手機上每一格只剩四十幾像素寬，
 * 「廠商已接單」這種四個字的名稱一定會被截斷或縮成看不清的字級——高齡使用者是
 * 這個功能的主要受眾，寧可多佔一點垂直空間。
 *
 * 每一格都畫，包含還沒走到的：住戶最常問的不是「現在到哪」而是「接下來還有什麼」，
 * 只畫已完成的關卡等於把後半段藏起來。
 *
 * 進度不是由前端從狀態推算的，而是後端 `progress` 欄位直接給的——狀態機在
 * `app/services/statuses.py`，兩邊各推一次遲早會對不上。
 */
export function CaseProgress({
  steps,
  quoteAmount,
}: {
  steps: RequestProgressStep[];
  /** 有報價時顯示在「已報價」那一格底下。 */
  quoteAmount?: number | null;
}) {
  if (steps.length === 0) return null;

  // 目前走到的那一格＝最後一個完成的關卡，它要比其他完成的關卡更醒目。
  const currentIndex = steps.reduce((last, step, index) => (step.done ? index : last), -1);

  return (
    <section className="rounded-3xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5">
      <h2 className="text-base font-black text-[var(--color-foreground)]">服務進度</h2>
      <ol className="mt-4">
        {steps.map((step, index) => {
          const isCurrent = index === currentIndex;
          const isLast = index === steps.length - 1;
          return (
            <li key={step.status} className="flex gap-3">
              {/* 圓點與連接線：整條線靠這一欄畫出來，文字欄不必管對齊 */}
              <div className="flex flex-col items-center">
                <span
                  aria-hidden
                  className={`mt-1 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border-2 ${
                    step.done
                      ? "border-[var(--color-success)] bg-[var(--color-success)]"
                      : "border-[var(--color-border)] bg-[var(--color-surface)]"
                  }`}
                >
                  {step.done && (
                    <span className="h-1.5 w-1.5 rounded-full bg-[var(--color-surface)]" />
                  )}
                </span>
                {!isLast && (
                  <span
                    aria-hidden
                    className={`w-0.5 flex-1 ${
                      steps[index + 1].done
                        ? "bg-[var(--color-success)]"
                        : "bg-[var(--color-border)]"
                    }`}
                  />
                )}
              </div>

              <div className={`min-w-0 flex-1 ${isLast ? "pb-0" : "pb-5"}`}>
                <div className="flex flex-wrap items-center gap-2">
                  <span
                    className={`text-base ${
                      step.done
                        ? "font-black text-[var(--color-foreground)]"
                        : "font-medium text-[var(--color-muted-foreground)]"
                    }`}
                  >
                    {step.label}
                  </span>
                  {/* 「目前進度」不只是顏色差異：只靠深淺的話色弱使用者分不出走到哪 */}
                  {isCurrent && (
                    <span className="rounded-full bg-[var(--color-success-soft)] px-2 py-0.5 text-xs font-bold text-[var(--color-success)]">
                      目前進度
                    </span>
                  )}
                </div>
                {step.at && (
                  <p className="mt-0.5 text-sm text-[var(--color-muted-foreground)]">
                    {formatStepTime(step.at)}
                  </p>
                )}
                {step.status === "QUOTED" && step.done && quoteAmount != null && (
                  <p className="mt-1 text-base font-black text-[var(--color-foreground)]">
                    NT${quoteAmount.toLocaleString("zh-TW")}
                  </p>
                )}
              </div>
            </li>
          );
        })}
      </ol>
    </section>
  );
}

function formatStepTime(value: string) {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "";
  return parsed.toLocaleString("zh-TW", {
    month: "numeric",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}
