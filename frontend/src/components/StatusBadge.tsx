import type { RequestStatus } from "../types/request";

/**
 * 狀態徽章配色一律引用 index.css 的語意狀態色 Token（Requirement 6.6：元件不寫死色碼），
 * 文字色為 `--color-{status}`、背景為對應的 `--color-{status}-soft`；此配對已由
 * `styles/contrast.test.ts` 驗證於 Light/Dark 兩模式皆達 4.5:1，因此兩模式共用同一組
 * className，soft 背景在 Dark 模式自動變為低飽和深色，使膠囊邊界在兩模式皆可辨識
 * （Requirement 16.6）。
 *
 * 中性狀態（已取消／未知狀態）改用 `--color-muted-foreground` on `--color-canvas`，
 * 同樣為對比測試涵蓋的 Token 配對，取代原本固定的 gray-100/gray-500。
 */
const WARNING_STYLE = "bg-[var(--color-warning-soft)] text-[var(--color-warning)]";
const SUCCESS_STYLE = "bg-[var(--color-success-soft)] text-[var(--color-success)]";
const COMPLETED_STYLE = "bg-[var(--color-info-soft)] text-[var(--color-info)]";
const NEUTRAL_STYLE = "bg-[var(--color-canvas)] text-[var(--color-muted-foreground)]";

const STYLES: Record<string, string> = {
  SUBMITTED: WARNING_STYLE,
  PENDING_PROVIDER: WARNING_STYLE,
  CONFIRMED: SUCCESS_STYLE,
  IN_PROGRESS: SUCCESS_STYLE,
  COMPLETED: COMPLETED_STYLE,
  CANCELLED: NEUTRAL_STYLE,
  REJECTED: NEUTRAL_STYLE,
  FAILED: "bg-[var(--color-danger-soft)] text-[var(--color-danger)]",
  VERIFIED: COMPLETED_STYLE,
};

export function StatusBadge({
  status,
  label,
}: {
  status: RequestStatus | string;
  label: string;
}) {
  const style = STYLES[status] ?? NEUTRAL_STYLE;
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-sm font-medium ${style}`}
    >
      {/* 顏色圓點僅為輔助，狀態語意同時以 label 文字傳達（Requirement 16.5） */}
      <span className="h-2 w-2 rounded-full bg-current" aria-hidden />
      {label}
    </span>
  );
}
