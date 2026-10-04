import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        paper: "#f4efe6",
        "paper-deep": "#e7dfd1",
        ink: "#241c18",
        "ink-soft": "#5e554e",
        chili: "#d84a2f",
        "chili-dark": "#b33820",
        moss: "#1f6b4a",
        gold: "#c9842a",
        card: "#fffaf3",
        line: "#e3d8c8",
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
