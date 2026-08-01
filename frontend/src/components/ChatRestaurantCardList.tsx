import { RestaurantCard, type RestaurantCardInfo } from "./RestaurantCard";

/**
 * 對話裡「幫我找餐廳」搜尋結果的卡片版，取代純文字列表。點卡片等同於直接打出
 * 店名送出——後端的 _match_restaurant_pick 本來就支援用店名比對，不需要新的 API。
 */
export function ChatRestaurantCardList({
  restaurants,
  onSelect,
}: {
  restaurants: RestaurantCardInfo[];
  onSelect: (name: string) => void;
}) {
  return (
    <div className="mt-3 flex snap-x gap-3 overflow-x-auto pb-1">
      {restaurants.map((restaurant) => (
        <RestaurantCard
          key={restaurant.id}
          restaurant={restaurant}
          selected={false}
          onSelect={() => onSelect(restaurant.name)}
        />
      ))}
    </div>
  );
}
