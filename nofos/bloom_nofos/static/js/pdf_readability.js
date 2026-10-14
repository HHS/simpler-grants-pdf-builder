(() => {
  const form = document.getElementById("pdf-readability-form");
  if (form) {
    form.addEventListener("submit", (event) => {
      if (!form.checkValidity()) return;
      // Let the server render the shared inline upload error for a missing file.
      if (!document.getElementById("pdf").files.length) return;
      if (document.getElementById("analyze-pdf-button").disabled) {
        event.preventDefault();
        return;
      }
      document.getElementById("readability-progress-trigger")?.click();
      // Start the horse from the left edge when the modal opens, like Word export.
      document.getElementById("readability-progress-horse")?.classList.add("is-running");
      document.getElementById("analyze-pdf-button").disabled = true;
      document.getElementById("pdf-submit-status").textContent = "Analyzing your PDF…";
    });
  }

  // Browsers may restore the submitting page from their back/forward cache.
  window.addEventListener("pageshow", (event) => {
    if (!form || !event.persisted) return;
    document.getElementById("analyze-pdf-button").disabled = false;
    document.getElementById("pdf-submit-status").textContent = "";
    document.getElementById("readability-progress-horse")?.classList.remove("is-running");
    const modal = document.getElementById("readability-progress-modal");
    if (modal?.classList.contains("is-visible")) modal.querySelector("[data-close-modal]")?.click();
  });

  const report = document.getElementById("report-title");
  if (report) {
    const showReady = () => {
      document.getElementById("readability-progress-trigger")?.click();
      window.setTimeout(() => {
        const modal = document.getElementById("readability-progress-modal");
        if (modal?.classList.contains("is-visible")) {
          document.getElementById("readability-progress-ok")?.click();
        }
      }, 3000);
    };
    if (document.readyState === "complete") showReady();
    else window.addEventListener("load", showReady, { once: true });
  }

  const uploadError = document.getElementById("pdf--error");
  if (uploadError) {
    uploadError.setAttribute("tabindex", "-1");
    uploadError.focus();
  }

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
      text("readability-draft-scope"),
      text("readability-draft-readiness"),
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
