/* Transient results only. Editing/reimporting reloads the page and clears them. */
(() => {
  const form = document.getElementById("section-readability");
  if (!form) return;
  const rows = Array.from(document.querySelectorAll("[data-section-readability]"));
  const notice = document.getElementById("section-readability-status");
  const allButton = form.querySelector("button");
  const messages = {
    insufficient: "Not enough prose for a grade estimate. At least 50 words in 3 complete sentences are needed.",
    excluded_policy: "Not scored: identified policy language. Review it through the policy workflow.",
    excluded_basic: "Not scored: Basic information.",
    policy_unavailable: "Not scored: canonical policy data is not configured.",
    unavailable: "Grade-level estimate unavailable. Try again.",
  };
  const summaries = {
    insufficient: "Readability: too little text",
    excluded_policy: "Readability: policy language excluded",
    excluded_basic: "Readability: Basic information excluded",
    policy_unavailable: "Readability: unavailable",
    unavailable: "Readability: unavailable",
  };
  let busy = false;
  let stale = false;
  const clear = (message) => {
    rows.forEach((row) => {
      row.querySelector("[data-section-result]").textContent = message;
      row.querySelector("[data-section-explanation]").textContent = "Reload this page before checking again.";
      row.querySelector("button").hidden = false;
    });
    allButton.hidden = false;
  };
  async function check(selected) {
    if (busy || stale) return;
    const targets = selected ? rows.filter((row) => row.dataset.sectionReadability === selected) : rows;
    if (selected ? !targets.length || targets[0].querySelector("button").hidden : allButton.hidden) return;
    const trigger = selected ? targets[0].querySelector("button") : allButton;
    busy = true;
    allButton.setAttribute("aria-disabled", "true");
    rows.forEach((row) => row.querySelector("button").setAttribute("aria-disabled", "true"));
    targets.forEach((row) => { row.querySelector("[data-section-result]").textContent = "Readability: checking…"; });
    notice.textContent = "Checking section readability.";
    try {
      const response = await fetch(form.dataset.url, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": form.querySelector("[name=csrfmiddlewaretoken]").value },
        body: JSON.stringify({ revision: form.dataset.revision, ...(selected ? { subsection_id: selected } : {}) }),
      });
      if (response.status === 409) {
        stale = true;
        clear("Results cleared: this document or measurement has changed.");
        notice.textContent = "Reload this page before checking again.";
        return;
      }
      if (!response.ok) throw new Error("unavailable");
      const data = await response.json();
      if (stale) return;
      if (data.revision !== form.dataset.revision) {
        stale = true;
        clear("Results cleared: this document or measurement has changed.");
        notice.textContent = "Reload this page before checking again.";
        return;
      }
      const restoreFocus = document.activeElement === trigger;
      targets.forEach((row) => {
        const result = data.results.find((item) => item.id === row.dataset.sectionReadability);
        const output = row.querySelector("[data-section-result]");
        const explanation = row.querySelector("[data-section-explanation]");
        output.textContent = result?.status === "current"
          ? `Readability: grade ${result.grade.toFixed(1)} estimate`
          : summaries[result?.status] || summaries.unavailable;
        explanation.textContent = result?.status === "current"
          ? "Flesch–Kincaid grade-level estimate. A result does not mean the text is approved for editing."
          : messages[result?.status] || messages.unavailable;
        const retry = !result || result.status === "unavailable";
        row.querySelector("button").hidden = !retry;
        row.querySelector("[data-section-check-label]").textContent = retry ? "Retry" : "Check";
        // Reuse Builder's validated targets as reference, without inferring a
        // NOFO category or making a section-level compliance determination.
        if (result?.status === "current") {
          (data.goals || []).forEach((goal) => {
            const limit = goal.operator === "at_most_by_category"
              ? `at most ${goal.minimum} or ${goal.maximum}, depending on NOFO type`
              : `${goal.operator === "at_most" ? "at most" : "at least"} ${goal.value}`;
            explanation.textContent += ` ${goal.label}: ${limit}.`;
          });
        }
      });
      notice.textContent = data.results.some((result) => result.status === "policy_unavailable")
        ? "Section readability is unavailable until canonical policy data is configured."
        : "Section readability checked. Results appear beside each subsection and are not saved.";
      if (selected) {
        notice.textContent = `${targets[0].dataset.subsectionName}: ${targets[0].querySelector("[data-section-result]").textContent}. ${targets[0].querySelector("[data-section-explanation]").textContent}`;
      }
      allButton.hidden = rows.length > 0 && rows.every((row) => row.querySelector("button").hidden);
      // Move focus only if the completed action is still focused when hidden.
      if (trigger.hidden && restoreFocus) {
        (selected ? targets[0].querySelector("summary") : notice).focus();
      }
    } catch {
      if (stale) return;
      targets.forEach((row) => {
        row.querySelector("[data-section-result]").textContent = summaries.unavailable;
        row.querySelector("[data-section-explanation]").textContent = messages.unavailable;
        row.querySelector("[data-section-check-label]").textContent = "Retry";
        row.querySelector("button").hidden = false;
      });
      notice.textContent = "Section readability could not be checked. Try again.";
    } finally {
      busy = false;
      allButton.setAttribute("aria-disabled", String(stale));
      rows.forEach((row) => row.querySelector("button").setAttribute("aria-disabled", String(stale)));
    }
  }
  form.addEventListener("submit", (event) => { event.preventDefault(); check(); });
  rows.forEach((row) => row.querySelector("button").addEventListener("click", () => check(row.dataset.sectionReadability)));
  window.addEventListener("pageshow", (event) => {
    if (event.persisted) {
      stale = true;
      clear("Results cleared: reload this page before checking again.");
      allButton.setAttribute("aria-disabled", "true");
      rows.forEach((row) => row.querySelector("button").setAttribute("aria-disabled", "true"));
      notice.textContent = "Reload this page to check current content.";
    }
  });
})();
