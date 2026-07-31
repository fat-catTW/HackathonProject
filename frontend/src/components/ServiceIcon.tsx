export type ServiceIconType =
  | "aircon" | "plumbing" | "appliance" | "cleaning" | "pest" | "moving" | "restaurant" | "delivery" | "health"
  | "mic" | "send" | "check" | "chevronRight" | "chevronDown" | "close"
  | "back" | "phone" | "location" | "calendar" | "clock" | "chat"
  | "info" | "warning" | "logo" | "zoom" | "shop" | "home" | "sun" | "moon" | "more";

interface Props {
  type: ServiceIconType;
  size?: number;
  className?: string;
  /** 線條粗細，預設 1.6。重點展示場合（例如服務卡大圖示）可以加粗，讓圖示更有份量、不單薄。 */
  strokeWidth?: number;
}

const PATHS: Record<ServiceIconType, JSX.Element> = {
  aircon: (
    <>
      <line x1="3" y1="12" x2="21" y2="12" /><line x1="7.5" y1="4.2" x2="16.5" y2="19.8" />
      <line x1="16.5" y1="4.2" x2="7.5" y2="19.8" />
      <circle cx="3" cy="12" r="0.9" fill="currentColor" stroke="none" />
      <circle cx="21" cy="12" r="0.9" fill="currentColor" stroke="none" />
      <circle cx="7.5" cy="4.2" r="0.9" fill="currentColor" stroke="none" />
      <circle cx="16.5" cy="19.8" r="0.9" fill="currentColor" stroke="none" />
      <circle cx="16.5" cy="4.2" r="0.9" fill="currentColor" stroke="none" />
      <circle cx="7.5" cy="19.8" r="0.9" fill="currentColor" stroke="none" />
    </>
  ),
  plumbing: (
    <>
      <circle cx="6.2" cy="6.2" r="3" /><line x1="8.4" y1="8.4" x2="15.3" y2="15.3" />
      <circle cx="17.8" cy="17.8" r="3" />
      <line x1="4" y1="8.4" x2="8.4" y2="4" /><line x1="15.6" y1="20" x2="20" y2="15.6" />
    </>
  ),
  appliance: (
    <>
      <rect x="7" y="10" width="10" height="8" rx="2" />
      <line x1="10" y1="10" x2="10" y2="4" /><line x1="14" y1="10" x2="14" y2="4" />
      <line x1="9.5" y1="18" x2="9.5" y2="21" /><line x1="14.5" y1="18" x2="14.5" y2="21" />
    </>
  ),
  cleaning: (
    <>
      <circle cx="8" cy="16" r="4" /><circle cx="15.5" cy="9" r="3" /><circle cx="18.5" cy="16.5" r="2" />
    </>
  ),
  pest: (
    <>
      <ellipse cx="12" cy="14" rx="4" ry="5.5" /><circle cx="12" cy="7" r="2.2" />
      <line x1="10.5" y1="5" x2="9" y2="3" /><line x1="13.5" y1="5" x2="15" y2="3" />
      <line x1="8.2" y1="11" x2="4.5" y2="9.2" /><line x1="8" y1="14" x2="4" y2="14" /><line x1="8.2" y1="17" x2="4.5" y2="18.8" />
      <line x1="15.8" y1="11" x2="19.5" y2="9.2" /><line x1="16" y1="14" x2="20" y2="14" /><line x1="15.8" y1="17" x2="19.5" y2="18.8" />
    </>
  ),
  moving: (
    <>
      <rect x="4" y="8.5" width="16" height="11.5" rx="1.5" />
      <line x1="4" y1="14" x2="20" y2="14" /><line x1="12" y1="8.5" x2="12" y2="20" />
      <path d="M8 8.5 L9.3 4.8 H14.7 L16 8.5" />
    </>
  ),
  restaurant: (
    <>
      <circle cx="8" cy="12" r="5.5" />
      <line x1="16.5" y1="4" x2="16.5" y2="20" />
      <path d="M14.5 4 V10 a2 2 0 0 0 4 0 V4" />
    </>
  ),
  delivery: (
    <>
      <circle cx="6.5" cy="18" r="2.3" />
      <circle cx="17.5" cy="18" r="2.3" />
      <path d="M6.5 18 H11 L13.5 8.5 H16.5" />
      <rect x="14.5" y="4.5" width="5" height="4" rx="1" />
    </>
  ),
  health: (
    <>
      <path d="M12 20.5s-7.5-4.6-9.3-9.4C1.6 7.7 3.6 5 6.6 5c1.8 0 3.3.9 4.2 2.3l1.2 1.8 1.2-1.8C14.1 5.9 15.6 5 17.4 5c3 0 5 2.7 3.9 6.1C19.5 15.9 12 20.5 12 20.5z" />
      <line x1="9" y1="11.5" x2="15" y2="11.5" />
      <line x1="12" y1="8.5" x2="12" y2="14.5" />
    </>
  ),
  mic: (
    <>
      <rect x="9" y="3" width="6" height="11" rx="3" />
      <path d="M5 11a7 7 0 0 0 14 0" />
      <line x1="12" y1="18" x2="12" y2="21.5" /><line x1="8.3" y1="21.5" x2="15.7" y2="21.5" />
    </>
  ),
  send: (
    <>
      <path d="M4 12 L20 4 L13.5 20 L11 13 Z" /><line x1="11" y1="13" x2="20" y2="4" />
    </>
  ),
  check: <path d="M4 12.5 L9.5 18 L20 5.5" />,
  chevronRight: <path d="M9 5 L16 12 L9 19" />,
  chevronDown: <path d="M5 9 L12 16 L19 9" />,
  close: (
    <>
      <line x1="5" y1="5" x2="19" y2="19" /><line x1="19" y1="5" x2="5" y2="19" />
    </>
  ),
  back: <path d="M15 5 L8 12 L15 19" />,
  phone: (
    <>
      <rect x="8" y="2" width="8" height="20" rx="2" /><line x1="11" y1="18" x2="13" y2="18" />
    </>
  ),
  location: (
    <>
      <path d="M12 21s7-7.2 7-12a7 7 0 1 0-14 0c0 4.8 7 12 7 12z" /><circle cx="12" cy="9" r="2.3" />
    </>
  ),
  calendar: (
    <>
      <rect x="3.5" y="5" width="17" height="15" rx="2" /><line x1="3.5" y1="9.5" x2="20.5" y2="9.5" />
      <line x1="8" y1="3" x2="8" y2="7" /><line x1="16" y1="3" x2="16" y2="7" />
    </>
  ),
  clock: (
    <>
      <circle cx="12" cy="12" r="8.5" /><line x1="12" y1="12" x2="12" y2="7" /><line x1="12" y1="12" x2="15.5" y2="14" />
    </>
  ),
  chat: <path d="M4 5h16a1 1 0 0 1 1 1v9a1 1 0 0 1-1 1H9l-4.5 4v-4H4a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1z" />,
  info: (
    <>
      <circle cx="12" cy="12" r="8.5" /><line x1="12" y1="11" x2="12" y2="16.5" />
      <circle cx="12" cy="7.7" r="1" fill="currentColor" stroke="none" />
    </>
  ),
  warning: (
    <>
      <path d="M12 3.5 L21.5 20 H2.5 Z" /><line x1="12" y1="9.5" x2="12" y2="14" />
      <circle cx="12" cy="17" r="1" fill="currentColor" stroke="none" />
    </>
  ),
  logo: (
    <>
      <circle cx="12" cy="12" r="9.3" /><path d="M7.7 12.4 L10.6 15.4 L16.4 9" />
    </>
  ),
  zoom: (
    <>
      <circle cx="10" cy="10" r="6.5" /><line x1="14.8" y1="14.8" x2="20" y2="20" />
    </>
  ),
  shop: (
    <>
      <path d="M7 9 L6 18 Q6 20 8 20 L16 20 Q18 20 18 18 L17 9" />
      <line x1="9" y1="9" x2="9" y2="3" /><line x1="15" y1="9" x2="15" y2="3" />
    </>
  ),
  home: (
    <>
      <path d="M4 11.5 L12 4 L20 11.5" /><path d="M6 10 V20 H18 V10" />
      <line x1="10" y1="20" x2="10" y2="14.5" /><line x1="14" y1="20" x2="14" y2="14.5" />
      <line x1="10" y1="14.5" x2="14" y2="14.5" />
    </>
  ),
  sun: (
    <>
      <circle cx="12" cy="12" r="4.4" />
      <line x1="12" y1="2.5" x2="12" y2="5" /><line x1="12" y1="19" x2="12" y2="21.5" />
      <line x1="2.5" y1="12" x2="5" y2="12" /><line x1="19" y1="12" x2="21.5" y2="12" />
      <line x1="5.3" y1="5.3" x2="7.1" y2="7.1" /><line x1="16.9" y1="16.9" x2="18.7" y2="18.7" />
      <line x1="18.7" y1="5.3" x2="16.9" y2="7.1" /><line x1="7.1" y1="16.9" x2="5.3" y2="18.7" />
    </>
  ),
  moon: <path d="M20 14.2A8.4 8.4 0 0 1 9.8 4 8.6 8.6 0 1 0 20 14.2z" />,
  more: (
    <>
      <circle cx="5" cy="12" r="1.6" fill="currentColor" stroke="none" />
      <circle cx="12" cy="12" r="1.6" fill="currentColor" stroke="none" />
      <circle cx="19" cy="12" r="1.6" fill="currentColor" stroke="none" />
    </>
  ),
};

/** 服務/介面圖示（原始 SVG 來自設計稿 ServiceIcon.dc.html）。未知 type 時 fallback 為 chat 圖示。 */
export function ServiceIcon({ type, size = 24, className, strokeWidth = 1.6 }: Props) {
  const content = PATHS[type] ?? PATHS.chat;
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden
    >
      {content}
    </svg>
  );
}
