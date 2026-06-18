// Live-Suche in der Navigation: sucht Accounts und Filme per API.
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

  function render(data) {
    // Ergebnisse werden komplett neu aufgebaut, damit alte Treffer verschwinden.
    const results = data.results || [];
    const users = data.users || [];
    panel.replaceChildren();
    if (!results.length && !users.length) {
      hide();
      return;
    }
    if (users.length) {
      const label = document.createElement("div");
      label.className = "px-3 pb-1 pt-2 text-[10px] uppercase tracking-[0.18em] text-text-mute";
      label.textContent = "Accounts";
      panel.appendChild(label);
    }
    users.forEach((user) => {
      const a = document.createElement("a");
      a.href = `/${user.username}`;
      a.className =
        "flex items-center gap-3 px-3 py-2 text-sm transition hover:bg-surface-2 focus:bg-surface-2 focus:outline-none";
      a.setAttribute("role", "option");
      const avatar = document.createElement(user.avatar_url ? "img" : "span");
      avatar.className = "flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-surface-2 object-cover text-xs font-semibold text-text-dim";
      if (user.avatar_url) {
        avatar.src = user.avatar_url;
        avatar.alt = "";
      } else {
        avatar.textContent = (user.name || user.username).slice(0, 1).toUpperCase();
      }
      const span = document.createElement("span");
      span.className = "min-w-0";
      span.innerHTML = `<span class="block truncate text-text"></span><span class="block truncate text-xs text-text-mute"></span>`;
      span.children[0].textContent = user.name;
      span.children[1].textContent = `@${user.username}`;
      a.append(avatar, span);
      panel.appendChild(a);
    });
    if (results.length) {
      const label = document.createElement("div");
      label.className = "border-t border-border px-3 pb-1 pt-2 text-[10px] uppercase tracking-[0.18em] text-text-mute";
      label.textContent = "Films";
      panel.appendChild(label);
    }
    results.forEach((film) => {
      const a = document.createElement("a");
      a.href = `/film/${film.tmdb_id}`;
      a.className =
        "flex items-center gap-3 px-3 py-2 text-sm transition hover:bg-surface-2 focus:bg-surface-2 focus:outline-none";
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
      render(data);
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
    timer = window.setTimeout(() => run(q), 250);
  });

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
