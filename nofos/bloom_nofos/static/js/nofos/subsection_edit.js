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
