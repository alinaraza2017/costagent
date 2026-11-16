/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: "#f4f6fb",
        ink: "#1e293b",
        mist: "#64748b",
        line: "#e4e9f5",
        primary: {
          50: "#eef3ff",
          100: "#e0e9ff",
          500: "#7c97f6",
          600: "#5f7ef0",
          700: "#4766d6",
        },
        lavender: {
          50: "#f6f3ff",
          100: "#ece6ff",
          400: "#c4b5fd",
        },
        mint: {
          50: "#f0fdf8",
          100: "#d9f7ee",
          500: "#5ecfb8",
          600: "#3cb89f",
        },
        coral: {
          50: "#fff5f5",
          100: "#fde8e8",
          500: "#e08b8b",
        },
      },
      boxShadow: {
        card: "0 10px 30px rgba(90, 110, 160, 0.08)",
      },
      fontFamily: {
        sans: ['"Segoe UI"', "Helvetica Neue", "Arial", "sans-serif"],
      },
    },
  },
  plugins: [],
};
