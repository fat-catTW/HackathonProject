type Slot = "LUNCH" | "DINNER";

interface Props {
  slot: Slot | null;
  specificTime: string | null;
  onSlotChange: (slot: Slot) => void;
  onTimeChange: (time: string) => void;
}

function timesFor(slot: Slot): string[] {
  const [start, end] = slot === "LUNCH" ? [11, 14] : [17, 21];
  const times: string[] = [];
  for (let h = start; h < end; h++) {
    times.push(`${String(h).padStart(2, "0")}:00`);
    times.push(`${String(h).padStart(2, "0")}:30`);
  }
  return times;
}

/** 選項按鈕的選取／未選取樣式，一律引用語意色 Token（Requirement 6.6）。 */
const SELECTED = "border-[var(--color-primary)] bg-[var(--color-primary-soft)] text-[var(--color-primary)]";
const UNSELECTED = "border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-foreground)]";

/**
 * 時段與具體時間選擇。選取狀態同時以 `aria-pressed`、邊框與底色表達（Requirement 16.5）；
 * 所有按鈕觸控區維持 min-h-[44px]（Requirement 16.4）。具體時間為資料型文字，
 * 改用 `--font-mono` 使數字等寬對齊（Requirement 7.3）。
 */
export function TimeSlotSelector({ slot, specificTime, onSlotChange, onTimeChange }: Props) {
  const slotButton = "min-h-[44px] rounded-2xl border-2 px-4 py-3 text-base font-bold";
  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-2 gap-3">
        <button
          type="button"
          aria-pressed={slot === "LUNCH"}
          onClick={() => onSlotChange("LUNCH")}
          className={`${slotButton} ${slot === "LUNCH" ? SELECTED : UNSELECTED}`}
        >
          午餐（11:00–14:00）
        </button>
        <button
          type="button"
          aria-pressed={slot === "DINNER"}
          onClick={() => onSlotChange("DINNER")}
          className={`${slotButton} ${slot === "DINNER" ? SELECTED : UNSELECTED}`}
        >
          晚餐（17:00–21:00）
        </button>
      </div>

      {slot && (
        <div className="grid grid-cols-4 gap-2">
          {timesFor(slot).map((time) => (
            <button
              key={time}
              type="button"
              aria-pressed={specificTime === time}
              onClick={() => onTimeChange(time)}
              className={`min-h-[44px] rounded-xl border-2 font-[family-name:var(--font-mono)] text-sm font-bold ${
                specificTime === time ? SELECTED : UNSELECTED
              }`}
            >
              {time}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
