/** @type {import('tailwindcss').Config} */
module.exports = {
  // Scan all template HTML and external JS files for class names so the JIT
  // compiler emits only what's actually used.
  content: [
    './app/templates/**/*.html',
    './app/static/js/**/*.js',
  ],
  theme: {
    extend: {
      colors: {
        // Brand orange palette — matches the FuelTrack logo / nav icon.
        fuel: {
          50:  '#fff7ed',
          100: '#ffedd5',
          400: '#fb923c',
          500: '#f97316',
          600: '#ea580c',
          700: '#c2410c',
        },
      },
    },
  },
  plugins: [],
}
