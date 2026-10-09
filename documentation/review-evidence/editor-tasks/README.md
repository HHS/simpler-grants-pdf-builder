# Editor task validation

October 9, 2026. Documentation-only change; no application behavior changed.

## Source review

Reviewed the task labels, navigation, status restrictions, converter behavior,
and table-size rules against Builder code. Browser checks used checkout
036d6684 with a separate SQLite database and synthetic NOFO. Cross-checked
relevant controls and redirect behavior against upstream main at 9d468df2.

## Browser checks completed

- Opened a subsection from the NOFO edit page.
- Renamed it, enabled callout/page-break settings, saved, and confirmed the
  return to the NOFO edit page and persistence after reopening. Heading ID
  remained unchanged.
- Expanded Other actions, opened Add subsection, entered a name, selected H3,
  entered synthetic text, saved, and confirmed the new subsection in the table.
- Opened Configure section, enabled full-width tables, reloaded, and confirmed
  the setting persisted.
- Opened deletion confirmation, verified Yes, delete it wording, and cancelled.
  Final deletion was not submitted.
- Filled author, subject, and keywords; saved and confirmed displayed values.
- Used Find & Replace search and checked result labels. Final replacement and
  deselection behavior were not validated; an automated deselection attempt
  did not change the checked state.
- Opened the subsection Preview tab and confirmed the Markdown table rendered
  with column headers and ordinary data cells.

Read-only inspection of production Builder 3.50.1 confirmed the edit page's
PDF controls and the notice that downloading saves a readability snapshot.
Source review confirmed successful PDF generation records an audit event;
finished downloads also save or reuse a readability snapshot. Neither PDF
action was submitted in production. No production records were edited.
No email attachments or production document content are included in this PR.

[subsection-controls.png](subsection-controls.png) shows synthetic test content only.

## Remaining validation

PDF preview/download are disabled on localhost and require the configured PDF
service. No external PDF service was called. Complex HTML table repair/splitting,
actual cut-and-paste subsection splitting, cover upload/removal and alt-text
saving, theme saving, bulk page-break removal, external-link checking, endnote
repair, and all status/group combinations were not exercised end to end.
These tasks are documented as source-reviewed rather than fully UI-verified.

Support instructions direct teams to their grants policy office first, with
SimplerNOFOs as the fallback. Caption guidance accepts a descriptive nearby
heading with no mandatory Table: prefix. Complexity is treated as a contextual
review prompt rather than an automatic demand to remove every merged cell.
