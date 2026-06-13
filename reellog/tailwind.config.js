/** @type {import('tailwindcss').Config} */
// Design tokens live here so colour/font usage stays consistent across the app.
module.exports = {
  content: ["./app/templates/**/*.html", "./app/static/js/**/*.js"],
  theme: {
    extend: {
      colors: {
        bg: "#0B0C0E",
        surface: "#15171B",
        "surface-2": "#1E2127",
        border: "#2A2E37",
        text: "#ECEDEE",
        "text-dim": "#9BA1AC",
        "text-mute": "#5C626D",
        accent: "#D9A441", // amber: stars, focus, single primary action
        like: "#E0567B", // rose: the "like" heart
      },
      fontFamily: {
        // Serif for editorial film titles/headings; Inter for body/UI.
        serif: ['"Fraunces"', "Georgia", "ui-serif", "serif"],
        sans: ['"Inter"', "system-ui", "-apple-system", "sans-serif"],
      },
      maxWidth: {
        content: "1180px",
      },
      transitionDuration: {
        175: "175ms",
      },
    },
  },
  plugins: [],
};
