// This JS file controls which checkboxes are clicked and sends AJAX requests to the server to set subsection comparison_types
document.addEventListener("DOMContentLoaded", () => {
  const compareAllCheckbox = document.getElementById("compare-all-sections");
  const sectionCheckboxes = document.querySelectorAll(
    'input[name="compare_sections"]'
  );
  const subsectionCheckboxes = document.querySelectorAll(
    'input[name="compare_subsections"]'
  );
  const allCheckboxes = [
    compareAllCheckbox,
    ...sectionCheckboxes,
    ...subsectionCheckboxes,
  ];
  const usaButtons = document.querySelectorAll(".usa-button");
  const container = document.querySelector(".compare-all-sections-container"); // has data-url + data-csrf-token

  /* ------------------------- small helpers ------------------------- */

  // Create or remove a slim USWDS alert just after .usa-list
  function showAlert(message, status = "warning") {
    const summaryList = document.querySelector(".usa-list");
    if (!summaryList) return;

    // remove existing alert if present
    document.getElementById("compare-alert")?.remove();

    const el = document.createElement("div");
    el.id = "compare-alert";
    el.className = `usa-alert usa-alert--${status} usa-alert--slim margin-top-2`;
    el.setAttribute("role", "alert");
    el.setAttribute("tabindex", "-1");
    el.innerHTML = `<div class="usa-alert__body"><p class="usa-alert__text">${message}</p></div>`;
    summaryList.after(el);
    el.focus();

    // auto-remove after 4s
    setTimeout(() => el.remove(), 4000);
  }

  function setControlsDisabled(disabled) {
    allCheckboxes.forEach((cb) => (cb.disabled = disabled));
    usaButtons.forEach((btn) => (btn.disabled = disabled));
  }

  function updateUsaButtons() {
    const noneChecked = allCheckboxes.every((cb) => !cb.checked);
    usaButtons.forEach((btn) => {
      btn.toggleAttribute("aria-disabled", noneChecked);
      btn.toggleAttribute("disabled", noneChecked);
      btn.classList.toggle("disabled-link", noneChecked);
    });
    if (noneChecked) {
      showAlert(
        "Please select at least one section or subsection to compare.",
        "warning"
      );
    } else {
      document.getElementById("compare-alert")?.remove();
    }
  }

  // Map a NodeList of checkboxes to { checkbox -> {current, desired} }
  function buildCheckboxValueMap(nodes, desired) {
    const map = new Map();
    nodes.forEach((cb) => {
      map.set(cb, { current: cb.checked, desired });
      cb.checked = desired;
    });
    return map;
  }

  // Keep the tri-state "Compare All" checkbox accurate
  function updateCompareAllSectionsCheckbox() {
    const list = [...sectionCheckboxes, ...subsectionCheckboxes];
    const allChecked = list.every((cb) => cb.checked);
    const anyChecked = list.some((cb) => cb.checked);
    compareAllCheckbox.checked = allChecked;
    compareAllCheckbox.indeterminate = !allChecked && anyChecked;
  }

  // Keep each section checkbox in sync with its subsections
  function updateCompareSectionCheckboxes() {
    sectionCheckboxes.forEach((sectionCheckbox) => {
      const sectionId = sectionCheckbox.value;
      const sectionSubs = document.querySelectorAll(
        `#section-${sectionId} input[name="compare_subsections"]`
      );
      if (!sectionSubs.length) return;

      const allChecked = [...sectionSubs].every((cb) => cb.checked);
      const anyChecked = [...sectionSubs].some((cb) => cb.checked);
      sectionCheckbox.checked = allChecked;
      sectionCheckbox.indeterminate = !allChecked && anyChecked;
    });
  }

  /* ----------------------------- save ------------------------------ */

  async function saveSubsectionSelections(checkboxValueMap, elementForFocus) {
    const url = container?.dataset.url;
    const csrfToken = container?.dataset.csrfToken;
    if (!url || !csrfToken) {
      console.error(
        "Missing URL or CSRF token on .compare-all-sections-container"
      );
      return;
    }

    setControlsDisabled(true);

    // body: { subsections: { "<id>": true|false } }
    const subsections = Object.fromEntries(
      [...checkboxValueMap.entries()].map(([cb, v]) => [cb.value, v.desired])
    );

    try {
      const res = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken,
        },
        credentials: "same-origin",
        body: JSON.stringify({ subsections }),
      });
      const data = await res.json();

      if (data.status === "success") {
        console.log(
          `Subsection selections saved. ${data.updated_count} updated.`
        );
      } else if (data.status === "fail") {
        console.error(data.message);
      } else if (data.status === "partial") {
        console.warn(data.message);
      }

      // Revert any failed IDs to their previous state
      (data.failed_subsection_ids || []).forEach((failedId) => {
        const failed = document.querySelector(
          `input[name="compare_subsections"][value="${failedId}"]`
        );
        if (!failed) return;
        for (const [mapCb, values] of checkboxValueMap.entries()) {
          if (mapCb.value === failedId) {
            failed.checked = values.current;
            break;
          }
        }
      });

      if (data.status !== "success") {
        showAlert(
          data.message || "There was a problem saving your selection.",
          data.status === "fail" ? "error" : "warning"
        );
        elementForFocus?.focus();
      }
    } catch (err) {
      console.error("Error saving subsection selections:", err);
      showAlert("There was a problem saving your selection.", "error");
      elementForFocus?.focus();
    } finally {
      updateCompareSectionCheckboxes();
      updateCompareAllSectionsCheckbox();
      setControlsDisabled(false);
      updateUsaButtons();
    }
  }

  // Expose for other parts of the page that may call it
  window.saveSubsectionSelections = saveSubsectionSelections;

  /* --------------------------- event wires ------------------------- */

  // "Compare All Sections" toggles all sections + subsections
  compareAllCheckbox.addEventListener("change", function () {
    const desired = this.checked;
    const map = buildCheckboxValueMap(subsectionCheckboxes, desired);
    // also reflect on all section checkboxes
    sectionCheckboxes.forEach((cb) => (cb.checked = desired));
    saveSubsectionSelections(map, this);
  });

  // A section checkbox toggles only its own subsections
  sectionCheckboxes.forEach((sectionCheckbox) => {
    sectionCheckbox.addEventListener("change", function () {
      const sectionId = this.value;
      const desired = this.checked;
      const sectionSubs = document.querySelectorAll(
        `#section-${sectionId} input[name="compare_subsections"]`
      );
      const map = buildCheckboxValueMap(sectionSubs, desired);
      saveSubsectionSelections(map, this);
    });
  });

  // Individual subsection checkbox
  subsectionCheckboxes.forEach((subsectionCheckbox) => {
    subsectionCheckbox.addEventListener("change", function () {
      const map = new Map([
        [this, { current: !this.checked, desired: this.checked }],
      ]);
      saveSubsectionSelections(map, this);
    });
  });

  /* --------------------------- initial sync ------------------------ */
  updateCompareSectionCheckboxes();
  updateCompareAllSectionsCheckbox();
  updateUsaButtons();
});
