// This JS file does 2 things:
// 1. Highlights the right nav item based on the viewport's scroll position (taking offset into account because of sticky headers)
// 2. Activates the "next section"/"previous section" buttons as we scroll
document.addEventListener("DOMContentLoaded", function () {
  const OFFSET = 200; // 5px more than scroll-margin-top
  const navLinks = Array.from(
    document.querySelectorAll(".nofo_view--changes--list a")
  );
  const prevBtn = document.querySelector(".usa-button--expand_less");
  const nextBtn = document.querySelector(".usa-button--expand_more");

  const sections = navLinks
    .map((link) => {
      const id = link.getAttribute("href").substring(1);
      const heading = document.querySelector(`#${CSS.escape(id)}`);
      return { link, heading };
    })
    .filter((item) => item.heading);

  function setButtonState() {
    if (navLinks.length === 0) {
      prevBtn.setAttribute("aria-disabled", "true");
      nextBtn.setAttribute("aria-disabled", "true");
      return;
    }

    const activeIndex = navLinks.findIndex((link) =>
      link.parentElement.classList.contains("is-active")
    );

    // If no active link yet
    if (activeIndex === -1) {
      prevBtn.setAttribute("aria-disabled", "true");
      nextBtn.removeAttribute("aria-disabled");
      nextBtn.onclick = () => navLinks[0].click();
      return;
    }

    // Previous button
    if (activeIndex > 0) {
      prevBtn.removeAttribute("aria-disabled");
      prevBtn.onclick = () => navLinks[activeIndex - 1].click();
    } else {
      prevBtn.setAttribute("aria-disabled", "true");
      prevBtn.onclick = null;
    }

    // Next button
    if (activeIndex < navLinks.length - 1) {
      nextBtn.removeAttribute("aria-disabled");
      nextBtn.onclick = () => navLinks[activeIndex + 1].click();
    } else {
      nextBtn.setAttribute("aria-disabled", "true");
      nextBtn.onclick = null;
    }
  }

  function updateActiveNav() {
    let current = null;

    for (let i = 0; i < sections.length; i++) {
      const rect = sections[i].heading.getBoundingClientRect();
      if (rect.top - OFFSET <= 0) {
        current = sections[i];
      } else {
        break;
      }
    }

    // No active if above first section
    if (
      sections.length > 0 &&
      sections[0].heading.getBoundingClientRect().top - OFFSET > 0
    ) {
      current = null;
    }

    navLinks.forEach((link) =>
      link.parentElement.classList.remove("is-active")
    );
    if (current) {
      current.link.parentElement.classList.add("is-active");
    }

    setButtonState();
  }

  // "passive: true" improves scroll performance
  window.addEventListener("scroll", updateActiveNav, { passive: true });
  updateActiveNav(); // run on page load
});
