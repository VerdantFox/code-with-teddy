module.exports = {
  content: [
    "./app/web/html/templates/**/*.html",
    "./app/web/html/static/**/*.js",
    "./app/web/html/**/*.py",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Roboto", "sans-serif"],
      },
    },
  },
  plugins: [require("@tailwindcss/forms")],
}
