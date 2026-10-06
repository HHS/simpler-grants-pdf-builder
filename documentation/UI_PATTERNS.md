# UI patterns

Use this guide when adding or changing Builder screens. Start with an existing
component and its behavior before creating a new variation. This is a small,
incremental catalog of verified patterns, not an audit of every screen.

## File-upload errors

Use the shared [`file_input.html`](../nofos/bloom_nofos/templates/includes/file_input.html)
component for a file field's error state. NOFO Compare and the PDF checker are
examples of this pattern.

### What the user sees

- The label and file requirements remain visible.
- The field group has a red left border.
- A bold red `Error: …` message appears between the hint and file picker.
- The file picker has a red dashed border and remains available for correction.
- The submit action remains available so the user can choose another file and retry.

The screenshot below shows the PDF checker's missing-file state. Its blue outline
is keyboard focus on the error message, rather than part of the red error styling.

![PDF checker inline upload error](review-evidence/pdf-upload-errors-1038/inline-error.png)

### Implementation

Pass the user-facing error to the shared include instead of recreating its markup:

```django
{% include "includes/file_input.html" with id="pdf" label="Choose a PDF" hint=upload_hint accept=".pdf,application/pdf" error=error only %}
```

The component adds `usa-form-group--error`, the inline `usa-error-message`,
`aria-invalid="true"`, and an `aria-describedby` reference to the hint and error.
Use a stable, unique field ID. Preserve these associations when customizing a form.

For this server-rendered pattern, do not pass `required=True` if it would make
browser constraint validation intercept an empty submission with a native tooltip.
The server must still validate missing files, file counts, formats, and size;
removing the browser constraint does not make the upload optional.

For the PDF checker, JavaScript focuses the inline error using a temporary
`tabindex="-1"`. Missing-file submissions reach server validation without opening
the processing modal or disabling the submit button. Keep the same error usable
when JavaScript is unavailable.

Write an error that explains the problem and the next action, such as
“Choose one PDF file to analyze.” Avoid raw exceptions or technical diagnostics.
For a single file field, avoid repeating the same message in a separate alert.
A multi-field form may need an error summary linking to its invalid fields; that
pattern is outside this guide's current scope. Operational failures unrelated to
file correction may also need different feedback.

### Verify before shipping

1. Submit without a file: verify the inline error, invalid field association,
   and absence of a competing browser tooltip.
2. Upload a rejected file: verify a useful correction message and no normal result.
3. Use keyboard navigation: verify error focus and that the picker and submit
   action remain usable for retry.
4. Correct the file and resubmit: verify successful processing and cleared errors.
5. Check narrow screens and server validation with JavaScript unavailable.

Useful references:

- [PDF upload page](../nofos/bloom_nofos/templates/pdf_readability.html)
- [PDF interaction behavior](../nofos/bloom_nofos/static/js/pdf_readability.js)
- [PDF page tests](../nofos/bloom_nofos/tests_bloom_nofos/test_pdf_readability.py)
- [Import error codes](IMPORT_ERROR_CODES.md), for blocking NOFO import messages
