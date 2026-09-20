/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        surface: {
          DEFAULT: "#0b1220",
          panel: "#111a2c",
          border: "#1f2b42",
        },
        accent: {
          DEFAULT: "#3b82f6",
          soft: "#1d4ed8",
        },
      },
    },
  },
  plugins: [],
};
