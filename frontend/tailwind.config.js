/*
 * 語意色 Token 都是 CSS 變數，Tailwind 沒辦法把透明度直接塞進 `var(--color-primary)`：
 * 色票若只寫成字串，`bg-brand/5`、`border-tertiary/50` 這種帶透明度的 class 會整條
 * 規則產不出來——畫面上不是「淡一點」，而是那個顏色根本沒套上（邊框掉回預設灰、
 * 底色完全不見），而且沒有任何錯誤訊息，很容易寫了以為有效。
 *
 * 改成用函式定義色票：沒帶透明度時輸出原本的 var()（跟以前完全一樣），帶了就用
 * color-mix 混進 transparent，兩種寫法都會產生 CSS。opacityValue 在某些工具類會是
 * `var(--tw-bg-opacity)` 這種字串（不是數字），那種情況一樣退回不透明的 var()。
 */
const withAlpha =
  (variable) =>
  ({ opacityValue } = {}) => {
    const alpha = Number(opacityValue);
    if (!Number.isFinite(alpha) || alpha >= 1) return `var(${variable})`;
    return `color-mix(in srgb, var(${variable}) ${alpha * 100}%, transparent)`;
  };

/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // 既有別名一律指向 index.css 的語意色彩變數，使同一組 className 同時支援 Light/Dark 兩模式
        paper: withAlpha("--color-background"),
        ink: withAlpha("--color-foreground"),
        pine: { DEFAULT: "#14655B", dark: "#0E4A43", soft: "#E3F0EE" },
        amber: { DEFAULT: "#E8A13D", soft: "#FBF1DF" },
        leaf: { DEFAULT: "#2E9E5B", soft: "#E5F4EB" },
        sky: { DEFAULT: "#2C7FB8", soft: "#E4F0F8" },
        brand: {
          DEFAULT: withAlpha("--color-primary"),
          dark: withAlpha("--color-primary-hover"),
          soft: withAlpha("--color-primary-soft"),
        },
        secondary: {
          DEFAULT: withAlpha("--color-secondary"),
          soft: withAlpha("--color-secondary-soft"),
        },
        tertiary: {
          DEFAULT: withAlpha("--color-tertiary"),
          soft: withAlpha("--color-tertiary-soft"),
        },
        surface: withAlpha("--color-surface"),
        mascotHighlight: withAlpha("--color-mascot-accent"),
        canvas: withAlpha("--color-canvas"),
        accent: { DEFAULT: withAlpha("--color-warning"), soft: withAlpha("--color-warning-soft") },
        paper2: "#FAF9F6",
        success: { DEFAULT: withAlpha("--color-success"), soft: withAlpha("--color-success-soft") },
        info: { DEFAULT: withAlpha("--color-info"), soft: withAlpha("--color-info-soft") },
        danger: withAlpha("--color-danger"),
      },
      fontFamily: {
        sans: ['"Noto Sans TC"', "PingFang TC", "Microsoft JhengHei", "sans-serif"],
        serif: ['"Noto Serif TC"', "serif"],
      },
      spacing: {
        "4.5": "1.125rem",
        "5.5": "1.375rem",
        "13": "3.25rem",
        "15": "3.75rem",
        "19": "4.75rem",
        "21": "5.25rem",
      },
    },
  },
  plugins: [],
};
