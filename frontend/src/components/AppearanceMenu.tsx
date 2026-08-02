import { useEffect, useRef, useState } from "react";
import { useAccessibilityMode } from "../hooks/useAccessibilityMode";
import { useColorMode, type ColorMode } from "../hooks/useColorMode";
import { useDailyGreeting } from "../hooks/useDailyGreeting";
import { useOnboarding } from "../hooks/useOnboarding";
import { Mascot } from "./Mascot";
import { ServiceIcon } from "./ServiceIcon";

/** 淺色模式圖示（太陽）。線條規格對齊 ServiceIcon：24 viewBox、stroke 1.6、currentColor。 */
function SunIcon({ size = 24 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      <circle cx="12" cy="12" r="4.4" />
      <line x1="12" y1="2.5" x2="12" y2="5" />
      <line x1="12" y1="19" x2="12" y2="21.5" />
      <line x1="2.5" y1="12" x2="5" y2="12" />
      <line x1="19" y1="12" x2="21.5" y2="12" />
      <line x1="5.3" y1="5.3" x2="7.1" y2="7.1" />
      <line x1="16.9" y1="16.9" x2="18.7" y2="18.7" />
      <line x1="18.7" y1="5.3" x2="16.9" y2="7.1" />
      <line x1="7.1" y1="16.9" x2="5.3" y2="18.7" />
    </svg>
  );
}

/** 深色模式圖示（月亮）。 */
function MoonIcon({ size = 24 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      <path d="M20 14.2A8.4 8.4 0 0 1 9.8 4 8.6 8.6 0 1 0 20 14.2z" />
    </svg>
  );
}

const MODE_OPTIONS: ReadonlyArray<{
  mode: ColorMode;
  label: string;
  Icon: (props: { size?: number }) => JSX.Element;
}> = [
  { mode: "light", label: "淺色", Icon: SunIcon },
  { mode: "dark", label: "深色", Icon: MoonIcon },
];

/**
 * 外觀設定選單：點左上角管家頭像才展開，平常不佔版面。
 * 取代舊的 `ThemeMenu`（5 色塊選色），改為 Light / Dark 兩個模式選項，
 * 並保留既有的無障礙模式開關與「重看導覽」入口。
 */
export function AppearanceMenu() {
  const { mode, setMode } = useColorMode();
  const { enabled: a11yEnabled, toggle: toggleA11y } = useAccessibilityMode();
  const { reopen: reopenOnboarding } = useOnboarding();
  const { reopen: reopenGreeting } = useDailyGreeting();
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function onPointerDown(e: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(false);
    }
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  return (
    <div ref={rootRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="true"
        aria-expanded={open}
        aria-label="開啟外觀設定"
        className="flex h-14 w-14 items-center justify-center rounded-2xl bg-[var(--color-surface)] shadow-sm transition hover:shadow-md focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand"
      >
        <Mascot size={36} />
      </button>

      {open && (
        <div
          role="menu"
          aria-label="外觀設定"
          className="absolute left-0 top-[calc(100%+8px)] z-30 w-[17rem] rounded-[24px] border border-[var(--color-border)] bg-[var(--color-surface)] p-4 shadow-xl"
        >
          <p className="mb-3 text-sm font-bold text-[var(--color-muted-foreground)]">外觀設定</p>

          <div className="grid grid-cols-2 gap-3">
            {MODE_OPTIONS.map(({ mode: optionMode, label, Icon }) => {
              const active = optionMode === mode;
              return (
                <button
                  key={optionMode}
                  type="button"
                  role="menuitemradio"
                  aria-checked={active}
                  aria-label={`切換為${label}模式`}
                  onClick={() => {
                    setMode(optionMode);
                    setOpen(false);
                  }}
                  className={`flex min-h-[44px] min-w-[44px] flex-col items-center gap-1.5 rounded-2xl border-2 p-2 transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand ${
                    active
                      ? "border-brand bg-brand-soft"
                      : "border-transparent hover:border-[var(--color-border)]"
                  }`}
                >
                  <span
                    className={`flex h-12 w-12 items-center justify-center rounded-2xl ${
                      active ? "text-brand" : "text-[var(--color-muted-foreground)]"
                    }`}
                  >
                    <Icon size={26} />
                  </span>
                  <span className="text-xs font-bold text-[var(--color-foreground)]">
                    {label}
                    {active ? "：使用中" : ""}
                  </span>
                </button>
              );
            })}
          </div>

          <button
            type="button"
            role="menuitemcheckbox"
            aria-checked={a11yEnabled}
            aria-label="切換無障礙模式"
            onClick={toggleA11y}
            className={`mt-3 flex min-h-[44px] w-full items-center gap-2 rounded-2xl border-2 px-2 py-2.5 text-left transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand ${
              a11yEnabled
                ? "border-brand bg-brand-soft"
                : "border-transparent hover:border-[var(--color-border)]"
            }`}
          >
            <span
              className={`flex h-9 w-9 items-center justify-center rounded-xl ${
                a11yEnabled ? "text-brand" : "text-[var(--color-muted-foreground)]"
              }`}
            >
              <ServiceIcon type="zoom" size={20} />
            </span>
            <span className="text-xs font-bold text-[var(--color-foreground)]">
              無障礙模式{a11yEnabled ? "：已開啟" : "：已關閉"}
            </span>
          </button>

          <button
            type="button"
            onClick={() => {
              reopenOnboarding();
              setOpen(false);
            }}
            className="mt-2 flex min-h-[44px] w-full items-center gap-2 rounded-2xl border-2 border-transparent px-2 py-2.5 text-left transition hover:border-[var(--color-border)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand"
          >
            <span className="flex h-9 w-9 items-center justify-center rounded-xl text-[var(--color-muted-foreground)]">
              <ServiceIcon type="info" size={18} />
            </span>
            <span className="text-xs font-bold text-[var(--color-foreground)]">重新觀看新手導覽</span>
          </button>

          {/*
            問候卡一天只會自動跳一次（見 useDailyGreeting）。使用者早上隨手關掉之後
            想再看今天有什麼安排，就從這裡叫回來，不必等到明天。
          */}
          <button
            type="button"
            onClick={() => {
              reopenGreeting();
              setOpen(false);
            }}
            className="mt-2 flex min-h-[44px] w-full items-center gap-2 rounded-2xl border-2 border-transparent px-2 py-2.5 text-left transition hover:border-[var(--color-border)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand"
          >
            <span className="flex h-9 w-9 items-center justify-center rounded-xl text-[var(--color-muted-foreground)]">
              <ServiceIcon type="sun" size={18} />
            </span>
            <span className="text-xs font-bold text-[var(--color-foreground)]">重看今日問候</span>
          </button>
        </div>
      )}
    </div>
  );
}
