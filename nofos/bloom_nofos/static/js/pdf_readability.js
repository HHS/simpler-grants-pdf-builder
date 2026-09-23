(() => {
  const form = document.getElementById("pdf-readability-form");
  if (form) {
    form.addEventListener("submit", () => {
      if (!form.checkValidity()) return;
      document.getElementById("analyze-pdf-button").disabled = true;
      document.getElementById("pdf-submit-status").textContent = "Analyzing your PDF…";
    });
  }

  const errorSummary = document.getElementById("readability-error-summary");
  if (errorSummary) errorSummary.focus();

  const printButton = document.getElementById("print-readability-report");
  if (printButton) printButton.addEventListener("click", () => window.print());
})();
