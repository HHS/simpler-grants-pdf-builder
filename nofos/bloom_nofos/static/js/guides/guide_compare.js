// This JS file does 2 things:
// 1. Highlights the right nav item based on the viewport's scroll position (taking offset into account because of sticky headers)
// 2. Activates the "next section"/"previous section" buttons as we scroll
document.addEventListener("DOMContentLoaded", function () {
  const OFFSET = 200; // 5px more than scroll-margin-top
  const navLinks = Array.from(
    document.querySelectorAll(".nofo_view--changes--list a")
  );
  const navContainer = document.querySelector(".nofo_view--changes--list ol");
  const prefersReduced = window.matchMedia(
    "(prefers-reduced-motion: reduce)"
  ).matches;

  const prevBtn = document.querySelector(".usa-button--expand_less");
  const nextBtn = document.querySelector(".usa-button--expand_more");

  const sections = navLinks
    .map((link) => {
      const id = link.getAttribute("href").substring(1);
      const heading = document.querySelector(`#${CSS.escape(id)}`);
      return { link, heading };
    })
    .filter((item) => item.heading);

  let lastActiveLI = null;

  function ensureVisible(li) {
    const c = navContainer; // your side-nav <ol>
    if (!c || !li) return;

    const pad = 5; // cushion
    const cRect = c.getBoundingClientRect();
    const r = li.getBoundingClientRect();
    const above = r.top < cRect.top + pad;
    const below = r.bottom > cRect.bottom - pad;

    if (!(above || below)) return; // already in view

    // Center the item within the container
    // offsetTop is fine here since <li> is a child of the <ol>. If nested, sum offsetTop chain.
    const liTop = li.offsetTop;
    const liHeight = li.offsetHeight;
    const target = Math.max(
      0,
      Math.min(
        liTop - (c.clientHeight - liHeight) / 2,
        c.scrollHeight - c.clientHeight
      )
    );

    c.scrollTo({
      top: target,
      behavior: prefersReduced ? "auto" : "smooth",
    });
  }

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
      if (rect.top - OFFSET <= 0) current = sections[i];
      else break;
    }

    // No active if above first section
    if (
      sections.length &&
      sections[0].heading.getBoundingClientRect().top - OFFSET > 0
    ) {
      current = null;
    }

    navLinks.forEach((link) =>
      link.parentElement.classList.remove("is-active")
    );

    if (current) {
      const li = current.link.parentElement;
      li.classList.add("is-active");

      // Only scroll the side-nav when the active item changed
      if (li !== lastActiveLI) {
        // Defer to next frame to avoid layout thrash while scrolling
        requestAnimationFrame(() => ensureVisible(li));
        lastActiveLI = li;
      }
    } else {
      lastActiveLI = null;
    }

    setButtonState();
  }

  // "passive: true" improves scroll performance
  window.addEventListener("scroll", updateActiveNav, { passive: true });
  updateActiveNav(); // run on page load
});
