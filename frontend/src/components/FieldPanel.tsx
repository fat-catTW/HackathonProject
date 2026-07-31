import { ServiceIcon } from "./ServiceIcon";
import { buildFieldRows, fieldLabel, type CollectedFieldValue } from "../utils/fieldLabels";

interface Props {
  collected: Record<string, CollectedFieldValue>;
  missing: string[];
}

/**
 * 對話頁的「已填寫／尚缺」動態欄位面板，取代寫死欄位順序的舊版 FormSummary。
 *
 * 配色改用語意色 Token（Requirement 6.6），Light/Dark 共用同一份 className。面板本身
 * 維持不透明 `--color-surface`（Requirement 15.2：資料型區塊不套玻璃擬態）。
 * 「已填寫／尚缺」兩種狀態除了顏色，另以勾選圖示與虛線邊框區隔，不單靠顏色傳達
 * （Requirement 16.5）。
 */
export function FieldPanel({ collected, missing }: Props) {
  const filled = buildFieldRows(collected);
  if (filled.length === 0 && missing.length === 0) return null;

  return (
    <div className="flex flex-col gap-2.5 border-t border-[var(--color-border)] bg-[var(--color-surface)] px-5 py-3.5">
      {filled.length > 0 && (
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-bold text-[var(--color-success)]">已填寫</span>
          {filled.map((row) => (
            <span
              key={row.key}
              className="inline-flex items-center gap-1.5 rounded-full bg-[var(--color-success-soft)] px-3 py-1.5 text-xs font-semibold text-[var(--color-foreground)]"
            >
              <ServiceIcon type="check" size={13} className="text-[var(--color-success)]" />
              {row.label}：{row.value}
            </span>
          ))}
        </div>
      )}
      {missing.length > 0 && (
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-bold text-[var(--color-muted-foreground)]">尚缺</span>
          {missing.map((key) => (
            <span
              key={key}
              className="rounded-full border border-dashed border-[var(--color-border)] px-3 py-1.5 text-xs font-semibold text-[var(--color-muted-foreground)]"
            >
              {fieldLabel(key)}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
