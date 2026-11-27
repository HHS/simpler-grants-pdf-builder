// "Is callout box?" and "Is note?" are a single choice: checking one unchecks
// the other. The server also rejects a form that sends both (#1437).
document.addEventListener("DOMContentLoaded", () => {
  const box = document.getElementById("callout_box");
  const note = document.getElementById("callout_style");
  if (!box || !note) return;

  const keepOne = (checked, other) => {
    if (checked.checked && other.checked) {
      other.checked = false;
      // Let other listeners, such as the callout word warning, update.
      other.dispatchEvent(new Event("change"));
    }
  };
  box.addEventListener("change", () => keepOne(box, note));
  note.addEventListener("change", () => keepOne(note, box));
});
