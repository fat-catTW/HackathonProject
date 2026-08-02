import { useLocation, useNavigate } from "react-router-dom";
import { ServiceIcon } from "./ServiceIcon";
import type { ServiceIconType } from "./ServiceIcon";
import { useColorMode } from "../hooks/useColorMode";

interface NavItem {
  key: string;
  label: string;
  icon: ServiceIconType;
  path: string;
  tone: "primary" | "secondary" | "tertiary";
}

const NAV_ITEMS: readonly NavItem[] = [
  { key: "home", label: "首頁", icon: "home", path: "/home", tone: "primary" },
  { key: "chat", label: "AI 管家", icon: "chat", path: "/new", tone: "secondary" },
  { key: "services", label: "我的服務", icon: "calendar", path: "/my-services", tone: "tertiary" },
];

const TONE_VARS: Record<NavItem["tone"], { ink: string; soft: string }> = {
  primary: { ink: "var(--color-primary)", soft: "var(--color-primary-soft)" },
  secondary: { ink: "var(--color-secondary)", soft: "var(--color-secondary-soft)" },
  tertiary: { ink: "var(--color-tertiary)", soft: "var(--color-tertiary-soft)" },
};

interface Props {
  /**
   * `"floating"`（預設）：`fixed` 浮在畫面底部，用於一般可捲動頁面（HomePage、MyServicesPage）。
   * `"static"`：正常文件流中的一般元素，用於本身已是 `h-dvh` 版面殼層、且底部已有輸入框等
   * 固定元素的頁面（例如 ButlerPanel），避免兩個 `fixed` 元素互相疊住。
   */
  variant?: "floating" | "static";
}

/**
 * 底部分頁導覽列（對應聊天機器人 App 參考稿的 Home / Chat / ... 分頁列）。
 * `floating` 模式下使用頁面需自行在主要內容底部保留足夠留白（例如 `pb-28`），避免內容被蓋住。
 */
export function BottomNav({ variant = "floating" }: Props) {
  const location = useLocation();
  const navigate = useNavigate();
  const { mode, toggle } = useColorMode();

  const bar = (
    <div
      className={
        variant === "floating"
          ? // bg-surface/95：透明度要走色票別名才會生效，寫成 bg-[var(--color-surface)]/95
            // 產不出 CSS（見 tailwind.config.js 的 withAlpha），那樣毛玻璃底下會整片透空。
            "flex w-full max-w-md items-center gap-1 rounded-[28px] border border-[var(--color-border)] bg-surface/95 p-2 shadow-[0_20px_50px_-20px_rgba(0,0,0,0.4)] backdrop-blur"
          : "flex w-full items-center gap-1 border-t border-[var(--color-border)] bg-[var(--color-surface)] p-2 pb-[max(0.5rem,env(safe-area-inset-bottom))]"
      }
    >
      {NAV_ITEMS.map((item) => {
          const active = location.pathname === item.path;
          const tone = TONE_VARS[item.tone];
          return (
            <button
              key={item.key}
              type="button"
              onClick={() => navigate(item.path)}
              aria-current={active ? "page" : undefined}
              className="flex min-h-[44px] flex-1 flex-col items-center gap-1 rounded-2xl py-1.5 transition"
              style={{ background: active ? tone.soft : "transparent" }}
            >
              <span
                className="flex h-8 w-8 items-center justify-center"
                style={{ color: active ? tone.ink : "var(--color-muted-foreground)" }}
              >
                <ServiceIcon type={item.icon} size={22} />
              </span>
              <span
                className="text-xs font-bold"
                style={{ color: active ? tone.ink : "var(--color-muted-foreground)" }}
              >
                {item.label}
              </span>
            </button>
          );
        })}

        <button
          type="button"
          onClick={toggle}
          aria-label={mode === "light" ? "切換為深色模式" : "切換為淺色模式"}
          className="flex min-h-[44px] flex-1 flex-col items-center gap-1 rounded-2xl py-1.5 text-[var(--color-muted-foreground)] transition hover:text-[var(--color-warning)]"
        >
          <span className="flex h-8 w-8 items-center justify-center">
            <ServiceIcon type={mode === "light" ? "moon" : "sun"} size={22} />
          </span>
          <span className="text-xs font-bold">外觀</span>
        </button>
    </div>
  );

  if (variant === "static") {
    return (
      <nav aria-label="主要導覽" className="shrink-0">
        {bar}
      </nav>
    );
  }

  return (
    <nav
      aria-label="主要導覽"
      className="fixed inset-x-0 bottom-0 z-30 flex justify-center px-4 pb-[max(1rem,env(safe-area-inset-bottom))]"
    >
      {bar}
    </nav>
  );
}
