interface Props {
  size?: number;
  className?: string;
  /** 強制指定機器人主色，不給則自動跟隨目前主題（--color-brand）。用於主題選色器同時顯示多種顏色。 */
  bodyColor?: string;
  /** 強制指定機器人強調色，不給則自動跟隨目前主題（--color-mascot-highlight）。 */
  highlightColor?: string;
}

/** 品牌吉祥物圖示（原始 SVG 來自設計稿 Mascot.dc.html）。顏色隨主題切換，造型固定。 */
export function Mascot({ size = 120, className, bodyColor, highlightColor }: Props) {
  const body = bodyColor ?? "var(--color-brand)";
  const highlight = highlightColor ?? "var(--color-mascot-highlight)";

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 200 220"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-hidden
    >
      <line x1="100" y1="8" x2="100" y2="32" stroke={body} strokeWidth="7" strokeLinecap="round" />
      <circle cx="100" cy="8" r="10" fill={highlight} />
      <ellipse cx="48" cy="172" rx="15" ry="21" fill={body} transform="rotate(-18 48 172)" />
      <ellipse cx="154" cy="150" rx="14" ry="20" fill={body} transform="rotate(38 154 150)" />
      <rect x="56" y="138" width="88" height="68" rx="32" fill={body} />
      <circle cx="100" cy="166" r="17" fill="#FFFFFF" />
      <path d="M100 176 L91 165 A6.5 6.5 0 0 1 100 156 A6.5 6.5 0 0 1 109 165 Z" fill={highlight} />
      <rect x="24" y="28" width="152" height="122" rx="48" fill={body} />
      <circle cx="24" cy="90" r="11" fill={highlight} />
      <circle cx="176" cy="90" r="11" fill={highlight} />
      <rect x="47" y="55" width="106" height="74" rx="30" fill="#FFFFFF" />
      <circle cx="80" cy="90" r="8.5" fill={body} />
      <circle cx="120" cy="90" r="8.5" fill={body} />
      <circle cx="65" cy="108" r="6.5" fill="#F7B8A3" opacity="0.85" />
      <circle cx="135" cy="108" r="6.5" fill="#F7B8A3" opacity="0.85" />
      <path d="M84 109 Q100 124 116 109" stroke={body} strokeWidth="4.5" fill="none" strokeLinecap="round" />
    </svg>
  );
}
