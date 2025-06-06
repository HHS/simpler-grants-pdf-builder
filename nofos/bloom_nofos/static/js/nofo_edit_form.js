document.addEventListener('DOMContentLoaded', function () {
  try {
    const formId = window.nofoEditFormId || 'nofo_edit_form';
    const form = document.getElementById(formId);

    // No form found
    if (!form) {
      return;
    }

    const buttons = form.querySelectorAll('button[type="submit"]');
    const replaceButton = form.querySelector('#replace-button');
    if (!buttons.length) {
      return;
    }

    const checkboxes = form.querySelectorAll('input[name="replace_subsections"]');

    // Store original text for each button
    const buttonTexts = {};
    buttons.forEach(btn => {
      buttonTexts[btn.id || btn.getAttribute('name') || 'default'] = btn.dataset.baseText || btn.textContent.trim() || 'Save';
    });

    // Nothing checked
    if (checkboxes.length === 0) {
      return;
    }

    // Initialize Select All / Deselect All button if it exists
    const toggleButton = document.getElementById('toggle-all-checkboxes');
    if (toggleButton) {
      const selectAllText = toggleButton.querySelector('.select-all-text');
      const deselectAllText = toggleButton.querySelector('.deselect-all-text');

      // Function to update the button text based on checkbox states
      function updateToggleButtonText() {
        let allChecked = true;
        checkboxes.forEach(checkbox => {
          if (!checkbox.checked) {
            allChecked = false;
          }
        });

        if (allChecked) {
          selectAllText.style.display = 'none';
          deselectAllText.style.display = 'inline';
        } else {
          selectAllText.style.display = 'inline';
          deselectAllText.style.display = 'none';
        }
      }

      // Initialize toggle button text
      updateToggleButtonText();

      // Toggle all checkboxes when button is clicked
      toggleButton.addEventListener('click', function() {
        let allChecked = true;

        // Check if all checkboxes are currently checked
        checkboxes.forEach(checkbox => {
          if (!checkbox.checked && !checkbox.disabled) {
            allChecked = false;
          }
        });

        // Toggle checkboxes based on current state
        checkboxes.forEach(checkbox => {
          if (!checkbox.disabled) {
            checkbox.checked = !allChecked;
            updateRowHighlight(checkbox);
          }
        });

        // Update button texts
        updateToggleButtonText();
        updateButtonText();
      });
    }

    function updateButtonText() {
      const checkedCount = form.querySelectorAll('input[name="replace_subsections"]:checked').length;

      buttons.forEach(button => {
        const baseText = buttonTexts[button.id || button.getAttribute('name') || 'default'];

        // Only update replace button or buttons without explicit action
        if (button.id === 'replace-button' || !button.getAttribute('name')) {
          if (button.id === 'replace-button') {
            // Special handling for replace button
            if (checkedCount === 1) {
              button.textContent = `${baseText} 1 subsection`;
            } else if (checkedCount === checkboxes.length) {
              button.textContent = `${baseText} All`;
            } else if (checkedCount > 1) {
              button.textContent = `${baseText} ${checkedCount} subsections`;
            } else {
              button.textContent = baseText;
            }
          } else {
            // Default handling for other buttons without explicit action
            if (checkedCount === 0) {
              button.textContent = baseText;
            } else if (checkedCount === 1) {
              button.textContent = `${baseText} + 1 subsection`;
            } else {
              button.textContent = `${baseText} + ${checkedCount} subsections`;
            }
          }
        }
      });
    }

    function updateRowHighlight(checkbox) {
      const row = checkbox.closest('tr');
      if (!row) return;

      // Toggle the highlight class based on checkbox state
      if (checkbox.checked) {
        row.classList.add('subsection--selected');
      } else {
        row.classList.remove('subsection--selected');
      }
    }

    // Attach listener to each checkbox
    checkboxes.forEach(function (checkbox) {
      checkbox.addEventListener('change', function () {
        updateButtonText();
        updateRowHighlight(this);

        // Update toggle button text if it exists
        if (toggleButton) {
          const selectAllText = toggleButton.querySelector('.select-all-text');
          const deselectAllText = toggleButton.querySelector('.deselect-all-text');

          let allChecked = true;
          checkboxes.forEach(checkbox => {
            if (!checkbox.checked) {
              allChecked = false;
            }
          });

          if (allChecked) {
            selectAllText.style.display = 'none';
            deselectAllText.style.display = 'inline';
          } else {
            selectAllText.style.display = 'inline';
            deselectAllText.style.display = 'none';
          }
        }
      });
    });

    // Initialize state
    updateButtonText();
    // Initialize highlighting for all checked checkboxes
    checkboxes.forEach(checkbox => {
      if (checkbox.checked) {
        updateRowHighlight(checkbox);
      }
    });

    // Add form submission handler
    form.addEventListener('submit', function(event) {
      const selectedCheckboxes = form.querySelectorAll('input[name="replace_subsections"]:checked');
      const selectedSubsections = Array.from(selectedCheckboxes).map(cb => cb.value);

      // If no subsections selected and it's a replace action, trigger cancel button click
      if (selectedSubsections.length === 0 && event.submitter && event.submitter.id === 'replace-button') {
        event.preventDefault();
        form.querySelector('a.usa-button--outline').click();
        return;
      }
    });
  } catch (error) {
    console.error('Error in form initialization:', error);
  }
});
