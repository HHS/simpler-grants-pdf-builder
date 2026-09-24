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

  const calculationNotes = document.getElementById("readability-calculation-notes");
  if (calculationNotes) {
    let wasOpen = false;
    window.addEventListener("beforeprint", () => {
      wasOpen = calculationNotes.open;
      calculationNotes.open = true;
    });
    window.addEventListener("afterprint", () => {
      calculationNotes.open = wasOpen;
    });
  }

  const copyButton = document.getElementById("copy-readability-report");
  if (copyButton) copyButton.addEventListener("click", async () => {
    const text = (id) => document.getElementById(id)?.textContent.trim() || "";
    const lines = [
      "HHS NOFO Builder — PDF readability report",
      `File: ${text("readability-file")}`,
      `Analyzed: ${text("readability-date")}`,
      `Measurement version: ${text("readability-version")}`,
      "",
      "Measurement scope",
      text("readability-scope-pages"),
      text("readability-scope-method"),
      text("readability-coverage"),
      text("readability-word-scope"),
      text("readability-reliability"),
      "",
      "Readability measures",
    ];
    document.querySelectorAll(".readability-metric").forEach((metric) => {
      lines.push(metric.textContent.trim().replace(/\s+/g, " "));
    });
    const notes = document.querySelectorAll("#readability-warning-list li");
    if (notes.length) {
      lines.push("", `Calculation notes (${notes.length})`);
      notes.forEach((note) => lines.push(`- ${note.textContent.trim()}`));
    }
    lines.push("", "How to read these results", text("readability-disclaimer"));
    const reportText = lines.filter((line, index) => line || lines[index - 1]).join("\n");
    const status = document.getElementById("readability-copy-status");
    const fallback = document.getElementById("readability-copy-fallback");
    try {
      if (!navigator.clipboard?.writeText) throw new Error("Clipboard unavailable");
      await navigator.clipboard.writeText(reportText);
      fallback.hidden = true;
      status.textContent = "Metrics copied to clipboard.";
    } catch {
      fallback.value = reportText;
      fallback.hidden = false;
      fallback.focus();
      fallback.select();
      status.textContent = "Automatic copying is unavailable. The report text is selected below; press Command+C or Ctrl+C to copy it.";
    }
  });
})();
