interface Props {
  rating: number;
  count?: number;
}

/**
 * 星等＋數字＋則數的純展示元件（例："★★★★☆ 4.6（128）"）。
 * 商品卡片、比價清單、評價清單共用。
 */
export function RatingStars({ rating, count }: Props) {
  const filled = Math.max(0, Math.min(5, Math.round(rating)));
  const stars = "★".repeat(filled) + "☆".repeat(5 - filled);

  return (
    <span className="inline-flex items-center gap-1 text-sm text-[var(--color-muted-foreground)]">
      <span className="text-[var(--color-primary-accent)]" aria-hidden="true">
        {stars}
      </span>
      <span>
        {rating.toFixed(1)}
        {typeof count === "number" && count > 0 ? `（${count}）` : ""}
      </span>
    </span>
  );
}
