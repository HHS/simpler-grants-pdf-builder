document.addEventListener('DOMContentLoaded', function() {
  const expandCollapseBtn = document.getElementById('expand-collapse-all');
  const accordionButtons = document.querySelectorAll('.usa-accordion__button');

  function updateButtonState() {
    // Check if all accordions are expanded
    const allExpanded = Array.from(accordionButtons).every(btn =>
      btn.getAttribute('aria-expanded') === 'true'
    );

    if (allExpanded) {
      expandCollapseBtn.textContent = 'Collapse all';
      expandCollapseBtn.classList.remove('usa-button--add');
      expandCollapseBtn.classList.add('usa-button--remove');
    } else {
      expandCollapseBtn.textContent = 'Expand all';
      expandCollapseBtn.classList.remove('usa-button--remove');
      expandCollapseBtn.classList.add('usa-button--add');
    }
  }

  expandCollapseBtn.addEventListener('click', function() {
    // Check current state
    const allExpanded = Array.from(accordionButtons).every(btn =>
      btn.getAttribute('aria-expanded') === 'true'
    );

    // Save current scroll position
    const currentScrollY = window.scrollY;

    // Toggle all accordions
    const buttonsArray = Array.from(accordionButtons);

    buttonsArray.forEach(btn => {
      if (allExpanded) {
        // Collapse all
        if (btn.getAttribute('aria-expanded') === 'true') {
          btn.click();
        }
      } else {
        // Expand all
        if (btn.getAttribute('aria-expanded') === 'false') {
          btn.click();
        }
      }
    });

    // Restore scroll position and focus on expand/collapse button to prevent auto-scrolling
    window.scrollTo(0, currentScrollY);
    expandCollapseBtn.focus();

    // Update button state after a brief delay to allow accordion animations
    setTimeout(updateButtonState, 100);
  });

  // Listen for changes to accordion states (in case user manually expands/collapses)
  accordionButtons.forEach(btn => {
    btn.addEventListener('click', function() {
      setTimeout(updateButtonState, 100);
    });
  });

  // Initialize button state on page load
  updateButtonState();
});
