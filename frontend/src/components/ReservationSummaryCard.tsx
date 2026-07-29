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

export function ReservationSummaryCard({ data, onConfirm, onEdit, submitting }: Props) {
  return (
    <div className="rounded-3xl border border-gray-200 bg-white p-5">
      {ROWS.map((row) => (
        <div key={row.key} className="flex justify-between gap-3 border-b border-gray-100 py-3.5 text-base leading-relaxed last:border-b-0">
          <span className="font-bold text-slate-500">{row.label}</span>
          <span className="text-right font-bold text-slate-900">{row.format ? row.format(data) : String(data[row.key])}</span>
        </div>
      ))}

      <div className="mt-5 flex flex-col gap-3">
        <button
          type="button"
          onClick={onConfirm}
          disabled={submitting}
          className="min-h-[44px] rounded-2xl bg-brand px-6 py-4 text-base font-bold text-white disabled:opacity-60"
        >
          {submitting ? "訂位處理中，請稍候" : "確認送出"}
        </button>
        <button
          type="button"
          onClick={onEdit}
          disabled={submitting}
          className="min-h-[44px] rounded-2xl border-2 border-brand px-6 py-4 text-base font-bold text-brand disabled:opacity-60"
        >
          返回修改
        </button>
      </div>
    </div>
  );
}
