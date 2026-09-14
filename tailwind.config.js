/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        "surface-bright": "#333947",
        "secondary-fixed": "#c4e7ff",
        "surface": "#0d131f",
        "inverse-on-surface": "#2b303e",
        "secondary-container": "#00a6e0",
        "on-tertiary-fixed-variant": "#004b73",
        "on-primary-container": "#003751",
        "surface-container-low": "#161c28",
        "on-tertiary-container": "#003655",
        "surface-container-lowest": "#080e1a",
        "surface-tint": "#89ceff",
        "tertiary": "#93ccff",
        "on-secondary": "#00354a",
        "primary-fixed": "#c9e6ff",
        "error-container": "#93000a",
        "on-primary-fixed-variant": "#004c6e",
        "outline-variant": "#3e4850",
        "on-primary": "#00344d",
        "primary-fixed-dim": "#89ceff",
        "surface-container-high": "#242a37",
        "on-tertiary": "#003351",
        "tertiary-fixed": "#cce5ff",
        "primary": "#89ceff",
        "on-surface": "#dde2f4",
        "on-secondary-fixed": "#001e2c",
        "surface-container": "#1a202c",
        "on-error-container": "#ffdad6",
        "on-secondary-fixed-variant": "#004c69",
        "on-tertiary-fixed": "#001d31",
        "tertiary-container": "#40a2e7",
        "surface-variant": "#2f3542",
        "on-primary-fixed": "#001e2f",
        "secondary": "#7bd0ff",
        "secondary-fixed-dim": "#7bd0ff",
        "primary-container": "#0ea5e9",
        "outline": "#88929b",
        "on-surface-variant": "#bec8d2",
        "on-background": "#dde2f4",
        "error": "#ffb4ab",
        "tertiary-fixed-dim": "#93ccff",
        "inverse-primary": "#006591",
        "on-error": "#690005",
        "surface-dim": "#0d131f",
        "on-secondary-container": "#00374d",
        "background": "#0d131f",
        "surface-container-highest": "#2f3542",
        "inverse-surface": "#dde2f4"
      },
      borderRadius: {
        DEFAULT: "0.25rem",
        lg: "0.5rem",
        xl: "0.75rem",
        full: "9999px"
      },
      spacing: {
        "gutter-sm": "0.5rem",
        "space-sm": "0.5rem",
        "space-md": "0.75rem",
        gutter: "0.75rem",
        "space-xs": "0.25rem",
        margin: "1rem",
        "space-xl": "1.5rem",
        "space-lg": "1rem"
      },
      fontFamily: {
        "headline-md": ["Inter", "sans-serif"],
        "body-md": ["Inter", "sans-serif"],
        "body-sm": ["Inter", "sans-serif"],
        "label-xs": ["JetBrains Mono", "monospace"],
        "headline-lg": ["Inter", "sans-serif"],
        "headline-xl": ["Inter", "sans-serif"],
        "label-sm": ["JetBrains Mono", "monospace"],
        "label-md": ["JetBrains Mono", "monospace"],
        "body-lg": ["Inter", "sans-serif"]
      },
      fontSize: {
        "headline-md": ["18px", { lineHeight: "24px", letterSpacing: "-0.01em", fontWeight: "600" }],
        "body-md": ["13px", { lineHeight: "18px", letterSpacing: "0em", fontWeight: "400" }],
        "body-sm": ["12px", { lineHeight: "16px", letterSpacing: "0.01em", fontWeight: "400" }],
        "label-xs": ["10px", { lineHeight: "12px", letterSpacing: "0.08em", fontWeight: "600" }],
        "headline-lg": ["24px", { lineHeight: "30px", letterSpacing: "-0.015em", fontWeight: "600" }],
        "headline-xl": ["32px", { lineHeight: "38px", letterSpacing: "-0.02em", fontWeight: "600" }],
        "headline-xl-mobile": ["24px", { lineHeight: "30px", letterSpacing: "-0.01em", fontWeight: "600" }],
        "label-sm": ["11px", { lineHeight: "14px", letterSpacing: "0.06em", fontWeight: "500" }],
        "label-md": ["12px", { lineHeight: "16px", letterSpacing: "0.04em", fontWeight: "500" }],
        "body-lg": ["15px", { lineHeight: "22px", letterSpacing: "0em", fontWeight: "400" }]
      },
      keyframes: {
        "pulse-slow": {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.6" },
        }
      }
    }
  },
  plugins: [],
}
