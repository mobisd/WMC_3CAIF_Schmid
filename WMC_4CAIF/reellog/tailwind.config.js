/** @type {import('tailwindcss').Config} */
// Design-Tokens: Farben, Fonts und Breiten bleiben dadurch ueberall gleich.
module.exports = {
  content: ["./app/templates/**/*.html", "./app/static/js/**/*.js"],
  theme: {
    extend: {
      colors: {
        bg: "#111820",
        surface: "#18212A",
        "surface-2": "#202A34",
        border: "#2F3C49",
        line: "rgba(218,228,238,.12)",
        text: "#F1F5F8",
        "text-dim": "#AFBBC7",
        "text-mute": "#758391",
        mute: "#758391",
        accent: "#D9A441", // amber: stars, focus, single primary action
        link: "#7DB4D8", // cool secondary accent for navigation and text links
        like: "#E0567B", // rose: the "like" heart
      },
      fontFamily: {
        sans: [
          "-apple-system",
          "BlinkMacSystemFont",
          '"SF Pro Display"',
          '"SF Pro Text"',
          '"Segoe UI"',
          "Roboto",
          "Arial",
          "sans-serif",
        ],
        serif: ["Georgia", "ui-serif", "serif"],
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
