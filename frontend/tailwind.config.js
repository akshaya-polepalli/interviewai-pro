/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: {
          DEFAULT: "#0B1220",
          elevated: "#121A2B",
          muted: "#1A2438",
        },
        ink: {
          DEFAULT: "#E8EEF9",
          muted: "#9AA8C7",
          subtle: "#6B7A99",
        },
        accent: {
          DEFAULT: "#2DD4BF",
          soft: "#14B8A6",
          strong: "#0F766E",
        },
        danger: "#F87171",
        warn: "#FBBF24",
      },
      fontFamily: {
        display: ['"Sora"', "system-ui", "sans-serif"],
        body: ['"IBM Plex Sans"', "system-ui", "sans-serif"],
        mono: ['"IBM Plex Mono"', "ui-monospace", "monospace"],
      },
      boxShadow: {
        glass: "0 8px 32px rgba(0, 0, 0, 0.35)",
      },
      backgroundImage: {
        "hero-grid":
          "radial-gradient(circle at 20% 20%, rgba(45, 212, 191, 0.12), transparent 40%), radial-gradient(circle at 80% 0%, rgba(96, 165, 250, 0.10), transparent 35%), linear-gradient(160deg, #070B14 0%, #0B1220 45%, #0E1A2F 100%)",
      },
      keyframes: {
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(12px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "200% 0" },
          "100%": { backgroundPosition: "-200% 0" },
        },
      },
      animation: {
        "fade-up": "fade-up 0.6s ease-out both",
        shimmer: "shimmer 2.4s linear infinite",
      },
    },
  },
  plugins: [],
};
