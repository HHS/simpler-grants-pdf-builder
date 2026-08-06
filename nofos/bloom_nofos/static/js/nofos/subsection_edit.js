document.addEventListener("DOMContentLoaded", () => {
  const headingToggle = document.getElementById("has_heading");
  const headingFields = document.getElementById("subsection-heading-fields");

  if (headingToggle && headingFields) {
    const headingInputs = headingFields.querySelectorAll("input, select");
    const syncHeadingFields = () => {
      const hasHeading = headingToggle.checked;
      headingFields.hidden = !hasHeading;
      headingInputs.forEach((input) => {
        input.disabled = !hasHeading;
      });
    };

    headingToggle.addEventListener("change", syncHeadingFields);
    syncHeadingFields();
  }

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
