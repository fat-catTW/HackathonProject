interface Props {
  name: string;
  phone: string;
  onNameChange: (value: string) => void;
  onPhoneChange: (value: string) => void;
  error?: string | null;
}

/**
 * 聯絡人資訊表單。配色改用語意色 Token（Requirement 6.6）：輸入框明確指定
 * `--color-surface` 底與 `--color-foreground` 字，placeholder 用
 * `--color-muted-foreground`，確保 Dark 模式下輸入內容與提示文字皆可讀。
 * 觸控區、maxLength 與錯誤訊息呈現行為不變（Requirement 16.4、17.4）。
 */
export function ReservationContactForm({ name, phone, onNameChange, onPhoneChange, error }: Props) {
  const label = "block text-base font-bold leading-relaxed text-[var(--color-foreground)]";
  const field =
    "mt-2 min-h-[44px] w-full rounded-xl border-2 border-[var(--color-border)] bg-[var(--color-surface)] px-3.5 py-2.5 text-base text-[var(--color-foreground)] outline-none placeholder:text-[var(--color-muted-foreground)] focus:border-[var(--color-primary)]";
  return (
    <div className="flex flex-col gap-4">
      <div>
        <label htmlFor="contact-name" className={label}>
          聯絡人姓名
        </label>
        <input
          id="contact-name"
          aria-label="聯絡人姓名"
          type="text"
          maxLength={50}
          value={name}
          onChange={(e) => onNameChange(e.target.value)}
          className={field}
        />
      </div>
      <div>
        <label htmlFor="contact-phone" className={label}>
          聯絡電話
        </label>
        <input
          id="contact-phone"
          aria-label="聯絡電話"
          type="tel"
          placeholder="0912345678"
          value={phone}
          onChange={(e) => onPhoneChange(e.target.value)}
          className={`${field} font-[family-name:var(--font-mono)]`}
        />
      </div>
      {/* 錯誤訊息以文字＋語意色雙重表達，不單靠顏色（Requirement 16.5） */}
      {error && <p className="text-sm font-bold text-[var(--color-danger)]">{error}</p>}
    </div>
  );
}
