# PR 983 Word custom endnote marker evidence

These screenshots show the endnote import regression reported from the attached
Announcement Module Word document. They were rendered locally in Chrome on
September 28, 2026 from the exact imported heading text, native endnote link,
duplicate custom marker, and warning messages involved in the issue.

- `before.png` shows Mammoth's prior output: a linked native `[1]` followed by
  an unlinked `[1]`. The manual-endnote analyzer consequently reports the two
  warnings shown in NOFO Builder.
- `after.png` shows the corrected output: one linked `[1]`, with the native
  citation relationship preserved. The analyzer returns zero issues.

The layout is a focused local regression-evidence view using NOFO Builder's
visual language, not a deployed-environment screenshot. The green analysis
result in `after.png` makes the verified zero-issue result visible; the normal
editor simply omits the endnote warning panel when there are no issues.

Automated coverage constructs a real DOCX containing
`w:endnoteReference w:customMarkFollows="1"`, verifies Mammoth's duplicated
nested-superscript HTML, runs the shared import pipeline, and asserts that the
stored content has one marker and no endnote warnings.
