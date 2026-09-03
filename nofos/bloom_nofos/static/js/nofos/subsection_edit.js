document.addEventListener("DOMContentLoaded", () => {
  const textEl = document.getElementById("subsection-html_id");
  const button = document.getElementById("subsection-html_id--button");
  if (!textEl || !button) return; // nothing to do

  button.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(textEl.textContent || "");
      button.textContent = "Copied!";
      setTimeout(() => (button.textContent = "Copy"), 1000);
    } catch (err) {
      console.error("Copy failed:", err);
    }
  });
});

// Keep this independent of the heading-copy button: unnamed subsections have
// no copy button, but can still be callouts.
document.addEventListener("DOMContentLoaded", () => {
  const checkbox = document.getElementById("callout_box");
  const warning = document.getElementById("callout-word-warning");
  // Martor adds a generated suffix to the textarea ID.
  const body = document.querySelector('.main-martor--container textarea[name="body"]');
  if (!checkbox || !warning || !body) return;

  const threshold = Number(warning.dataset.wordThreshold);
  if (!Number.isFinite(threshold)) return;

  // Unnamed subsections have no name field. Keep this list in sync with
  // CALLOUT_WORD_WARNING_EXEMPT_NAMES in nofos/nofos/views.py.
  const nameField = document.getElementById("name");
  const exemptNames = new Set(["Key facts", "Key Facts", "Key dates", "Key Dates"]);

  let editor;
  const update = () => {
    if (nameField && exemptNames.has(nameField.value.trim())) {
      if (!warning.hidden) warning.hidden = true;
      return;
    }
    // Advisory estimate, matching Python's body.split() and existing floating
    // callouts. Markdown syntax may contribute to the count; this is not a
    // rendered-height or precise readability measurement.
    const text = editor ? editor.getValue() : body.value;
    const wordCount = (text.match(/\S+/g) || []).length;
    const hidden = !checkbox.checked || wordCount <= threshold;
    if (warning.hidden !== hidden) warning.hidden = hidden;
  };

  checkbox.addEventListener("change", update);
  body.addEventListener("input", update);
  if (nameField) nameField.addEventListener("input", update);

  // Martor initializes Ace on jQuery ready, which can follow DOMContentLoaded.
  // Until it is ready, keep the server-rendered warning and textarea fallback.
  const attachEditor = (attempts = 0) => {
    const element = document.querySelector(".main-martor--container .ace_editor");
    if (window.ace && element) {
      editor = window.ace.edit(element);
      editor.on("change", update);
      update();
    } else if (attempts < 50) {
      setTimeout(() => attachEditor(attempts + 1), 100);
    }
  };

  update();
  attachEditor();
});
