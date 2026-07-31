interface Props {
  value: number;
  onChange: (value: number) => void;
  min?: number;
  max?: number;
}

/**
 * 人數增減控件。配色改用語意色 Token（Requirement 6.6），Light/Dark 共用同一份 className。
 * 觸控區維持 44×44px（h-11 w-11，於 18px 根字級下為 44px，Requirement 16.4）。
 * disabled 狀態以 `--color-border` 邊框 + `--color-muted-foreground` 降低強調度，
 * 在兩模式下皆與可用狀態明確區分（Requirement 17.4：維持既有互動語意）。
 */
export function PeopleCounter({ value, onChange, min = 1, max = 20 }: Props) {
  const stepButton =
    "flex h-11 w-11 items-center justify-center rounded-full border-2 border-[var(--color-primary)] text-2xl font-black text-[var(--color-primary)] disabled:border-[var(--color-border)] disabled:text-[var(--color-muted-foreground)] disabled:opacity-60";
  return (
    <div className="flex items-center justify-center gap-6">
      <button
        type="button"
        aria-label="減少人數"
        disabled={value <= min}
        onClick={() => onChange(value - 1)}
        className={stepButton}
      >
        −
      </button>
      <span className="min-w-[3ch] text-center font-[family-name:var(--font-mono)] text-2xl font-black text-[var(--color-foreground)]">
        {value}
      </span>
      <button
        type="button"
        aria-label="增加人數"
        disabled={value >= max}
        onClick={() => onChange(value + 1)}
        className={stepButton}
      >
        +
      </button>
    </div>
  );
}
