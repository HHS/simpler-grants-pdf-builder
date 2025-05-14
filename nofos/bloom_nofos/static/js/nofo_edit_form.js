document.addEventListener('DOMContentLoaded', function () {
  try {
    const formId = window.nofoEditFormId || 'nofo_edit_form';
    const form = document.getElementById(formId);
    
    if (!form) {
      console.error('Form not found:', formId);
      return;
    }

    const button = form.querySelector('button[type="submit"]');
    if (!button) {
      console.error('Submit button not found');
      return;
    }

    const checkboxes = form.querySelectorAll('input[name="replace_subsections"]');
    const originalButtonText = button.textContent.trim() || 'Save';

    if (checkboxes.length === 0) {
      // No subsection matches, nothing to do
      return;
    }

    function updateButtonText() {
      const checkedCount = form.querySelectorAll('input[name="replace_subsections"]:checked').length;
      const baseText = originalButtonText || 'Save';
      if (checkedCount === 0) {
        button.textContent = baseText;
      } else if (checkedCount === 1) {
        button.textContent = `${baseText} + 1 subsection`;
      } else {
        button.textContent = `${baseText} + ${checkedCount} subsections`;
      }
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
  } catch (error) {
    console.error('Error in form initialization:', error);
  }
});
