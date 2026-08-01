import { GlassPanel } from "./GlassPanel";
import { ServiceIcon } from "./ServiceIcon";

interface TaskCard {
  service_id: string;
  service_name: string;
}

export function TaskCardList({ cards }: { cards: TaskCard[] }) {
  return (
    <div className="mt-3 flex flex-col gap-2.5">
      {cards.map((card) => (
        <GlassPanel
          key={card.service_id}
          className="flex items-center gap-3 rounded-2xl p-3.5 shadow-sm"
        >
          <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-[var(--color-primary-soft)] text-[var(--color-primary)]">
            <ServiceIcon type="chat" size={18} />
          </span>
          <span className="text-base font-bold text-[var(--color-foreground)]">{card.service_name}</span>
        </GlassPanel>
      ))}
    </div>
  );
}
