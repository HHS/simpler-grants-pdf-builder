// This JS does 2 things:
// 1. Set table size in a CSS var to avoid a safari bug related to centering "Add subsection" buttons
// 2. Set or unset "tables-full-width" class when checkbox is clicked

// Render a temporary USWDS alert after the summary box
function showMessage(message, type = "success") {
  const el = document.createElement("div");
  el.className = `usa-alert usa-alert--${
    type === "success" ? "success" : "error"
  } usa-alert--slim margin-top-2`;
  el.innerHTML = `<div class="usa-alert__body"><p class="usa-alert__text">${message}</p></div>`;
  document.querySelector(".usa-summary-box")?.after(el);
  setTimeout(() => el.remove(), 4000);
}

document.addEventListener("DOMContentLoaded", () => {
  // Set CSS var to current table width (for Safari button positioning)
  const setTableWidthVariable = () => {
    const table = document.querySelector("table.table--section");
    if (table) {
      document.documentElement.style.setProperty(
        "--safari-tr-width",
        table.offsetWidth + "px"
      );
    }
  };

  // Initial run
  setTableWidthVariable();

  // Debounced resize
  let t;
  window.addEventListener("resize", () => {
    clearTimeout(t);
    t = setTimeout(setTableWidthVariable, 200);
  });

  // Set full table CSS when checkbox is clicked
  const checkbox = document.getElementById("toggle-tables-checkbox");
  if (!checkbox) return; // nothing to do

  // Fire POST on toggle; disable during request; restore on error
  checkbox.addEventListener("change", async () => {
    const prev = checkbox.checked;
    checkbox.disabled = true;

    try {
      const res = await fetch(checkbox.dataset.url, {
        method: "POST",
        headers: {
          "X-CSRFToken": checkbox.dataset.csrfToken,
          "Content-Type": "application/json",
        },
        credentials: "same-origin",
      });

      const data = await res.json();

      if (data?.success) {
        // Server decides the final state (default => unchecked, else checked)
        checkbox.checked = data.state !== "default";
        showMessage(data.message || "Saved.", "success");
      } else {
        checkbox.checked = prev;
        showMessage(
          data?.message || "An error occurred. Please try again.",
          "error"
        );
      }
    } catch (err) {
      console.error("Toggle error:", err);
      checkbox.checked = prev;
      showMessage("An error occurred. Please try again.", "error");
    } finally {
      checkbox.disabled = false;
      checkbox.focus();
    }
  });
});
