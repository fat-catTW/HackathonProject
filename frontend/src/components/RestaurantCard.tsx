import type { RestaurantInfo } from "../types/reservation";
import { ServiceIcon } from "./ServiceIcon";

interface Props {
  restaurant: RestaurantInfo;
  selected: boolean;
  onSelect: () => void;
}

export function RestaurantCard({ restaurant, selected, onSelect }: Props) {
  return (
    <button
      type="button"
      aria-pressed={selected}
      onClick={onSelect}
      className={`min-h-[44px] w-64 flex-none snap-start rounded-2xl border-2 p-4 text-left transition ${
        selected ? "border-brand bg-brand-soft" : "border-gray-200 bg-white"
      }`}
    >
      <p className="text-base font-black leading-normal text-slate-900">{restaurant.name}</p>
      <div className="mt-2 flex items-start gap-1.5 text-sm leading-relaxed text-slate-500">
        <ServiceIcon type="location" size={16} className="mt-0.5 flex-none" />
        <span>{restaurant.address}</span>
      </div>
      <div className="mt-1 flex items-center gap-1.5 text-sm leading-relaxed text-slate-500">
        <ServiceIcon type="phone" size={16} className="flex-none" />
        <span>{restaurant.phone}</span>
      </div>
    </button>
  );
}
