# PR 983 Word custom endnote marker evidence

These screenshots show the endnote import regression reported from the attached
Announcement Module Word document. They were captured in Chrome on September
28, 2026 from two locally running NOFO Builder revisions, using the real Django
editor view, templates, static styles, navigation, tabs, and warning analysis.

The local records reproduce the exact imported heading text, native endnote
link, duplicate custom marker, citation, and opportunity location involved in
the issue. Complete PDF metadata was supplied so unrelated metadata warnings do
not obscure the endnote behavior.

- `before.png` uses upstream `main`. It shows Mammoth's prior output: a linked
  native `[1]` followed by an unlinked `[1]`. The real Review endnotes tab is
  expanded and displays the resulting conflict and numbering warnings.
- `after.png` uses the PR branch. It shows the same editor and document content
  with one linked `[1]` and the native citation relationship preserved. The
  endnote analyzer returns zero issues, so the Review endnotes warning area is
  absent.

These are local application screenshots, not deployed-environment screenshots.

Automated coverage constructs a real DOCX containing
`w:endnoteReference w:customMarkFollows="1"`, verifies Mammoth's duplicated
nested-superscript HTML, runs the shared import pipeline, and asserts that the
stored content has one marker and no endnote warnings.
