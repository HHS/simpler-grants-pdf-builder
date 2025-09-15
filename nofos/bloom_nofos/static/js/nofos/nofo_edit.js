// This JS file does 4 things:
// 1. Operates the "NOFO actions" open/close menu
// 2. Copies the heading ids for sections and subsections (those link buttons you see)
// 3. Copies all the flagged internal links to clipboard
// 4. Controls when the "Top" link appears on the bottom right as you scroll
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
  // 2. Copies the heading ids for sections and subsections (those link buttons you see)
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
  // 3. Copies all the flagged internal links to clipboard
  // ------------------------------------------------------------
  const alertButtons = document.querySelectorAll(
    ".usa-site-alert .usa-button--content_copy"
  );
  alertButtons.forEach((button) => {
    button.addEventListener("click", function () {
      // Find the nearest parent with the class '.usa-site-alert'
      const alertBox = this.closest(".usa-site-alert");
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

  // ------------------------------------------------------------
  // 4. Controls when the "Top" link appears on the bottom right as you scroll
  // ------------------------------------------------------------
  const btn = document.querySelector(".back-to-top--container a");
  const sentinel = document.getElementById("back-to-top--sentinel");
  if (!btn || !sentinel) return;

  const io = new IntersectionObserver(([entry]) => {
    // Above top? (passed) boundingClientRect.top < 0
    const passed = entry.boundingClientRect.top < 0;

    if (entry.isIntersecting || passed) {
      btn.classList.add("is-visible");
    } else {
      // below bottom (not reached yet)
      btn.classList.remove("is-visible");
    }
  });

  io.observe(sentinel);
});

window.addEventListener("load", function () {
  document.documentElement.style.scrollBehavior = "smooth";
});
