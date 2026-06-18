// JavaScript fuer Settings: Tabs, Favoriten-Suche und Profil-Backdrop-Auswahl.
import { api } from "./api.js";
import { openDialog, wireDialog } from "./modal-utils.js";

const tabsRoot = document.querySelector("[data-settings-tabs]");
if (tabsRoot) {
  const tabs = [...tabsRoot.querySelectorAll("[data-settings-tab]")];
  const panels = [...tabsRoot.querySelectorAll("[data-settings-panel]")];
  const initial = "profile";

  function showTab(name) {
    // Nur der aktive Settings-Bereich bleibt sichtbar.
    tabs.forEach((tab) => {
      const active = tab.dataset.settingsTab === name;
      tab.classList.toggle("is-active", active);
      tab.setAttribute("aria-selected", active ? "true" : "false");
    });
    panels.forEach((panel) => {
      panel.classList.toggle("hidden", panel.dataset.settingsPanel !== name);
    });
  }

  tabs.forEach((tab) => {
    tab.addEventListener("click", () => showTab(tab.dataset.settingsTab));
  });
  showTab(initial);
}

document.querySelectorAll("form").forEach((form) => {
  form.addEventListener("submit", () => {
    const button = form.querySelector('button[type="submit"]');
    if (!button) return;
    button.dataset.originalText = button.textContent;
    button.textContent = "Working...";
    button.disabled = true;
  });
});

