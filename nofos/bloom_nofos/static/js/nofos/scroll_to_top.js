document.addEventListener("DOMContentLoaded", function () {
  const btn = document.querySelector(".back-to-top--container a");
  
  if (!btn) return;

  // Show button after scrolling past 90% of viewport height
  const triggerHeight = window.innerHeight * 0.9;

  const handleScroll = () => {
    if (window.scrollY > triggerHeight) {
      btn.classList.add("is-visible");
    } else {
      btn.classList.remove("is-visible");
    }
  };

  // Use passive listener for better scroll performance
  window.addEventListener("scroll", handleScroll, { passive: true });

  // Smooth scroll to top when clicked
  btn.addEventListener("click", function (e) {
    e.preventDefault();
    window.scrollTo({
      top: 0,
      behavior: "smooth"
    });
  });
});