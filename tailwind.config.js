/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./shop/templates/**/*.html", "./shop/**/*.py"],
  theme: {
    extend: {
      colors: {
        surface: "#FFFFFF",
        accent: "#825641",
        accentSoft: "#F7A3B1",
        accentDark: "#570301",
        bg: "#EFE9E4",
        panel: "#FFFFFF",
        plum: "#713274",
        gold: "#FF9A00",
        warmGray: "#65635C"
      },
      fontFamily: {
        body: ["Lato", "sans-serif"],
        display: ["Agada", "Cormorant Garamond", "serif"]
      },
      boxShadow: {
        glow: "0 24px 70px rgba(130, 86, 65, 0.15)"
      }
    }
  },
  plugins: []
};
