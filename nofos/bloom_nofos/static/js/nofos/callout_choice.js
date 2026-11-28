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

// Warn, without blocking, when a note doesn't start with a note label such as
// "**Note:**" or "**Note for applicants:**". Keep the pattern in sync with
// _IMPORT_LABEL and has_note_label in nofos/nofos/note_paragraphs.py.
const NOTE_LABEL =
  /^\s*(?:\*\*|__|\*|_)?\s*(?:(?:please\s+)?notes?(?:\s+for(?:\s+(?![-–—](?:\s|$))[^\s:()–—]+){1,8})?(?:\s*\([^()]{1,80}\))?\s*[:\-–—]|n\.\s*b\.(?:\s*[:\-–—])?(?=\s|$))/i;

document.addEventListener("DOMContentLoaded", () => {
  const note = document.getElementById("callout_style");
  const warning = document.getElementById("note-label-warning");
  // Martor adds a generated suffix to the textarea ID.
  const body = document.querySelector('.main-martor--container textarea[name="body"]');
  if (!note || !warning || !body) return;

  let editor;
  const update = () => {
    const text = editor ? editor.getValue() : body.value;
    // Drop Markdown emphasis markers so "**Note**:" and "**N.B.**" also count.
    const firstLine = text.trimStart().split("\n", 1)[0].replace(/\*+|_+/g, "");
    const hidden = !note.checked || NOTE_LABEL.test(firstLine);
    if (warning.hidden !== hidden) warning.hidden = hidden;
  };

  note.addEventListener("change", update);
  body.addEventListener("input", update);

  // Martor initializes Ace on jQuery ready, which can follow DOMContentLoaded.
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
