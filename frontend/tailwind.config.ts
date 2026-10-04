import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        paper: "#f4efe6",
        "paper-deep": "#ebe9df",
        ink: "#241c18",
        "ink-soft": "#5e554e",
        chili: "#c45a56",
        "chili-dark": "#a74946",
        moss: "#1f3315",
        gold: "#8ea35e",
        card: "#fbf8f2",
        line: "#e2e0d7",
        canvas: "#fcfcfc",
        fill: "#d9d9d9",
        coral: "#d96b67",
        croc: "#b5c384",
        "croc-dark": "#8ea35e",
        orange: "#ee8f55",
        "coral-dark": "#c45a56",
      },
      fontFamily: {
        serif: ["var(--font-serif)", "Georgia", "serif"],
        sans: ["var(--font-sans)", "Segoe UI", "sans-serif"],
      },
      boxShadow: {
        card: "0 24px 60px rgba(36, 28, 24, 0.12)",
      },
    },
  },
  plugins: [],
};

export default config;