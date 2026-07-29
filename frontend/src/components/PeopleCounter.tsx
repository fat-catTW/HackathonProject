interface Props {
  value: number;
  onChange: (value: number) => void;
  min?: number;
  max?: number;
}

export function PeopleCounter({ value, onChange, min = 1, max = 20 }: Props) {
  return (
    <div className="flex items-center justify-center gap-6">
      <button
        type="button"
        aria-label="減少人數"
        disabled={value <= min}
        onClick={() => onChange(value - 1)}
        className="flex h-11 w-11 items-center justify-center rounded-full border-2 border-brand text-2xl font-black text-brand disabled:border-gray-200 disabled:text-gray-300"
      >
        −
      </button>
      <span className="min-w-[3ch] text-center text-2xl font-black text-slate-900">{value}</span>
      <button
        type="button"
        aria-label="增加人數"
        disabled={value >= max}
        onClick={() => onChange(value + 1)}
        className="flex h-11 w-11 items-center justify-center rounded-full border-2 border-brand text-2xl font-black text-brand disabled:border-gray-200 disabled:text-gray-300"
      >
        +
      </button>
    </div>
  );
}
