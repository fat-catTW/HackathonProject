interface Props {
  name: string;
  phone: string;
  onNameChange: (value: string) => void;
  onPhoneChange: (value: string) => void;
  error?: string | null;
}

export function ReservationContactForm({ name, phone, onNameChange, onPhoneChange, error }: Props) {
  return (
    <div className="flex flex-col gap-4">
      <div>
        <label htmlFor="contact-name" className="block text-base font-bold leading-relaxed text-slate-900">
          聯絡人姓名
        </label>
        <input
          id="contact-name"
          aria-label="聯絡人姓名"
          type="text"
          maxLength={50}
          value={name}
          onChange={(e) => onNameChange(e.target.value)}
          className="mt-2 min-h-[44px] w-full rounded-xl border-2 border-gray-200 px-3.5 py-2.5 text-base outline-none focus:border-brand"
        />
      </div>
      <div>
        <label htmlFor="contact-phone" className="block text-base font-bold leading-relaxed text-slate-900">
          聯絡電話
        </label>
        <input
          id="contact-phone"
          aria-label="聯絡電話"
          type="tel"
          placeholder="0912345678"
          value={phone}
          onChange={(e) => onPhoneChange(e.target.value)}
          className="mt-2 min-h-[44px] w-full rounded-xl border-2 border-gray-200 px-3.5 py-2.5 text-base outline-none focus:border-brand"
        />
      </div>
      {error && <p className="text-sm font-bold text-danger">{error}</p>}
    </div>
  );
}
