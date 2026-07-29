interface Props {
  value: boolean | null;
  onChange: (isPremium: boolean) => void;
}

export function PremiumToggle({ value, onChange }: Props) {
  return (
    <div className="flex flex-col gap-3">
      <p className="text-sm leading-relaxed text-slate-500">
        高級訂位代表將由專人為您安排指定餐廳或特殊座位需求，處理時間可能較長。
      </p>
      <button
        type="button"
        aria-pressed={value === true}
        onClick={() => onChange(true)}
        className={`min-h-[44px] rounded-2xl border-2 px-4 py-3 text-left text-base font-bold ${
          value === true ? "border-brand bg-brand-soft text-brand" : "border-gray-200 bg-white text-slate-700"
        }`}
      >
        是，我要指定/高級訂位
      </button>
      <button
        type="button"
        aria-pressed={value === false}
        onClick={() => onChange(false)}
        className={`min-h-[44px] rounded-2xl border-2 px-4 py-3 text-left text-base font-bold ${
          value === false ? "border-brand bg-brand-soft text-brand" : "border-gray-200 bg-white text-slate-700"
        }`}
      >
        否，一般訂位即可
      </button>
    </div>
  );
}
