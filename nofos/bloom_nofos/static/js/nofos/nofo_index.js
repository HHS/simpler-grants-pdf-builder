// This JS file adds a click event to sortable table headers to click the button when the headers are clicked
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("th[data-sortable]").forEach((th) => {
    th.addEventListener("click", (e) => {
      // Avoid double-firing if the user actually clicked the button
      if (e.target.closest("button")) return;

      const button = th.querySelector("button");
      if (button) {
        button.focus(); // move focus
        button.click(); // trigger sort
      }
    });
  });
});
