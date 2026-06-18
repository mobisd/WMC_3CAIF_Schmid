// Kleine Helfer fuer Dialoge, damit Modal-Code nicht ueberall doppelt steht.
export function wireDialog(dialog) {
  if (!dialog) return;

  const focusable = () =>
    [...dialog.querySelectorAll("button, [href], input, select, textarea, [tabindex]:not([tabindex='-1'])")]
      .filter((el) => !el.disabled && el.offsetParent !== null);

  dialog.addEventListener("click", (e) => {
    if (e.target === dialog) dialog.close();
  });
  dialog.querySelectorAll("[data-modal-close]").forEach((btn) => {
    btn.addEventListener("click", () => dialog.close());
  });
  dialog.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      dialog.close();
      return;
    }
    if (e.key !== "Tab") return;
    const items = focusable();
    if (!items.length) return;
    const first = items[0];
    const last = items[items.length - 1];
    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault();
      first.focus();
    }
  });
}

export function openDialog(dialog, initialFocus) {
  // Nach dem Oeffnen wird direkt ein sinnvoller Button/Input fokussiert.
  dialog.showModal();
  setTimeout(() => (initialFocus || dialog.querySelector("button, input"))?.focus(), 0);
}
