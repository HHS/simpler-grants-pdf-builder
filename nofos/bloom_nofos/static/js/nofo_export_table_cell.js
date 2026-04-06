(function () {
  const cells = document.querySelectorAll(".content-guide-download-cell");

  if (!cells.length || !window.NofoExport?.downloadFormAsBlob) return;

  cells.forEach((root) => {
    if (root.dataset.downloadBound === "true") return;
    root.dataset.downloadBound = "true";

    const form = root.querySelector(".content-guide-download-form");
    const button = root.querySelector(".content-guide-download-btn");
    const label = root.querySelector(".content-guide-download-label");

    if (!form || !button || !label) return;

    form.addEventListener("submit", async function (e) {
      e.preventDefault();

      const defaultLabel = button.dataset.defaultLabel || "Download";
      const loadingLabel = button.dataset.loadingLabel || "Loading…";

      root.classList.remove("is-error");
      button.disabled = true;
      label.textContent = loadingLabel;
      root.classList.add("is-downloading");
      button.classList.remove("usa-button--file_download");
      button.classList.add("usa-button--loader");

      try {
        await window.NofoExport.downloadFormAsBlob(form);

        setTimeout(() => {
          button.disabled = false;
          label.textContent = defaultLabel;
          root.classList.remove("is-downloading");
          button.classList.remove("usa-button--loader");
          button.classList.add("usa-button--file_download");
        }, 1000);
      } catch (err) {
        console.error(err);
        button.disabled = false;
        label.textContent = defaultLabel;
        root.classList.remove("is-downloading");
        root.classList.add("is-error");
        button.classList.remove("usa-button--loader");
        button.classList.add("usa-button--file_download");
      }
    });
  });
})();
