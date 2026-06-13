/** @type {import('tailwindcss').Config} */
// Design tokens live here so colour/font usage stays consistent across the app.
module.exports = {
  content: ["./app/templates/**/*.html", "./app/static/js/**/*.js"],
  theme: {
    extend: {
      colors: {
        bg: "#0D0E10",
        ink: "#ECEAE4",
        dim: "rgba(236,234,228,.55)",
        mute: "rgba(236,234,228,.34)",
        line: "rgba(236,234,228,.10)",
        gold: "#E5A94E",
        rose: "#F26A8D",
        surface: "#111317",
        "surface-2": "#17191E",
        border: "rgba(236,234,228,.10)",
        text: "#ECEAE4",
        "text-dim": "rgba(236,234,228,.55)",
        "text-mute": "rgba(236,234,228,.34)",
        accent: "#E5A94E",
        like: "#F26A8D",
      },
      fontFamily: {
        // Serif for editorial film titles/headings; Inter for body/UI.
        serif: ['"Fraunces"', "Georgia", "ui-serif", "serif"],
        sans: ['"Inter"', "system-ui", "-apple-system", "sans-serif"],
      },
      maxWidth: {
        content: "1180px",
        shell: "1040px",
      },
      transitionDuration: {
        175: "175ms",
      },
    },
  },
  plugins: [],
};
