import type { RestaurantInfo } from "../types/reservation";
import { RestaurantCard } from "./RestaurantCard";

interface Props {
  restaurants: RestaurantInfo[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onNeedHelp: () => void;
}

export function RestaurantCardList({ restaurants, selectedId, onSelect, onNeedHelp }: Props) {
  return (
    <div className="flex snap-x gap-3 overflow-x-auto pb-2">
      {restaurants.slice(0, 6).map((restaurant) => (
        <RestaurantCard
          key={restaurant.id}
          restaurant={restaurant}
          selected={selectedId === restaurant.id}
          onSelect={() => onSelect(restaurant.id)}
        />
      ))}
      <button
        type="button"
        onClick={onNeedHelp}
        className="min-h-[44px] w-64 flex-none snap-start rounded-2xl border-2 border-dashed border-gray-300 bg-white p-4 text-left text-base font-bold text-brand"
      >
        客服協助媒合
        <p className="mt-1 text-sm font-normal leading-relaxed text-slate-500">留下需求，由客服為您安排。</p>
      </button>
    </div>
  );
}
