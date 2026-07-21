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
      },
      fontFamily: {
        sans: ['"Noto Sans TC"', "PingFang TC", "Microsoft JhengHei", "sans-serif"],
      },
    },
  },
  plugins: [],
};
