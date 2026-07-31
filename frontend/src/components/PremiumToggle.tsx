interface Props {
  value: boolean | null;
  onChange: (isPremium: boolean) => void;
}

/** 選項按鈕的選取／未選取樣式，一律引用語意色 Token（Requirement 6.6）。 */
const SELECTED = "border-[var(--color-primary)] bg-[var(--color-primary-soft)] text-[var(--color-primary)]";
const UNSELECTED = "border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-foreground)]";

/**
 * 高級訂位選擇。選取狀態同時以 `aria-pressed`、邊框與底色三重表達，不單靠顏色
 * （Requirement 16.5）；觸控區維持 min-h-[44px]（Requirement 16.4）。
 */
export function PremiumToggle({ value, onChange }: Props) {
  const option = "min-h-[44px] rounded-2xl border-2 px-4 py-3 text-left text-base font-bold";
  return (
    <div className="flex flex-col gap-3">
      <p className="text-sm leading-relaxed text-[var(--color-muted-foreground)]">
        高級訂位代表將由專人為您安排指定餐廳或特殊座位需求，處理時間可能較長。
      </p>
      <button
        type="button"
        aria-pressed={value === true}
        onClick={() => onChange(true)}
        className={`${option} ${value === true ? SELECTED : UNSELECTED}`}
      >
        是，我要指定/高級訂位
      </button>
      <button
        type="button"
        aria-pressed={value === false}
        onClick={() => onChange(false)}
        className={`${option} ${value === false ? SELECTED : UNSELECTED}`}
      >
        否，一般訂位即可
      </button>
    </div>
  );
}