const dialog = document.getElementById("settings-backdrop-dialog");
if (dialog) {
  wireDialog(dialog);

  const openBtn = document.querySelector("[data-settings-backdrop-open]");
  const removeBtn = document.querySelector("[data-settings-backdrop-remove]");
  const search = dialog.querySelector("[data-backdrop-search]");
  const results = dialog.querySelector("[data-backdrop-results]");
  const grid = dialog.querySelector("[data-backdrop-grid]");
  const saveBtn = dialog.querySelector("[data-backdrop-save]");
  const error = dialog.querySelector("[data-backdrop-error]");
  let selectedFilm = null;
  let selectedBackdrop = null;
  let timer = null;

  function setError(message = "") {
    error.textContent = message;
    error.classList.toggle("hidden", !message);
  }

  function resetPicker() {
    // Nach jedem Oeffnen startet die Backdrop-Auswahl sauber neu.
    selectedFilm = null;
    selectedBackdrop = null;
    results.innerHTML = "";
    grid.innerHTML = "";
    saveBtn.disabled = true;
    setError("");
  }

  function backdropUrl(path, size = "w780") {
    return `https://image.tmdb.org/t/p/${size}${path}`;
  }

  function renderFilms(items) {
    results.innerHTML = "";
    if (!items.length) {
      results.innerHTML = '<p class="text-sm text-text-mute">No films found.</p>';
      return;
    }
    items.forEach((film) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "flex w-full items-center gap-3 rounded-md border border-border p-2 text-left hover:border-accent";
      btn.innerHTML = `
        <img class="h-14 w-10 rounded object-cover bg-surface-2" alt="" src="${film.poster_path ? `https://image.tmdb.org/t/p/w92${film.poster_path}` : "/static/img/poster-fallback.svg"}">
        <span class="min-w-0">
          <span class="block truncate text-sm">${film.title}</span>
          <span class="text-xs text-text-mute">${film.year || ""}</span>
        </span>`;
      btn.addEventListener("click", () => loadBackdrops(film));
      results.append(btn);
    });
  }

  function renderBackdrops(backdrops) {
    grid.innerHTML = "";
    selectedBackdrop = null;
    saveBtn.disabled = true;
    if (!backdrops.length) {
      grid.innerHTML = '<p class="col-span-full text-sm text-text-mute">No backdrops available for this film.</p>';
      return;
    }
    backdrops.forEach((img) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "group relative overflow-hidden rounded-md ring-1 ring-border focus:outline-none focus:ring-2 focus:ring-accent";
      btn.innerHTML = `<img src="${backdropUrl(img.file_path)}" alt="" class="aspect-video w-full object-cover">`;
      btn.addEventListener("click", () => {
        selectedBackdrop = img.file_path;
        grid.querySelectorAll("button").forEach((b) => b.classList.remove("ring-2", "ring-accent"));
        btn.classList.add("ring-2", "ring-accent");
        saveBtn.disabled = false;
      });
      grid.append(btn);
    });
  }

  async function loadBackdrops(film) {
    selectedFilm = film;
    grid.innerHTML = '<p class="col-span-full text-sm text-text-mute">Loading backdrops...</p>';
    setError("");
    try {
      const data = await api.get(`/api/movies/${film.tmdb_id}/images`);
      renderBackdrops(data.backdrops || []);
    } catch (err) {
      grid.innerHTML = "";
      setError("Couldn't load images, try again.");
    }
  }

  async function searchFilms(query) {
    if (!query.trim()) {
      resetPicker();
      return;
    }
    try {
      const data = await api.get(`/api/search?q=${encodeURIComponent(query)}`);
      renderFilms(data.results || []);
    } catch (err) {
      setError(err.message);
    }
  }

  openBtn?.addEventListener("click", () => {
    resetPicker();
    search.value = "";
    openDialog(dialog, search);
  });
  search?.addEventListener("input", () => {
    clearTimeout(timer);
    timer = setTimeout(() => searchFilms(search.value), 250);
  });
  saveBtn?.addEventListener("click", async () => {
    if (!selectedFilm || !selectedBackdrop) return;
    try {
      await api.post("/api/profile/backdrop", {
        tmdb_id: selectedFilm.tmdb_id,
        backdrop_path: selectedBackdrop,
      });
      window.location.reload();
    } catch (err) {
      setError(err.message);
    }
  });
  removeBtn?.addEventListener("click", async () => {
    try {
      await api.del("/api/profile/backdrop");
      window.location.reload();
    } catch (err) {
      alert(err.message);
    }
  });
}

const favoritePicker = document.querySelector("[data-favorites-picker]");
if (favoritePicker) {
  const slots = [...favoritePicker.querySelectorAll("[data-favorite-slot]")];
  const search = favoritePicker.querySelector("[data-favorite-search]");
  const results = favoritePicker.querySelector("[data-favorite-results]");
  let timer = null;

  function escapeHtml(value = "") {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function posterUrl(path) {
    return path ? `https://image.tmdb.org/t/p/w185${path}` : "/static/img/poster-fallback.svg";
  }

  function selectedIds() {
    return new Set(
      slots
        .map((slot) => slot.querySelector("[data-favorite-input]").value)
        .filter(Boolean)
    );
  }

  function firstEmptySlot() {
    return slots.find((slot) => !slot.querySelector("[data-favorite-input]").value) || slots[slots.length - 1];
  }

  function clearSlot(slot) {
    slot.querySelector("[data-favorite-input]").value = "";
    slot.querySelector("[data-favorite-preview]").innerHTML =
      `<div class="flex h-full w-full items-center justify-center text-sm text-text-mute">${slots.indexOf(slot) + 1}</div>`;
    slot.querySelector("[data-favorite-remove]").classList.add("hidden");
  }

  function setSlot(slot, film) {
    slot.querySelector("[data-favorite-input]").value = film.tmdb_id;
    slot.querySelector("[data-favorite-preview]").innerHTML =
      `<img src="${posterUrl(film.poster_path)}" alt="${escapeHtml(film.title)} poster" loading="lazy" />`;
    slot.querySelector("[data-favorite-remove]").classList.remove("hidden");
  }

  function renderResults(films) {
    results.innerHTML = "";
    const chosen = selectedIds();
    const available = films.filter((film) => !chosen.has(String(film.tmdb_id)));
    if (!available.length) {
      results.classList.remove("hidden");
      results.innerHTML = '<p class="px-3 py-2 text-sm text-text-mute">No films found.</p>';
      return;
    }
    available.slice(0, 6).forEach((film) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "flex w-full items-center gap-3 px-3 py-2 text-left transition hover:bg-surface-2";
      button.innerHTML = `
        <img class="h-14 w-10 rounded object-cover bg-surface-2" alt="" src="${posterUrl(film.poster_path)}">
        <span class="min-w-0">
          <span class="block truncate text-sm">${escapeHtml(film.title)}</span>
          <span class="text-xs text-text-mute">${film.year || ""}</span>
        </span>`;
      button.addEventListener("click", () => {
        setSlot(firstEmptySlot(), film);
        results.classList.add("hidden");
        search.value = "";
      });
      results.append(button);
    });
    results.classList.remove("hidden");
  }

  async function searchFilms(query) {
    if (!query.trim()) {
      results.classList.add("hidden");
      results.innerHTML = "";
      return;
    }
    try {
      const data = await api.get(`/api/search?q=${encodeURIComponent(query)}`);
      renderResults(data.results || []);
    } catch (err) {
      results.classList.remove("hidden");
      results.innerHTML = `<p class="px-3 py-2 text-sm text-like">${escapeHtml(err.message)}</p>`;
    }
  }

  slots.forEach((slot) => {
    slot.querySelector("[data-favorite-remove]").addEventListener("click", () => clearSlot(slot));
  });

  search?.addEventListener("input", () => {
    clearTimeout(timer);
    timer = setTimeout(() => searchFilms(search.value), 250);
  });
}
