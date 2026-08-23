(function () {
  if (!window.NofoExport?.downloadFormAsBlob) return;

  function setupForm(form) {
    const button = form.querySelector("button[aria-controls]");
    const modalId = button?.getAttribute("aria-controls");
    const modal = modalId ? document.getElementById(modalId) : null;
    if (!modal) return;

    const loading = modal.querySelector('[data-docx-state="loading"]');
    const success = modal.querySelector('[data-docx-state="success"]');
    const error = modal.querySelector('[data-docx-state="error"]');
    const errorText = modal.querySelector("[data-docx-error-text]");
    const status = modal.querySelector("[data-docx-status]");
    const doneBtn = modal.querySelector("[data-docx-done-btn]");
    const horseTrack = modal.querySelector("[data-docx-horse-track]");
    const modalWrapper = modal.closest(".usa-modal-wrapper");

    if (!loading || !success || !error || !doneBtn) return;

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
        if (status) status.textContent = message || "Generating your document.";

        horseTrack?.classList.add("is-running");
        horseTrack?.classList.remove("is-finished");

        clearCloseTimer();
        return;
      }

      doneBtn.hidden = false;
      if (status) status.textContent = "";

      if (state === "error") {
        if (errorText) {
          errorText.textContent =
            message ||
            "Sorry — something went wrong generating the document. Please try again.";
        }

        horseTrack?.classList.remove("is-running");
        horseTrack?.classList.remove("is-finished");

        clearCloseTimer();
        return;
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

    form.addEventListener("submit", async function (e) {
      e.preventDefault();
      setState("loading");

      try {
        await window.NofoExport.downloadFormAsBlob(form);
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
    doneBtn.addEventListener("click", clearCloseTimer);
  }

  document.querySelectorAll(".docx-download-form").forEach(setupForm);
})();
