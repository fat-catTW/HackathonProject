import { GlassPanel } from "./GlassPanel";

interface SummaryData {
  clinicName: string;
  clinicAddress: string;
  date: string;
  time: string;
  symptomNote: string;
  contactName: string;
  phone: string;
}

interface Props {
  data: SummaryData;
  onConfirm: () => void;
  onEdit: () => void;
  submitting: boolean;
}

const ROWS: { key: keyof SummaryData; label: string }[] = [
  { key: "clinicName", label: "診所名稱" },
  { key: "clinicAddress", label: "診所地址" },
  { key: "date", label: "看診日期" },
  { key: "time", label: "看診時間" },
  { key: "symptomNote", label: "症狀描述" },
  { key: "contactName", label: "聯絡人" },
  { key: "phone", label: "聯絡電話" },
];

const MONO_KEYS = new Set<keyof SummaryData>(["date", "time", "phone"]);

export function ClinicSummaryCard({ data, onConfirm, onEdit, submitting }: Props) {
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
            {data[row.key]}
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
          {submitting ? "掛號處理中，請稍候" : "確認掛號"}
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
