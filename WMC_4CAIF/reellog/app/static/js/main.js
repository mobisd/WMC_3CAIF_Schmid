import "./search.js"; // wires up the nav live search on every page.
import { openDialog, wireDialog } from "./modal-utils.js";

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

function initAvatarDialog() {
  const dialog = document.getElementById("avatar-dialog");
  const openButton = document.querySelector("[data-avatar-open]");
  if (!dialog || !openButton) return;

  wireDialog(dialog);
  openButton.addEventListener("click", () => openDialog(dialog));
}

initFlashes();
initMenu();
initAvatarDialog();
