/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./shop/templates/**/*.html", "./shop/**/*.py"],
  theme: {
    extend: {
      colors: {
        surface: "#f9f9f9",
        accent: "#ff4fb8",
        accentSoft: "#ffe1f3",
        accentDark: "#c82682",
        bg: "#070508",
        panel: "#141116"
      },
      fontFamily: {
        body: ["Manrope", "sans-serif"],
        display: ["Playfair Display", "serif"]
      },
      boxShadow: {
        glow: "0 24px 80px rgba(255, 79, 184, 0.16)"
      }
    }
  },
  plugins: []
};
