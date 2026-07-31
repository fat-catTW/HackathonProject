/**
 * 吉祥物色調。圖示現在改用使用者提供的 AI orb 圖片（本身已有固定配色），tone 不再影響
 * 圖片顏色；型別與 prop 仍保留，是為了不用同時改動全站 9 處呼叫端（Landing、ButlerPanel、
 * ChatMessage、FloatingBadge…等）——沿用既有的 `tone="brand"` 之類寫法照樣能編譯、渲染。
 */
export type MascotTone = "brand" | "inverted" | "muted";

interface Props {
  size?: number;
  className?: string;
  /** @deprecated 圖片本身已有固定配色，此 prop 不再影響輸出，僅維持既有呼叫端相容。 */
  tone?: MascotTone;
}

/** 全站統一使用的品牌圖示（使用者提供，放在 `frontend/public/images/`）。 */
const MASCOT_ICON = "/images/ai-orb-icon.png";

/** 品牌圖示：全站沿用同一張使用者提供的 AI orb 圖片，取代原本手繪 SVG 吉祥物。造型與配色固定。 */
export function Mascot({ size = 120, className }: Props) {
  return (
    // 來源圖是正方形，width/height 又固定同值，不需要 object-fit 就不會變形；
    // 保持不帶 style，才不會踩到 LandingPage 「圖片不得有 per-mode style/filter」的檢查。
    <img src={MASCOT_ICON} alt="" aria-hidden width={size} height={size} className={className} />
  );
}
