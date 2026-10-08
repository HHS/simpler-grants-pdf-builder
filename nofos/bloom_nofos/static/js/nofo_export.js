(function () {
  window.NofoExport = window.NofoExport || {};

  window.NofoExport.downloadFormAsBlob = async function (form) {
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
      const error = new Error(`Request failed (${resp.status})`);
      if (resp.headers.get("Content-Type")?.includes("application/json")) {
        const body = await resp.json().catch(() => null);
        if (typeof body?.word_export_error === "string") {
          error.userMessage = body.word_export_error.slice(0, 500);
        }
      }
      throw error;
    }

    const blob = await resp.blob();

    let filename = "document.docx";
    const contentDisposition = resp.headers.get("Content-Disposition");
    const match =
      contentDisposition && contentDisposition.match(/filename="([^"]+)"/i);

    if (match?.[1]) {
      filename = match[1];
    }

    const objectUrl = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = objectUrl;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(objectUrl);
  };
})();
