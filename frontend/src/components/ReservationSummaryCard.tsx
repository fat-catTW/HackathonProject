import { GlassPanel } from "./GlassPanel";

interface SummaryData {
  restaurantName: string;
  date: string;
  timeSlot: string;
  specificTime: string | null;
  people: number;
  contactName: string;
  phone: string;
  isPremium: boolean;
}

interface Props {
  data: SummaryData;
  onConfirm: () => void;
  onEdit: () => void;
  submitting: boolean;
}

const ROWS: { key: keyof SummaryData; label: string; format?: (v: SummaryData) => string }[] = [
  { key: "restaurantName", label: "餐廳名稱" },
  { key: "date", label: "用餐日期" },
  { key: "timeSlot", label: "用餐時段", format: (d) => `${d.timeSlot}${d.specificTime ? ` ${d.specificTime}` : ""}` },
  { key: "people", label: "用餐人數", format: (d) => String(d.people) },
  { key: "contactName", label: "聯絡人" },
  { key: "phone", label: "聯絡電話" },
  { key: "isPremium", label: "訂位類型", format: (d) => (d.isPremium ? "高級訂位" : "一般訂位") },
];

/**
 * 訂位最終確認摘要卡。屬於流程終點的重點卡片，依 Requirement 13.6 / 15.1 套用
 * `GlassPanel` 玻璃擬態強調（多步驟流程中的其他步驟卡維持不透明實色）。
 *
 * 欄位標籤與字級規範維持不變（Requirement 13.6）；配色一律引用語意色 Token
 * （Requirement 6.6）。分隔線改用 `--color-border`，使其在 Dark 模式下同樣可辨識。
 * 資料型欄位值（日期、時間、人數、電話）改用 `--font-mono`（Requirement 7.3）。
 */
const MONO_KEYS = new Set<keyof SummaryData>(["date", "timeSlot", "people", "phone"]);

export function ReservationSummaryCard({ data, onConfirm, onEdit, submitting }: Props) {
  return (
    <GlassPanel className="rounded-3xl p-5">
      {ROWS.map((row) => (
        <div
          key={row.key}
          className="flex justify-between gap-3 border-b border-[var(--color-border)] py-3.5 text-base leading-relaxed last:border-b-0"
        >
          <span className="font-bold text-[var(--color-muted-foreground)]">{row.label}</span>
          <span
            className={`text-right font-bold text-[var(--color-foreground)] ${
              MONO_KEYS.has(row.key) ? "font-[family-name:var(--font-mono)]" : ""
            }`}
          >
            {row.format ? row.format(data) : String(data[row.key])}
          </span>
        </div>
      ))}

      <div className="mt-5 flex flex-col gap-3">
        <button
          type="button"
          onClick={onConfirm}
          disabled={submitting}
          className="min-h-[44px] rounded-2xl bg-[var(--color-primary)] px-6 py-4 text-base font-bold text-[var(--color-on-primary)] disabled:opacity-60"
        >
          {submitting ? "訂位處理中，請稍候" : "確認送出"}
        </button>
        <button
          type="button"
          onClick={onEdit}
          disabled={submitting}
          className="min-h-[44px] rounded-2xl border-2 border-[var(--color-primary)] px-6 py-4 text-base font-bold text-[var(--color-primary)] disabled:opacity-60"
        >
          返回修改
        </button>
      </div>
    </GlassPanel>
  );
}
