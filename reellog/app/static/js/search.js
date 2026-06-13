// Debounced live-search dropdown for the nav bar.
//
// Security note: results come from TMDB (external). We build the dropdown with
// DOM APIs and textContent — never innerHTML with raw data — so titles can't
// inject markup.
import { api } from "./api.js";

const form = document.querySelector("[data-live-search]");
if (form) {
  const input = form.querySelector("[data-search-input]");
  const panel = form.querySelector("[data-search-results]");
  let timer = null;
  let activeIndex = -1;

  function hide() {
    panel.classList.add("hidden");
    panel.replaceChildren();
    activeIndex = -1;
  }

  function render(results) {
    panel.replaceChildren();
    if (!results.length) {
      hide();
      return;
    }
    results.forEach((film) => {
      const a = document.createElement("a");
      a.href = `/film/${film.tmdb_id}`;
      a.className =
        "flex items-center gap-3 px-3 py-2 text-sm hover:bg-surface-2 focus:bg-surface-2 focus:outline-none";
      a.setAttribute("role", "option");

      const img = document.createElement("img");
      img.className = "h-12 w-8 shrink-0 rounded object-cover bg-surface-2";
      img.alt = "";
      img.loading = "lazy";
      img.src = film.poster_path
        ? `https://image.tmdb.org/t/p/w92${film.poster_path}`
        : "/static/img/poster-fallback.svg";

      const span = document.createElement("span");
      span.className = "min-w-0 truncate text-text";
      span.textContent = film.year ? `${film.title} (${film.year})` : film.title;

      a.append(img, span);
      panel.appendChild(a);
    });
    panel.classList.remove("hidden");
  }

  async function run(q) {
    try {
      const data = await api.get(`/api/search?q=${encodeURIComponent(q)}`);
      render(data.results || []);
    } catch {
      hide();
    }
  }

  input.addEventListener("input", () => {
    const q = input.value.trim();
    window.clearTimeout(timer);
    if (q.length < 2) {
      hide();
      return;
    }
    // Debounce so we don't fire a request on every keystroke.
    timer = window.setTimeout(() => run(q), 250);
  });

  // Keyboard navigation through the dropdown.
  input.addEventListener("keydown", (e) => {
    const items = [...panel.querySelectorAll('[role="option"]')];
    if (!items.length) return;
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      activeIndex += e.key === "ArrowDown" ? 1 : -1;
      if (activeIndex < 0) activeIndex = items.length - 1;
      if (activeIndex >= items.length) activeIndex = 0;
      items[activeIndex].focus();
    } else if (e.key === "Escape") {
      hide();
    }
  });

  document.addEventListener("click", (e) => {
    if (!form.contains(e.target)) hide();
  });
}
