import type { Config } from "tailwindcss";

// Tokens come from DESIGN.md (THOR / Hemeria): sharp corners, no shadows, one action colour.
const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    borderRadius: { none: "0", DEFAULT: "0" },
    boxShadow: { none: "none", DEFAULT: "none" },
    extend: {
      colors: {
        deep: "var(--deep)", sky: "var(--sky)", blue: "var(--blue)", red: "var(--red)",
        mist: "var(--mist)", paper: "var(--paper)", hover: "var(--hover)", muted: "var(--muted)",
        veil: "var(--veil)", line: "var(--line)", ink: "var(--ink)", dim: "var(--dim)", mute: "var(--mute)",
        ok: "var(--ok)", warn: "var(--warn)", danger: "var(--danger)",
        "ok-bg": "var(--ok-bg)", "warn-bg": "var(--warn-bg)", "danger-bg": "var(--danger-bg)",
      },
      fontFamily: {
        sans: ["IBM Plex Sans", "system-ui", "sans-serif"],
        mono: ["IBM Plex Mono", "ui-monospace", "monospace"],
      },
      fontSize: { body: ["13px", "1.45"], label: ["11px", "1.2"] },
    },
  },
  plugins: [],
};

export default config;
