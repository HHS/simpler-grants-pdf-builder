// This JS file does 5 things:
// 1. Operates the "NOFO actions" open/close menu
// 2. Controls tablist for broken links and heading issues to check in your NOFO
// 3. Copies the heading ids for sections and subsections (those link buttons you see)
// 4. Copies all the flagged internal links to clipboard
// 5. Controls when the "Top" link appears on the bottom right as you scroll
document.addEventListener("DOMContentLoaded", function () {
  // ------------------------------------------------------------
  // 1. Operates the "NOFO actions" open/close menu
  // ------------------------------------------------------------
  function nofoActionsInit(root) {
    const btn = root.querySelector("button[aria-controls]");
    const panel = document.getElementById(btn.getAttribute("aria-controls"));
    if (!btn || !panel) return;

    function setOpen(open) {
      btn.setAttribute("aria-expanded", String(open));
      panel.hidden = !open;
    }

    // initial state (ensure DOM and ARIA agree)
    setOpen(btn.getAttribute("aria-expanded") === "true" && !panel.hidden);

    btn.addEventListener("click", () => {
      const open = btn.getAttribute("aria-expanded") === "true";
      setOpen(!open);
    });

    // Optional: close on Escape when focus is inside
    root.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && btn.getAttribute("aria-expanded") === "true") {
        setOpen(false);
        btn.focus();
      }
    });

    // Optional: click outside to close
    document.addEventListener("click", (e) => {
      if (
        !root.contains(e.target) &&
        btn.getAttribute("aria-expanded") === "true"
      ) {
        setOpen(false);
      }
    });
  }

  document.querySelectorAll("[data-disclosure]").forEach(nofoActionsInit);

  // ------------------------------------------------------------
  // 2. Controls tablist for broken links and heading issues to check in your NOFO
  // ------------------------------------------------------------
  /**
   * Accessible tabs (ARIA Authoring Practices)
   * - Keeps aria-selected, tabindex, and panels in sync
   * - Keyboard: ArrowLeft/ArrowRight, Home, End
   * - Click selects and focuses tab
   * - Works for multiple tablists with [role="tablist"].automatic
   * Source: https://www.w3.org/WAI/ARIA/apg/patterns/tabs/examples/tabs-automatic/
   */
  class TabsAutomatic {
    constructor(tablistNode) {
      this.tablistNode = tablistNode;
      this.tabs = [...tablistNode.querySelectorAll('[role="tab"]')];
      this.panels = this.tabs.map((tab) =>
        document.getElementById(tab.getAttribute("aria-controls"))
      );

      // Prime all tabs/panels to a known baseline
      this.tabs.forEach((tab, i) => {
        tab.tabIndex = -1;
        tab.setAttribute("aria-selected", "false");
        tab.addEventListener("keydown", (e) => this.onKeydown(e));
        tab.addEventListener("click", () => this.setSelected(i));
      });

      // Activate the first tab without stealing focus on init
      this.setSelected(0, /*focus=*/ false);
    }

    /** Select tab by index; manage ARIA + focus + panel visibility */
    setSelected(index, focus = true) {
      this.currentIndex = index;

      this.tabs.forEach((tab, i) => {
        const isSelected = i === index;
        tab.setAttribute("aria-selected", String(isSelected));
        if (isSelected) {
          tab.removeAttribute("tabindex");
          if (focus) tab.focus();
        } else {
          tab.tabIndex = -1;
        }
        this.panels[i].classList.toggle("is-hidden", !isSelected);
      });
    }

    /** Compute a wrapped index (for ArrowLeft/ArrowRight) */
    wrap(i) {
      const len = this.tabs.length;
      return (i + len) % len;
    }

    /** Keyboard support per WAI-ARIA Tabs pattern */
    onKeydown(e) {
      const i = this.tabs.indexOf(e.currentTarget);
      const key = e.key;

      if (key === "ArrowLeft") this.setSelected(this.wrap(i - 1));
      else if (key === "ArrowRight") this.setSelected(this.wrap(i + 1));
      else if (key === "Home") this.setSelected(0);
      else if (key === "End") this.setSelected(this.tabs.length - 1);
      else return; // ignore other keys

      e.preventDefault();
      e.stopPropagation();
    }
  }

  // Initialize all automatic tablists
  document
    .querySelectorAll('[role="tablist"].automatic')
    .forEach((node) => new TabsAutomatic(node));

  // ------------------------------------------------------------
  // 3. Copies the heading ids for sections and subsections (those link buttons you see)
  // ------------------------------------------------------------
  const tableButtons = document.querySelectorAll(
    ".table--section .usa-button--content_copy"
  );
  tableButtons.forEach((button) => {
    button.addEventListener("click", function () {
      // Copy data-section-id to clipboard
      navigator.clipboard.writeText(`#${this.getAttribute("data-section-id")}`);

      // Add class to button
      this.classList.add("usa-button--check");

      // Change the text inside the button's span
      const prevSpanAltText = this.querySelector("span").textContent;
      this.querySelector("span").textContent = "Copied";

      // Set a timer to revert changes after 1 second
      setTimeout(() => {
        this.classList.remove("usa-button--check");
        this.querySelector("span").textContent = prevSpanAltText;
      }, 1000);
    });
  });

  // ------------------------------------------------------------
  // 4. Copies all the flagged internal links to clipboard
  // ------------------------------------------------------------
  const alertButtons = document.querySelectorAll(
    ".usa-alert__body .usa-button--content_copy"
  );
  alertButtons.forEach((button) => {
    button.addEventListener("click", function () {
      // Find the nearest parent with the class '.usa-alert__body'
      const alertBox = this.closest(".usa-alert__body");
      if (!alertBox) return console.error("Error: no alert box.");

      const detailsElement = alertBox.querySelector("details");
      const wasClosed = !detailsElement.open;
      // Temporarily open the <details> element if it's closed
      if (wasClosed) detailsElement.open = true;

      const summaryText = alertBox.querySelector("summary").innerText;
      const listText = Array.from(alertBox.querySelectorAll("ol li"))
        .map((item, i) => `${i + 1}. ${item.innerText}`)
        .join("\n");

      navigator.clipboard
        .writeText(`${summaryText}\n\n${listText}`)
        .then(() => {
          // Change button text on success
          button.innerHTML = "Copied!";
          // Revert text after 1 second
          setTimeout(() => (button.innerHTML = "Copy links"), 1000);
        })
        .catch((err) => console.error("Failed to copy text: " + err));

      if (wasClosed) detailsElement.open = false;
    });
  });
});