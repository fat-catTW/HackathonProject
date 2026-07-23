/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        paper: "#FFFDF8",
        ink: "#1F2933",
        pine: { DEFAULT: "#14655B", dark: "#0E4A43", soft: "#E3F0EE" },
        amber: { DEFAULT: "#E8A13D", soft: "#FBF1DF" },
        leaf: { DEFAULT: "#2E9E5B", soft: "#E5F4EB" },
        sky: { DEFAULT: "#2C7FB8", soft: "#E4F0F8" },
        brand: { DEFAULT: "#0F4C81", dark: "#0A3A63", soft: "#EAF1F8" },
        accent: { DEFAULT: "#F2A93B", soft: "#FDF3E1" },
        canvas: "#EEF1F4",
        paper2: "#FAF9F6",
        success: { DEFAULT: "#2FA766", soft: "#E7F5EC" },
        info: { DEFAULT: "#2C7BE5", soft: "#EAF1FC" },
        danger: "#C0392B",
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
