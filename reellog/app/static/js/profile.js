// Own-profile editing: remove a pinned favourite film. Loaded only on the
// current user's own profile (see profile.html scripts block).
import { api } from "./api.js";

document.querySelectorAll('[data-action="remove-favorite"]').forEach((btn) => {
  btn.addEventListener("click", async () => {
    btn.disabled = true;
    try {
      // The toggle endpoint removes it when it's already a favourite.
      await api.post("/api/favorites/toggle", {
        tmdb_id: Number(btn.dataset.tmdbId),
      });
      window.location.reload();
    } catch (err) {
      alert(err.message);
      btn.disabled = false;
    }
  });
});
