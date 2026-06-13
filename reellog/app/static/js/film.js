// Film page interactivity: watchlist toggle, quick-rate widget, and the
// log/review dialog (create + edit + delete). All mutations go through api.js,
// which attaches the CSRF token.
import { api } from "./api.js";

const panel = document.getElementById("action-panel");
if (panel) {
  const tmdbId = Number(panel.dataset.tmdbId);
  const today = panel.dataset.today;

  // --- shared star-widget factory ------------------------------------------
  // Operates on a container of 5 .star spans. value is in half-star units
  // (1..10) or 0 for unrated. `onSet(value)` fires on click. Hovering previews.
  function makeStarWidget(container, { onSet, allowClear = false }) {
    const stars = [...container.querySelectorAll(".star")];
    let value = Number(container.dataset.value || 0);

    // Map a pointer position within a star to a half (1) or full (2) value.
    function valueFromEvent(starIndex, e) {
      const star = stars[starIndex];
      const rect = star.getBoundingClientRect();
      const isLeftHalf = e.clientX - rect.left < rect.width / 2;
      return starIndex * 2 + (isLeftHalf ? 1 : 2);
    }

    function paint(v) {
      stars.forEach((star, i) => {
        const full = (i + 1) * 2;
        const half = full - 1;
        if (v >= full) {
          star.textContent = "★";
          star.style.color = "var(--accent)";
        } else if (v === half) {
          star.textContent = "⯨"; // left-half star glyph
          star.style.color = "var(--accent)";
        } else {
          star.textContent = "★";
          star.style.color = ""; // inherits text-mute
        }
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
        const v = valueFromEvent(i, e);
        // Click the current value again to clear (when allowed).
        if (allowClear && v === value) {
          setValue(0);
          onSet(0);
        } else {
          setValue(v);
          onSet(v);
        }
      });
    });

    container.addEventListener("mouseleave", () => paint(value));

    // Keyboard: arrows adjust by a half-star.
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

  // --- watchlist toggle ----------------------------------------------------
  const wlBtn = panel.querySelector('[data-action="toggle-watchlist"]');
  const wlLabel = panel.querySelector("[data-watchlist-label]");
  wlBtn?.addEventListener("click", async () => {
    wlBtn.disabled = true;
    try {
      const data = await api.post("/api/watchlist/toggle", { tmdb_id: tmdbId });
      const inList = data.in_watchlist;
      wlLabel.textContent = inList ? "In your watchlist ✓" : "Add to watchlist";
      wlBtn.setAttribute("aria-pressed", inList ? "true" : "false");
    } catch (err) {
      alert(err.message);
    } finally {
      wlBtn.disabled = false;
    }
  });

  // --- favourite toggle ----------------------------------------------------
  const favBtn = panel.querySelector('[data-action="toggle-favorite"]');
  const favLabel = panel.querySelector("[data-favorite-label]");
  favBtn?.addEventListener("click", async () => {
    favBtn.disabled = true;
    try {
      const data = await api.post("/api/favorites/toggle", { tmdb_id: tmdbId });
      const fav = data.is_favorite;
      favLabel.textContent = fav ? "★ In your favourites" : "☆ Add to favourites";
      favBtn.setAttribute("aria-pressed", fav ? "true" : "false");
    } catch (err) {
      alert(err.message);
    } finally {
      favBtn.disabled = false;
    }
  });

  // --- set profile backdrop from this film ---------------------------------
  const backdropBtn = panel.querySelector('[data-action="set-backdrop"]');
  backdropBtn?.addEventListener("click", async () => {
    backdropBtn.disabled = true;
    const original = backdropBtn.textContent;
    try {
      await api.post("/api/profile/backdrop", { tmdb_id: tmdbId });
      backdropBtn.textContent = "Profile backdrop updated ✓";
    } catch (err) {
      alert(err.message);
      backdropBtn.textContent = original;
    } finally {
      backdropBtn.disabled = false;
    }
  });

  // --- quick-rate widget (panel) -------------------------------------------
  const panelStars = panel.querySelector("[data-star-widget]");
  const ratingText = panel.querySelector("[data-rating-text]");
  if (panelStars) {
    panelStars.dataset.value = panel.dataset.rating || 0;
    makeStarWidget(panelStars, {
      allowClear: false,
      onSet: async (v) => {
        if (v === 0) return;
        try {
          await api.post("/api/logs", {
            tmdb_id: tmdbId,
            rating: v,
            watched_on: today, // quick-rate also marks it watched today
          });
          ratingText.textContent = `${v / 2} stars · logged`;
          // Reload so the entries list + stats reflect the new diary entry.
          window.location.reload();
        } catch (err) {
          alert(err.message);
        }
      },
    });
  }

  // --- log dialog ----------------------------------------------------------
  const dialog = document.getElementById("log-dialog");
  const form = document.getElementById("log-form");
  if (dialog && form) {
    const dialogStars = dialog.querySelector("[data-dialog-stars]");
    const titleEl = dialog.querySelector("[data-dialog-title]");
    const errorEl = dialog.querySelector("[data-dialog-error]");
    let editingId = null;

    const starWidget = makeStarWidget(dialogStars, {
      allowClear: true,
      onSet: () => {}, // dialog defers saving until "Save entry"
    });

    dialog.querySelector("[data-dialog-clear]")?.addEventListener("click", () =>
      starWidget.setValue(0)
    );

    function openDialog(log) {
      errorEl.classList.add("hidden");
      form.reset();
      if (log) {
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
        titleEl.textContent = "Log this film";
        form.elements.watched_on.value = today;
        starWidget.setValue(0);
      }
      dialog.showModal();
    }

    panel.querySelector('[data-action="open-log"]')?.addEventListener(
      "click",
      () => openDialog(null)
    );

    // Edit / delete buttons live in the entries list (outside the panel).
    document.querySelectorAll('[data-action="edit-log"]').forEach((btn) => {
      btn.addEventListener("click", () => openDialog(JSON.parse(btn.dataset.log)));
    });
    document.querySelectorAll('[data-action="delete-log"]').forEach((btn) => {
      btn.addEventListener("click", async () => {
        if (!confirm("Delete this diary entry?")) return;
        try {
          await api.del(`/api/logs/${btn.dataset.logId}`);
          window.location.reload();
        } catch (err) {
          alert(err.message);
        }
      });
    });

    dialog
      .querySelector("[data-dialog-cancel]")
      ?.addEventListener("click", () => dialog.close());

    form.addEventListener("submit", async (e) => {
      // The <form method="dialog"> would close it; we intercept to call the API.
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
        if (editingId) {
          await api.patch(`/api/logs/${editingId}`, payload);
        } else {
          await api.post("/api/logs", payload);
        }
        dialog.close();
        window.location.reload();
      } catch (err) {
        errorEl.textContent = err.message;
        errorEl.classList.remove("hidden");
      }
    });
  }
}
