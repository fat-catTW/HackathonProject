interface Props {
  value: string;
  onChange: (date: string) => void;
  today?: Date;
}

function toIsoDate(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

export function ReservationDatePicker({ value, onChange, today = new Date() }: Props) {
  const min = toIsoDate(today);
  const maxDate = new Date(today);
  maxDate.setDate(maxDate.getDate() + 60);
  const max = toIsoDate(maxDate);

  return (
    <div>
      <label htmlFor="reservation-date" className="block text-base font-bold leading-relaxed text-slate-900">
        用餐日期
      </label>
      <input
        id="reservation-date"
        aria-label="用餐日期"
        type="date"
        min={min}
        max={max}
        value={value}
        onInput={(e) => onChange((e.target as HTMLInputElement).value)}
        className="mt-2 min-h-[44px] w-full rounded-xl border-2 border-gray-200 px-3.5 py-2.5 text-base outline-none focus:border-brand"
      />
    </div>
  );
}
