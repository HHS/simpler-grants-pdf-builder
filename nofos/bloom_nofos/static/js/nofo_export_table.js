(function () {
  const cells = document.querySelectorAll(".content-guide-download-cell");

  async function downloadBlob(form) {
    const formData = new FormData(form);
    const csrfToken = form.querySelector(
      'input[name="csrfmiddlewaretoken"]',
    )?.value;

    const resp = await fetch(form.action, {
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
    if (match?.[1]) {
      filename = match[1];
    }

    const objectUrl = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = objectUrl;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(objectUrl);
  }

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
      const loadingLabel = button.dataset.loadingLabel || "Preparing…";

      root.classList.remove("is-error");
      button.disabled = true;
      label.textContent = loadingLabel;
      root.classList.add("is-downloading");

      try {
        await downloadBlob(form);

        setTimeout(() => {
          button.disabled = false;
          label.textContent = defaultLabel;
          root.classList.remove("is-downloading");
        }, 1000);
      } catch (err) {
        console.error(err);
        button.disabled = false;
        label.textContent = defaultLabel;
        root.classList.remove("is-downloading");
        root.classList.add("is-error");
      }
    });
  });
})();
