/* icon／卡片底色在紫、桃紅、青、藍四色間輪替，刻意讓多種色相同時出現在同一個畫面，
   不是只有單一品牌色的深淺變化。HomePage 的服務捷徑列跟所有服務視窗共用同一份配色順序。 */
export const SERVICE_TONES = [
  { soft: "var(--color-primary-soft)", ink: "var(--color-primary)" },
  { soft: "var(--color-secondary-soft)", ink: "var(--color-secondary)" },
  { soft: "var(--color-tertiary-soft)", ink: "var(--color-tertiary)" },
  { soft: "var(--color-info-soft)", ink: "var(--color-info)" },
] as const;
