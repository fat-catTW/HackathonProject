/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // 既有別名一律指向 index.css 的語意色彩變數，使同一組 className 同時支援 Light/Dark 兩模式
        paper: "var(--color-background)",
        ink: "var(--color-foreground)",
        pine: { DEFAULT: "#14655B", dark: "#0E4A43", soft: "#E3F0EE" },
        amber: { DEFAULT: "#E8A13D", soft: "#FBF1DF" },
        leaf: { DEFAULT: "#2E9E5B", soft: "#E5F4EB" },
        sky: { DEFAULT: "#2C7FB8", soft: "#E4F0F8" },
        brand: {
          DEFAULT: "var(--color-primary)",
          dark: "var(--color-primary-hover)",
          soft: "var(--color-primary-soft)",
        },
        secondary: { DEFAULT: "var(--color-secondary)", soft: "var(--color-secondary-soft)" },
        tertiary: { DEFAULT: "var(--color-tertiary)", soft: "var(--color-tertiary-soft)" },
        mascotHighlight: "var(--color-mascot-accent)",
        canvas: "var(--color-canvas)",
        accent: { DEFAULT: "var(--color-warning)", soft: "var(--color-warning-soft)" },
        paper2: "#FAF9F6",
        success: { DEFAULT: "var(--color-success)", soft: "var(--color-success-soft)" },
        info: { DEFAULT: "var(--color-info)", soft: "var(--color-info-soft)" },
        danger: "var(--color-danger)",
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
