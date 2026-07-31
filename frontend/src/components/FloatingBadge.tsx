import { useState } from "react";
import type { HTMLAttributes } from "react";
import { GlassPanel } from "./GlassPanel";
import { Mascot } from "./Mascot";
import { ServiceIcon } from "./ServiceIcon";
import type { ServiceIconType } from "./ServiceIcon";

/**
 * 徽章型態：
 * - `icon`：左側為圓形圖示片（`ServiceIcon`，未指定 `icon` 時退回 `Mascot`）。
 * - `avatar`：左側為圓形人物頭像（`avatarSrc`），無圖或載入失敗時退回姓名縮寫色塊 / `Mascot`。
 */
export type FloatingBadgeVariant = "icon" | "avatar";

interface Props extends Omit<HTMLAttributes<HTMLDivElement>, "children"> {
  /** 徽章主文字（例：「居家清潔」「AI 管家」）。 */
  label: string;
  /** 預設 `"icon"`。 */
  variant?: FloatingBadgeVariant;
  /** `variant="icon"` 時的 `ServiceIcon` 型別；省略則改用 `Mascot`。 */
  icon?: ServiceIconType;
  /** `variant="avatar"` 時的頭像圖片來源；省略或載入失敗時走 fallback。 */
  avatarSrc?: string;
  /** 頭像對應的人名，用於 `alt` 文字與姓名縮寫 fallback。 */
  avatarName?: string;
  /**
   * 附加到頭像 `<img>` 的 className，用於調整裁切。
   *
   * 情境：素材若是「人物在場景中」的方形照片，直接塞進 44px 圓框時臉會過小。
   * 此時可傳入 `scale-*` 與 `origin-*`（圓框本身是 overflow-hidden，等同放大裁切）。
   * 這裡刻意不接受濾鏡類 class：頭像在兩個色彩模式必須是同一份未經調色的影像
   * （Requirement 18.3）。
   */
  avatarClassName?: string;
  /** 選用的次要說明文字（例：「已確認」）。 */
  caption?: string;
}

/**
 * 取姓名縮寫：有空白分隔（拉丁語系）取前兩段首字母；
 * 無空白時，ASCII 名字取前兩個字母，中日韓姓名取前兩個字（例：「王小明」→「王小」）。
 */
function toInitials(name: string | undefined): string {
  const parts = (name ?? "").trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "";
  if (parts.length >= 2) {
    return `${Array.from(parts[0])[0]}${Array.from(parts[1])[0]}`.toUpperCase();
  }
  const chars = Array.from(parts[0]);
  const isAscii = /^[\x20-\x7E]+$/.test(parts[0]);
  return isAscii ? chars.slice(0, 2).join("").toUpperCase() : chars.slice(0, 2).join("");
}

const CIRCLE = "flex h-11 w-11 shrink-0 items-center justify-center overflow-hidden rounded-full";

/**
 * 漂浮徽章卡片：玻璃擬態圓角卡（沿用 `GlassPanel`）+ 圓形圖示／頭像 + 文字，
 * 用於 LandingPage Hero 手機外框周圍的漂浮裝飾元素。
 *
 * 顏色一律取自語意色彩 Token，Light/Dark 共用同一份程式碼。
 * 整張卡設為 `pointer-events-none`，因此漂浮疊在版面上時不會攔截任何可互動元素的觸控區域。
 * `variant="avatar"` 在缺圖或圖片載入失敗時會退回姓名縮寫色塊（有 `avatarName`）或 `Mascot`，不會出現破圖或空白區塊。
 */
export function FloatingBadge({
  label,
  variant = "icon",
  icon,
  avatarSrc,
  avatarName,
  avatarClassName,
  caption,
  className,
  ...rest
}: Props) {
  const [avatarFailed, setAvatarFailed] = useState(false);

  const classes = [
    "pointer-events-none inline-flex select-none items-center gap-3 rounded-2xl px-3.5 py-2.5 shadow-lg",
    className,
  ]
    .filter(Boolean)
    .join(" ");

  const initials = variant === "avatar" ? toInitials(avatarName) : "";
  const showAvatarImage = variant === "avatar" && Boolean(avatarSrc) && !avatarFailed;

  return (
    // data-testid 提供預設值供頁面層測試計數，呼叫端可經 rest 覆寫
    <GlassPanel data-testid="floating-badge" className={classes} {...rest}>
      {variant === "avatar" ? (
        showAvatarImage ? (
          <img
            src={avatarSrc}
            alt={avatarName ?? label}
            onError={() => setAvatarFailed(true)}
            className={`${CIRCLE} border-2 border-[var(--color-primary)] object-cover ${avatarClassName ?? ""}`}
          />
        ) : initials ? (
          <span
            data-testid="floating-badge-initials"
            aria-hidden
            className={`${CIRCLE} bg-[var(--color-primary)] text-base font-semibold text-[var(--color-on-primary)]`}
          >
            {initials}
          </span>
        ) : (
          <span className={`${CIRCLE} bg-[var(--color-primary-soft)]`}>
            <Mascot size={38} tone="brand" />
          </span>
        )
      ) : (
        <span className={`${CIRCLE} bg-[var(--color-primary-soft)] text-[var(--color-primary)]`}>
          {icon ? <ServiceIcon type={icon} size={24} /> : <Mascot size={38} tone="brand" />}
        </span>
      )}

      <span className="flex min-w-0 flex-col">
        <span className="truncate text-base font-semibold text-[var(--color-foreground)]">{label}</span>
        {caption ? (
          <span className="truncate text-sm text-[var(--color-muted-foreground)]">{caption}</span>
        ) : null}
      </span>
    </GlassPanel>
  );
}
