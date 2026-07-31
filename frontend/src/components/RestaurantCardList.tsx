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
      {/* 客服媒合入口：與餐廳卡同為不透明實色（Requirement 15.2），以虛線邊框區隔語意 */}
      <button
        type="button"
        onClick={onNeedHelp}
        className="min-h-[44px] w-64 flex-none snap-start rounded-2xl border-2 border-dashed border-[var(--color-border)] bg-[var(--color-surface)] p-4 text-left text-base font-bold text-[var(--color-primary)]"
      >
        客服協助媒合
        <p className="mt-1 text-sm font-normal leading-relaxed text-[var(--color-muted-foreground)]">
          留下需求，由客服為您安排。
        </p>
      </button>
    </div>
  );
}
