import { ServiceIcon } from "./ServiceIcon";

/** 卡片只用得到這幾個欄位；ReservationFlowPage 的完整 RestaurantInfo 和聊天室搜尋結果
 * （只有 id/name/address/phone/reason，沒有 brand/cuisine/supports_booking_api）都能直接套用。 */
export interface RestaurantCardInfo {
  id: string;
  name: string;
  address: string;
  phone: string;
  /** AI 搜尋這家店的理由（只有聊天室的搜尋結果才有）。 */
  reason?: string;
}

interface Props {
  restaurant: RestaurantCardInfo;
  selected: boolean;
  onSelect: () => void;
}

/**
 * 餐廳選擇卡。屬於資料型清單元件，依 Requirement 15.2 維持不透明實色
 * （`--color-surface`／選取時 `--color-primary-soft`），不套玻璃擬態或漸層。
 * 配色引用語意色 Token（Requirement 6.6），選取狀態同時以 `aria-pressed` 與
 * 邊框色雙重表達，不單靠顏色傳達（Requirement 16.5）。觸控區維持 min-h-[44px]。
 */
export function RestaurantCard({ restaurant, selected, onSelect }: Props) {
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
      <p className="text-base font-black leading-normal text-[var(--color-foreground)]">{restaurant.name}</p>
      {restaurant.address && (
        <div className="mt-2 flex items-start gap-1.5 text-sm leading-relaxed text-[var(--color-muted-foreground)]">
          <ServiceIcon type="location" size={16} className="mt-0.5 flex-none" />
          <span>{restaurant.address}</span>
        </div>
      )}
      {restaurant.phone && (
        <div className="mt-1 flex items-center gap-1.5 text-sm leading-relaxed text-[var(--color-muted-foreground)]">
          <ServiceIcon type="phone" size={16} className="flex-none" />
          <span className="font-[family-name:var(--font-mono)]">{restaurant.phone}</span>
        </div>
      )}
      {restaurant.reason && (
        <p className="mt-2 border-t border-[var(--color-border)] pt-2 text-sm leading-relaxed text-[var(--color-muted-foreground)]">
          {restaurant.reason}
        </p>
      )}
    </button>
  );
}
