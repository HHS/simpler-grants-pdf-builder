(() => {
  // Enhance only this form; other Builder forms keep their existing flows.
  const form = document.getElementById("word-comparison-form");
  if (!form || !window.fetch || !window.FormData || !window.AbortController) return;
  const field = form.querySelector('[name="passive"]');
  const button = form.querySelector('[type="submit"]');
  const fieldError = document.getElementById("passive--error");
  const feedback = document.getElementById("comparison-feedback");
  const entry = form.closest("[data-comparison-entry]");
  const failure = form.querySelector("[data-comparison-error]");
  if (!field || !button || !fieldError || !feedback || !entry || !failure) return;
  let busy = false;
  let saved = false;
  const originalDescription = field.getAttribute("aria-describedby") || "";

  function clearErrors() {
    fieldError.hidden = true;
    fieldError.textContent = "";
    field.removeAttribute("aria-invalid");
    field.setAttribute("aria-describedby", originalDescription);
    field.classList.remove("border-secondary-dark");
    failure.hidden = true;
    failure.textContent = "";
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (busy || saved) return;
    busy = true;
    clearErrors();
    feedback.replaceChildren();
    button.setAttribute("aria-disabled", "true");
    button.textContent = "Saving…";
    field.readOnly = true;
    form.setAttribute("aria-busy", "true");
    const controller = new AbortController();
    const timer = window.setTimeout(() => controller.abort(), 15000);
    try {
      const response = await window.fetch(form.action, {
        method: "POST", body: new FormData(form),
        headers: { Accept: "application/json" }, credentials: "same-origin",
        signal: controller.signal,
      });
      let payload = {};
      try { payload = await response.json(); } catch (_) { /* Safe fallback below. */ }
      if (response.status === 400 && payload.errors?.passive?.length) {
        fieldError.textContent = "Error: " + payload.errors.passive[0].message;
        fieldError.hidden = false;
        field.setAttribute("aria-invalid", "true");
        field.setAttribute("aria-describedby", (originalDescription + " passive--error").trim());
        field.classList.add("border-secondary-dark");
        fieldError.setAttribute("tabindex", "-1");
        fieldError.focus({ preventScroll: true });
        return;
      }
      if (!response.ok || payload.saved !== true || typeof payload.html !== "string") {
        if (response.status === 404) throw new Error("This report can no longer be saved. Analyze the document again.");
        if (response.status === 403 || response.redirected) throw new Error("Your session or permission may have changed. Sign in again or contact the pilot operator.");
        throw new Error("We couldn't confirm the save. Try again. The same report won't be saved twice.");
      }
      saved = true;
      // Trusted fragment rendered by the authenticated server using shared components.
      feedback.innerHTML = payload.html;
      entry.remove();
      // The submit control no longer exists: give focus a meaningful destination.
      feedback.focus({ preventScroll: true });
    } catch (error) {
      failure.textContent = error.name === "AbortError" || error instanceof TypeError
        ? "We couldn't confirm the save. Try again. The same report won't be saved twice."
        : error.message;
      failure.hidden = false;
    } finally {
      window.clearTimeout(timer);
      busy = false;
      form.removeAttribute("aria-busy");
      if (!saved) {
        field.readOnly = false;
        button.setAttribute("aria-disabled", "false");
        button.textContent = "Save comparison";
      }
    }
  });
})();
