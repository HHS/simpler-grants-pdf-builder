// This JS file returns more audit events if available, appends them to the table of existing audit events, and then resets the button with the next offset
const btn = document.getElementById("load-more-btn");
btn?.addEventListener("click", async (e) => {
  const button = e.currentTarget;
  const tbody = document.getElementById("audit-events-body");

  button.disabled = true;
  button.textContent = "Loading...";

  try {
    // Fetch the next page using the current offset
    const response = await fetch(`?offset=${button.dataset.nextOffset}`);
    const html = await response.text();

    // Parse response once and grab the new rows
    const doc = new DOMParser().parseFromString(html, "text/html");
    const newBody = doc.getElementById("audit-events-body");

    // Append new rows directly
    tbody.insertAdjacentHTML("beforeend", newBody.innerHTML);

    // Update or remove the button
    const nextButton = doc.getElementById("load-more-btn");

    const hasMore = doc.getElementById("load-more-btn");
    if (nextButton) {
      button.dataset.nextOffset = hasMore.dataset.nextOffset;
      button.disabled = false;
      button.textContent = "Load More Events";
    } else {
      button.remove();
    }
  } catch (error) {
    console.error("Error loading more events:", error);
    button.textContent = "Error loading more events. Try again.";
    button.disabled = false;
  }
});
