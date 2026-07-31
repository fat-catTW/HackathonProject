/**
 * WCAG 2.1 相對亮度與對比比值計算
 *
 * 依 WCAG 2.1 定義實作：
 * - 相對亮度 https://www.w3.org/TR/WCAG21/#dfn-relative-luminance
 * - 對比比值 https://www.w3.org/TR/WCAG21/#dfn-contrast-ratio
 *
 * 半透明色（例如 Dark 模式的 `rgba(59, 130, 246, 0.16)` 色塊）無法單獨算對比，
 * 需先用 `compositeOver` 疊到不透明底色上，取得實際呈現的色值後再計算。
 */

export interface Rgba {
  /** 0–255 */
  r: number;
  /** 0–255 */
  g: number;
  /** 0–255 */
  b: number;
  /** 0–1 */
  a: number;
}

/** WCAG 2.1 AA 門檻：一般內文 4.5:1、大型文字與圖形物件 3:1。 */
export const WCAG_AA_BODY_TEXT = 4.5;
export const WCAG_AA_LARGE_TEXT = 3;

const HEX_PATTERN = /^#([0-9a-f]{3}|[0-9a-f]{6})$/i;
const RGB_PATTERN = /^rgba?\(([^)]+)\)$/i;

/** 解析 CSS 色彩字串，支援 `#RGB`、`#RRGGBB`、`rgb()`、`rgba()`。 */
export function parseCssColor(value: string): Rgba {
  const input = value.trim();

  const hex = HEX_PATTERN.exec(input);
  if (hex) {
    const digits = hex[1];
    const expanded =
      digits.length === 3
        ? digits
            .split("")
            .map((char) => char + char)
            .join("")
        : digits;
    return {
      r: Number.parseInt(expanded.slice(0, 2), 16),
      g: Number.parseInt(expanded.slice(2, 4), 16),
      b: Number.parseInt(expanded.slice(4, 6), 16),
      a: 1,
    };
  }

  const rgb = RGB_PATTERN.exec(input);
  if (rgb) {
    const parts = rgb[1]
      .split(/[,/]/)
      .map((part) => part.trim())
      .filter((part) => part.length > 0);
    if (parts.length < 3) {
      throw new Error(`無法解析色彩字串：${value}`);
    }
    const channel = (part: string): number =>
      part.endsWith("%") ? (Number.parseFloat(part) / 100) * 255 : Number.parseFloat(part);
    const alpha = parts[3] === undefined ? 1 : Number.parseFloat(parts[3]);
    const parsed = {
      r: channel(parts[0]),
      g: channel(parts[1]),
      b: channel(parts[2]),
      a: parts[3]?.endsWith("%") ? alpha / 100 : alpha,
    };
    if (Object.values(parsed).some((component) => Number.isNaN(component))) {
      throw new Error(`無法解析色彩字串：${value}`);
    }
    return parsed;
  }

  throw new Error(`無法解析色彩字串：${value}`);
}

/** 將半透明前景色以 source-over 方式疊到底色上，回傳不透明結果色。 */
export function compositeOver(foreground: Rgba, background: Rgba): Rgba {
  if (background.a !== 1) {
    throw new Error("底色必須為不透明色，請先逐層疊合至不透明底色");
  }
  const alpha = foreground.a;
  return {
    r: foreground.r * alpha + background.r * (1 - alpha),
    g: foreground.g * alpha + background.g * (1 - alpha),
    b: foreground.b * alpha + background.b * (1 - alpha),
    a: 1,
  };
}

/** WCAG 2.1 相對亮度。 */
export function relativeLuminance(color: Rgba): number {
  const toLinear = (channel: number): number => {
    const normalized = channel / 255;
    return normalized <= 0.03928
      ? normalized / 12.92
      : Math.pow((normalized + 0.055) / 1.055, 2.4);
  };
  return (
    0.2126 * toLinear(color.r) + 0.7152 * toLinear(color.g) + 0.0722 * toLinear(color.b)
  );
}

/** WCAG 2.1 對比比值（1–21），兩個參數皆須為不透明色。 */
export function contrastRatio(a: Rgba, b: Rgba): number {
  const luminanceA = relativeLuminance(a);
  const luminanceB = relativeLuminance(b);
  const lighter = Math.max(luminanceA, luminanceB);
  const darker = Math.min(luminanceA, luminanceB);
  return (lighter + 0.05) / (darker + 0.05);
}
