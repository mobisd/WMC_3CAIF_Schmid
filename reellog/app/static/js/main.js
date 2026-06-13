// Site-wide enhancements: flash auto-dismiss, profile menu outside-click close.
import "./search.js"; // wires up the nav live search on every page.

// --- Flash messages: fade out after a few seconds --------------------------
function initFlashes() {
  const container = document.getElementById("flash-container");
  if (!container) return;
  container.querySelectorAll(".flash").forEach((el) => {
    window.setTimeout(() => {
      el.style.transition = "opacity 300ms";
      el.style.opacity = "0";
      window.setTimeout(() => el.remove(), 320);
    }, 4500);
  });
}

// --- Close the <details> profile menu when clicking outside it -------------
function initMenu() {
  const menu = document.querySelector("[data-menu]");
  if (!menu) return;
  document.addEventListener("click", (e) => {
    if (menu.open && !menu.contains(e.target)) menu.open = false;
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") menu.open = false;
  });
}

initFlashes();
initMenu();
