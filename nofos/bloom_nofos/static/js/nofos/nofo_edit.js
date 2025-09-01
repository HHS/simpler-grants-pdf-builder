// This JS file does 2 things:
// 1. Copies the heading ids for sections and subsections (those link buttons you see)
// 2. Copies all the flagged internal links to clipboard
document.addEventListener("DOMContentLoaded", function () {
  // Copy buttons for the heading ids
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

  // Copy buttons inside of the alert boxes (eg, copy broken links)
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
});

window.addEventListener("load", function () {
  document.documentElement.style.scrollBehavior = "smooth";
});
