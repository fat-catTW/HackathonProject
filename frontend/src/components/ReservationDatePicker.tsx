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

/**
 * 用餐日期選擇。配色改用語意色 Token（Requirement 6.6），輸入框明確指定
 * `--color-surface` 底與 `--color-foreground` 字，避免 Dark 模式下瀏覽器原生
 * date input 沿用淺色預設而導致文字不可讀（`color-scheme` 已於 index.css 依模式宣告）。
 * 觸控區維持 min-h-[44px]、既有 min/max 驗證行為不變（Requirement 16.4、17.4）。
 */
export function ReservationDatePicker({ value, onChange, today = new Date() }: Props) {
  const min = toIsoDate(today);
  const maxDate = new Date(today);
  maxDate.setDate(maxDate.getDate() + 60);
  const max = toIsoDate(maxDate);

  return (
    <div>
      <label
        htmlFor="reservation-date"
        className="block text-base font-bold leading-relaxed text-[var(--color-foreground)]"
      >
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
        className="mt-2 min-h-[44px] w-full rounded-xl border-2 border-[var(--color-border)] bg-[var(--color-surface)] px-3.5 py-2.5 font-[family-name:var(--font-mono)] text-base text-[var(--color-foreground)] outline-none focus:border-[var(--color-primary)]"
      />
    </div>
  );
}
