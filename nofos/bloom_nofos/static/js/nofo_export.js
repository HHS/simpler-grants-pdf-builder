(function () {
  const form = document.getElementById("docx-download-form");
  const loading = document.getElementById("docx-state-loading");
  const success = document.getElementById("docx-state-success");
  const error = document.getElementById("docx-state-error");
  const errorText = document.getElementById("docx-error-text");
  const status = document.getElementById("docx-status");
  const doneBtn = document.getElementById("docx-done-btn");
  const horseTrack = document.getElementById("docx-horse-track");
  const modalWrapper = document
    .getElementById("docx-modal")
    ?.closest(".usa-modal-wrapper");

  if (!form) return;

  let closeTimer = null;

  function clearCloseTimer() {
    if (closeTimer) {
      clearTimeout(closeTimer);
      closeTimer = null;
    }
  }

  function isModalOpen() {
    return modalWrapper?.classList.contains("is-visible");
  }

  function setState(state, message) {
    loading.hidden = state !== "loading";
    success.hidden = state !== "success";
    error.hidden = state !== "error";

    if (state === "loading") {
      doneBtn.hidden = true;
      status.textContent = message || "Generating your document.";

      horseTrack?.classList.add("is-running");
      horseTrack?.classList.remove("is-finished");

      clearCloseTimer();
    } else {
      doneBtn.hidden = false;
      status.textContent = "";
    }

    if (state === "error" && message) {
      errorText.textContent = message;

      horseTrack?.classList.remove("is-running");
      horseTrack?.classList.remove("is-finished");

      clearCloseTimer();
    }

    // Auto-close on success after 3s (only if still open)
    if (state === "success") {
      clearCloseTimer();

      horseTrack?.classList.add("is-finished");
      horseTrack?.classList.remove("is-running");

      closeTimer = setTimeout(() => {
        if (isModalOpen()) {
          doneBtn.click(); // closes via USWDS data-close-modal
        }
      }, 3000);
    }
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    setState("loading");

    try {
      const action_url = form.getAttribute("action");
      const csrfToken = form.dataset.csrfToken;

      const formData = new FormData(form);
      formData.set("export_action", "download");

      const resp = await fetch(action_url, {
        method: "POST",
        body: formData,
        credentials: "same-origin",
        headers: {
          "X-Requested-With": "XMLHttpRequest",
          "X-CSRFToken": csrfToken,
        },
      });

      if (!resp.ok) {
        const text = await resp.text().catch(() => "");
        throw new Error(text || `Request failed (${resp.status})`);
      }

      const blob = await resp.blob();

      let filename = "document.docx";
      const cd = resp.headers.get("Content-Disposition");
      const match = cd && cd.match(/filename="([^"]+)"/i);
      if (match?.[1]) filename = match[1];

      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);

      setState("success");
    } catch (err) {
      console.error(err);
      setState(
        "error",
        "Sorry — something went wrong generating the document. Please try again.",
      );
    }
  });

  // If the user closes manually, prevent a delayed click later
  doneBtn?.addEventListener("click", clearCloseTimer);
})();
