import type { HTMLAttributes, ReactNode } from "react";

interface Props extends HTMLAttributes<HTMLDivElement> {
  children?: ReactNode;
}

/**
 * 手機外框：純 CSS 做出機身、頂部 notch、側邊按鍵與立體陰影，`children` 承載實際 UI 縮小示意。
 * 不使用 `iframe`、不依賴任何外部圖片素材。機身刻意採深色機殼（不隨 Light/Dark 模式變動，
 * 真實裝置的金屬／玻璃機身本來就不會因為 App 主題換色），並加一道斜向玻璃反光，
 * 讓手機讀起來像一張「有光澤的實體裝置照片」而不是純色圓角方框。
 * 機身裝飾件一律 `aria-hidden` + `pointer-events-none`，不會攔截 `children` 內可互動元素的觸控區域。
 */
export function PhoneMockup({ className, children, ...rest }: Props) {
  const classes = [
    // aspect-[9/19.5]：真實手機的長寬比例（例如 iPhone），取代先前完全依內容撐高、
    // 導致外框看起來過矮過方的問題；寬度固定、高度由比例換算，不受 children 內容多寡影響。
    "relative mx-auto aspect-[9/19.5] w-[16.5rem] max-w-full rounded-[2.6rem] p-2.5",
    "shadow-[0_50px_90px_-30px_rgba(0,0,0,0.55)]",
    className,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    // data-testid 提供預設值供頁面層測試定位，呼叫端可經 rest 覆寫
    <div
      data-testid="phone-mockup"
      className={classes}
      style={{
        backgroundImage:
          "linear-gradient(155deg, rgba(70,68,86,1) 0%, rgba(18,17,24,1) 45%, rgba(38,36,48,1) 100%)",
      }}
      {...rest}
    >
      {/* 機身玻璃反光：斜向亮帶疊在深色機殼上，模擬鏡面反光 */}
      <span
        aria-hidden
        className="pointer-events-none absolute inset-0 rounded-[2.6rem]"
        style={{
          backgroundImage:
            "linear-gradient(115deg, transparent 28%, rgba(255,255,255,0.16) 45%, rgba(255,255,255,0.04) 56%, transparent 72%)",
        }}
      />

      {/* 側邊按鍵（純 CSS 幾何 + 陰影，僅裝飾） */}
      <span
        aria-hidden
        className="pointer-events-none absolute -left-[3px] top-[22%] h-9 w-[3px] rounded-l-full bg-black/40 shadow-sm"
      />
      <span
        aria-hidden
        className="pointer-events-none absolute -left-[3px] top-[36%] h-14 w-[3px] rounded-l-full bg-black/40 shadow-sm"
      />
      <span
        aria-hidden
        className="pointer-events-none absolute -right-[3px] top-[30%] h-12 w-[3px] rounded-r-full bg-black/40 shadow-sm"
      />

      {/*
        螢幕：h-full 撐滿外框（由 aspect-ratio 決定的）實際高度；notch／底部指示條維持絕對定位，
        children 改放進 flex-1 的內容區塊並自行 pt/pb 預留缺口空間，確保 children 也能撐滿整個螢幕
        （而不是只佔外框裡「內容需要的高度」）。
      */}
      <div className="relative flex h-full flex-col overflow-hidden rounded-[2.1rem] bg-[var(--color-canvas)]">
        <span
          aria-hidden
          className="pointer-events-none absolute left-1/2 top-2 z-10 h-4 w-20 -translate-x-1/2 rounded-full bg-black/70"
        />
        <div className="min-h-0 flex-1 overflow-hidden pb-4 pt-8">{children}</div>
        <span
          aria-hidden
          className="pointer-events-none absolute bottom-1.5 left-1/2 h-1 w-16 -translate-x-1/2 rounded-full bg-[var(--color-muted-foreground)] opacity-60"
        />
      </div>
    </div>
  );
}
