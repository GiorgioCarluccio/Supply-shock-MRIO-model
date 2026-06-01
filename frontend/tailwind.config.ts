import type { Config } from "tailwindcss";

/**
 * OpenEconomics brand palette.
 * Core foundation is black/white; Bluette is the primary accent, Lime the
 * secondary accent used sparingly for positive emphasis / active state.
 */
const config: Config = {
  content: [
    "./src/app/**/*.{ts,tsx}",
    "./src/components/**/*.{ts,tsx}",
    "./src/lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bluette: {
          DEFAULT: "#4400B3",
          700: "#4400B3",
          500: "#6E1AFF",
          400: "#8B5CFF",
          900: "#2B0073",
        },
        lime: {
          DEFAULT: "#B9FF69",
        },
        magenta: "#C300C3",
        cyan: "#00FFFF",
        ink: "#000000",
        paper: "#FFFFFF",
        grey: {
          text: "#595959",
          mid: "#DDDDDA",
          light: "#F4F4F2",
        },
      },
      fontFamily: {
        sans: ["var(--font-atkinson)", "Inter", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      borderRadius: {
        card: "4px",
      },
    },
  },
  plugins: [],
};

export default config;
