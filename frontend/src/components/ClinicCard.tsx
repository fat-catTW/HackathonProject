import type { ClinicInfo } from "../types/clinic";
import { ServiceIcon } from "./ServiceIcon";

interface Props {
  clinic: ClinicInfo;
  selected: boolean;
  recommended: boolean;
  recommendReason: string | null;
  onSelect: () => void;
}

export function ClinicCard({ clinic, selected, recommended, recommendReason, onSelect }: Props) {
  return (
    <button
      type="button"
      aria-pressed={selected}
      onClick={onSelect}
      className={`min-h-[44px] w-64 flex-none snap-start rounded-2xl border-2 p-4 text-left transition ${
        selected
          ? "border-[var(--color-primary)] bg-[var(--color-primary-soft)]"
          : "border-[var(--color-border)] bg-[var(--color-surface)]"
      }`}
    >
      {recommended && (
        <span className="mb-2 inline-block rounded-full bg-[var(--color-primary)] px-2.5 py-0.5 text-xs font-bold text-[var(--color-on-primary)]">
          AI 推薦
        </span>
      )}
      <p className="text-base font-black leading-normal text-[var(--color-foreground)]">{clinic.name}</p>
      <p className="mt-1 text-sm font-bold text-[var(--color-muted-foreground)]">
        {clinic.specialties.join("、")} · {clinic.is_open_now ? "現在有看診" : "目前休診"}
      </p>
      <div className="mt-2 flex items-start gap-1.5 text-sm leading-relaxed text-[var(--color-muted-foreground)]">
        <ServiceIcon type="location" size={16} className="mt-0.5 flex-none" />
        <span>{clinic.address}</span>
      </div>
      <div className="mt-1 flex items-center gap-1.5 text-sm leading-relaxed text-[var(--color-muted-foreground)]">
        <ServiceIcon type="phone" size={16} className="flex-none" />
        <span className="font-[family-name:var(--font-mono)]">{clinic.phone}</span>
      </div>
      {recommended && recommendReason && (
        <p className="mt-2 text-sm leading-relaxed text-[var(--color-primary)]">{recommendReason}</p>
      )}
    </button>
  );
}
