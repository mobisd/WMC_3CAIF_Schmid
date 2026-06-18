import { api } from "./api.js";
import { openDialog, wireDialog } from "./modal-utils.js";

const panel = document.getElementById("action-panel");
if (panel) {
  const tmdbId = Number(panel.dataset.tmdbId);
  const today = panel.dataset.today;

  function makeStarWidget(container, { onSet, allowClear = false }) {
    const stars = [...container.querySelectorAll(".star")];
    let value = Number(container.dataset.value || 0);

    function valueFromEvent(starIndex, e) {
      const rect = stars[starIndex].getBoundingClientRect();
      // Linke Sternhaelfte = halber Stern, rechte Haelfte = ganzer Stern.
      return starIndex * 2 + (e.clientX - rect.left < rect.width / 2 ? 1 : 2);
    }

    function paint(v) {
      stars.forEach((star, i) => {
        const full = (i + 1) * 2;
        const half = full - 1;
        star.textContent = v >= full ? "★" : v === half ? "◐" : "★";
        star.style.color = v >= half ? "var(--accent)" : "";
      });
    }

    function setValue(v) {
      value = v;
      container.dataset.value = String(v);
      container.setAttribute("aria-valuenow", String(v / 2));
      paint(v);
    }

    stars.forEach((star, i) => {
      star.addEventListener("mousemove", (e) => paint(valueFromEvent(i, e)));
      star.addEventListener("click", (e) => {
        const next = valueFromEvent(i, e);
        const v = allowClear && next === value ? 0 : next;
        setValue(v);
        onSet(v);
      });
    });
    container.addEventListener("mouseleave", () => paint(value));
    container.addEventListener("keydown", (e) => {
      if (e.key === "ArrowRight" || e.key === "ArrowUp") {
        e.preventDefault();
        const v = Math.min(10, value + 1);
        setValue(v);
        onSet(v);
      } else if (e.key === "ArrowLeft" || e.key === "ArrowDown") {
        e.preventDefault();
        const v = Math.max(0, value - 1);
        setValue(v);
        onSet(v);
      }
    });
    paint(value);
    return { setValue, getValue: () => value };
  }

  const wlBtn = panel.querySelector('[data-action="toggle-watchlist"]');
  const wlLabel = panel.querySelector("[data-watchlist-label]");
  wlBtn?.addEventListener("click", async () => {
    wlBtn.disabled = true;
    try {
      const data = await api.post("/api/watchlist/toggle", { tmdb_id: tmdbId });
      wlLabel.textContent = data.in_watchlist ? "In your watchlist" : "Add to watchlist";
      wlBtn.setAttribute("aria-pressed", data.in_watchlist ? "true" : "false");
    } catch (err) {
      alert(err.message);
    } finally {
      wlBtn.disabled = false;
    }
  });

  const panelStars = panel.querySelector("[data-star-widget]");
  const ratingText = panel.querySelector("[data-rating-text]");
  if (panelStars) {
    panelStars.dataset.value = panel.dataset.rating || 0;
    makeStarWidget(panelStars, {
      allowClear: true,
      onSet: async (v) => {
        try {
          await api.post("/api/logs", {
            tmdb_id: tmdbId,
            rating: v === 0 ? null : v,
            watched_on: today,
          });
          ratingText.textContent = v === 0 ? "Rating cleared" : `${v / 2} stars`;
          window.location.reload();
        } catch (err) {
          alert(err.message);
        }
      },
    });
  }

  const logDialog = document.getElementById("log-dialog");
  const form = document.getElementById("log-form");
  if (logDialog && form) {
    wireDialog(logDialog);
    const dialogStars = logDialog.querySelector("[data-dialog-stars]");
    const titleEl = logDialog.querySelector("[data-dialog-title]");
    const errorEl = logDialog.querySelector("[data-dialog-error]");
    let editingId = null;
    const starWidget = makeStarWidget(dialogStars, { allowClear: true, onSet: () => {} });

    logDialog.querySelector("[data-dialog-clear]")?.addEventListener("click", () => starWidget.setValue(0));

    function openLog(log, forceRewatch = false) {
      errorEl.classList.add("hidden");
      form.reset();
      // Wenn ein Log uebergeben wird, wird bearbeitet, sonst neu erstellt.
      if (log && !forceRewatch) {
        editingId = log.id;
        titleEl.textContent = "Edit entry";
        form.elements.log_id.value = log.id;
        form.elements.watched_on.value = log.watched_on || "";
        form.elements.review.value = log.review || "";
        form.elements.liked.checked = !!log.liked;
        form.elements.is_rewatch.checked = !!log.is_rewatch;
        form.elements.contains_spoilers.checked = !!log.contains_spoilers;
        starWidget.setValue(log.rating || 0);
      } else {
        editingId = null;
        titleEl.textContent = forceRewatch ? "Log again" : "Log this film";
        form.elements.watched_on.value = today;
        form.elements.is_rewatch.checked = forceRewatch;
        starWidget.setValue(0);
      }
      openDialog(logDialog, form.elements.watched_on);
    }

    panel.querySelector('[data-action="open-log"]')?.addEventListener("click", () => {
      openLog(panel.dataset.currentLog ? JSON.parse(panel.dataset.currentLog) : null);
    });
    panel.querySelector('[data-action="log-again"]')?.addEventListener("click", () => openLog(null, true));
    document.querySelectorAll('[data-action="edit-log"]').forEach((btn) => {
      btn.addEventListener("click", () => openLog(JSON.parse(btn.dataset.log)));
    });
    document.querySelectorAll('[data-action="delete-log"]').forEach((btn) => {
      btn.addEventListener("click", () => window.openDeleteDialog(btn.dataset.logId));
    });
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const rating = starWidget.getValue();
      const payload = {
        tmdb_id: tmdbId,
        watched_on: form.elements.watched_on.value || null,
        rating: rating === 0 ? null : rating,
        review: form.elements.review.value,
        liked: form.elements.liked.checked,
        is_rewatch: form.elements.is_rewatch.checked,
        contains_spoilers: form.elements.contains_spoilers.checked,
      };
      try {
        if (editingId) await api.patch(`/api/logs/${editingId}`, payload);
        else await api.post("/api/logs", payload);
        window.location.reload();
      } catch (err) {
        errorEl.textContent = err.message;
        errorEl.classList.remove("hidden");
      }
    });
  }

  const imageDialog = document.getElementById("film-image-dialog");
  if (imageDialog) {
    wireDialog(imageDialog);
    const title = imageDialog.querySelector("[data-image-title]");
    const note = imageDialog.querySelector("[data-image-note]");
    const grid = imageDialog.querySelector("[data-film-image-grid]");
    const error = imageDialog.querySelector("[data-film-image-error]");
    const saveBtn = imageDialog.querySelector("[data-image-save]");
    const resetBtn = imageDialog.querySelector("[data-image-reset]");
    const profileWrap = imageDialog.querySelector("[data-profile-backdrop-wrap]");
    const useProfile = imageDialog.querySelector("[data-use-profile-backdrop]");
    let mode = "poster";
    let selectedPath = null;
    let imagesPayload = null;

    function setError(message = "") {
      error.textContent = message;
      error.classList.toggle("hidden", !message);
    }
    function url(path, kind) {
      return `https://image.tmdb.org/t/p/${kind === "poster" ? "w342" : "w780"}${path}`;
    }
    function renderGrid() {
      grid.innerHTML = "";
      selectedPath = null;
      saveBtn.disabled = true;
      // Je nach Modus werden Poster oder Backdrops in dasselbe Modal geladen.
      const items = mode === "poster" ? imagesPayload.posters : imagesPayload.backdrops;
      const current = mode === "poster" ? panel.dataset.userPosterPath : panel.dataset.userBackdropPath;
      const fallback = mode === "poster" ? panel.dataset.defaultPosterPath : panel.dataset.defaultBackdropPath;
      if (!items.length) {
        grid.innerHTML = '<p class="col-span-full text-sm text-text-mute">No images available for this film.</p>';
        return;
      }
      items.forEach((img) => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "group relative overflow-hidden rounded-md ring-1 ring-border focus:outline-none focus:ring-2 focus:ring-accent";
        const badge = img.file_path === current ? "Yours" : img.file_path === fallback ? "Default" : "";
        btn.innerHTML = `
          <img src="${url(img.file_path, mode)}" alt="" class="${mode === "poster" ? "aspect-[2/3]" : "aspect-video"} w-full object-cover">
          ${badge ? `<span class="absolute left-2 top-2 rounded bg-bg/85 px-2 py-1 text-[10px] uppercase tracking-wider text-text">${badge}</span>` : ""}
        `;
        btn.addEventListener("click", () => {
          selectedPath = img.file_path;
          grid.querySelectorAll("button").forEach((b) => b.classList.remove("ring-2", "ring-accent"));
          btn.classList.add("ring-2", "ring-accent");
          saveBtn.disabled = false;
        });
        grid.append(btn);
      });
    }
    async function openImagePicker(nextMode) {
      mode = nextMode;
      title.textContent = mode === "poster" ? "Change poster" : "Change backdrop";
      note.textContent = "Choose from TMDB images for this film.";
      profileWrap.classList.toggle("hidden", mode !== "backdrop");
      profileWrap.classList.toggle("flex", mode === "backdrop");
      useProfile.checked = false;
      grid.innerHTML = '<p class="col-span-full text-sm text-text-mute">Loading images...</p>';
      setError("");
      openDialog(imageDialog);
      try {
        imagesPayload = await api.get(`/api/movies/${tmdbId}/images`);
        renderGrid();
      } catch (err) {
        grid.innerHTML = "";
        setError("Couldn't load images, try again.");
      }
    }
    panel.querySelectorAll("[data-image-picker]").forEach((btn) => {
      btn.addEventListener("click", () => openImagePicker(btn.dataset.imagePicker));
    });
    saveBtn.addEventListener("click", async () => {
      if (!selectedPath) return;
      try {
        // Speichern geht ans Backend, damit dort nochmal validiert wird.
        await api.patch(`/api/film-images/${tmdbId}`, {
          field: mode,
          path: selectedPath,
          use_as_profile_backdrop: mode === "backdrop" && useProfile.checked,
        });
        window.location.reload();
      } catch (err) {
        setError(err.message);
      }
    });
    resetBtn.addEventListener("click", async () => {
      try {
        await api.patch(`/api/film-images/${tmdbId}`, { field: mode, path: null });
        window.location.reload();
      } catch (err) {
        setError(err.message);
      }
    });
  }

  const deleteDialog = document.getElementById("delete-log-dialog");
  if (deleteDialog) {
    wireDialog(deleteDialog);
    const confirmBtn = deleteDialog.querySelector("[data-delete-confirm]");
    const error = deleteDialog.querySelector("[data-delete-error]");
    let deleteId = null;

    window.openDeleteDialog = (id) => {
      // Die ID wird gemerkt, geloescht wird erst nach der Bestaetigung.
      deleteId = id;
      error.classList.add("hidden");
      openDialog(deleteDialog, confirmBtn);
    };

    confirmBtn.addEventListener("click", async () => {
      if (!deleteId) return;
      confirmBtn.disabled = true;
      try {
        await api.del(`/api/logs/${deleteId}`);
        window.location.reload();
      } catch (err) {
        error.textContent = err.message;
        error.classList.remove("hidden");
      } finally {
        confirmBtn.disabled = false;
      }
    });
  }
}
