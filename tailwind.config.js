/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/niamoto/publish/templates/**/*.html",
    "./src/niamoto/core/plugins/widgets/*.py",
  ],
  theme: {
    extend: {
      colors: {
        primary: '#1fb99d',
        'nav-bg': '#228b22',
      },
    },
  },
  plugins: [],
}
