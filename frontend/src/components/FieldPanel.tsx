import { ServiceIcon } from "./ServiceIcon";
import { buildFieldRows, fieldLabel } from "../utils/fieldLabels";

interface Props {
  collected: Record<string, string | number>;
  missing: string[];
}

/** 對話頁的「已填寫／尚缺」動態欄位面板，取代寫死欄位順序的舊版 FormSummary。 */
export function FieldPanel({ collected, missing }: Props) {
  const filled = buildFieldRows(collected);
  if (filled.length === 0 && missing.length === 0) return null;

  return (
    <div className="flex flex-col gap-2.5 border-t border-gray-200 bg-white px-5 py-3.5">
      {filled.length > 0 && (
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-bold text-success">已填寫</span>
          {filled.map((row) => (
            <span
              key={row.key}
              className="inline-flex items-center gap-1.5 rounded-full bg-success-soft px-3 py-1.5 text-xs font-semibold text-ink"
            >
              <ServiceIcon type="check" size={13} className="text-success" />
              {row.label}：{row.value}
            </span>
          ))}
        </div>
      )}
      {missing.length > 0 && (
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-bold text-gray-400">尚缺</span>
          {missing.map((key) => (
            <span
              key={key}
              className="rounded-full border border-dashed border-gray-300 px-3 py-1.5 text-xs font-semibold text-gray-500"
            >
              {fieldLabel(key)}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
