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

export function TimeSlotSelector({ slot, specificTime, onSlotChange, onTimeChange }: Props) {
  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-2 gap-3">
        <button
          type="button"
          aria-pressed={slot === "LUNCH"}
          onClick={() => onSlotChange("LUNCH")}
          className={`min-h-[44px] rounded-2xl border-2 px-4 py-3 text-base font-bold ${
            slot === "LUNCH" ? "border-brand bg-brand-soft text-brand" : "border-gray-200 bg-white text-slate-700"
          }`}
        >
          午餐（11:00–14:00）
        </button>
        <button
          type="button"
          aria-pressed={slot === "DINNER"}
          onClick={() => onSlotChange("DINNER")}
          className={`min-h-[44px] rounded-2xl border-2 px-4 py-3 text-base font-bold ${
            slot === "DINNER" ? "border-brand bg-brand-soft text-brand" : "border-gray-200 bg-white text-slate-700"
          }`}
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
              className={`min-h-[44px] rounded-xl border-2 text-sm font-bold ${
                specificTime === time ? "border-brand bg-brand-soft text-brand" : "border-gray-200 bg-white text-slate-600"
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
