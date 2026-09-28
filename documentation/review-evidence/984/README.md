# PR 984 ACF alignment list evidence

These screenshots were captured in Chrome on September 28, 2026 from two
locally running NOFO Builder revisions using the real Django import and editor
views, templates, and static styles. Both applications imported
`HHS-2026-ACF-ACYF-AP-0003_For Design_07.01.2026.docx` through the standard
NOFO upload form.

- `before.png` uses upstream `main`. The three ordered-list groups restart at
  1, producing visible numbering of 1; 1–2; and 1–3.
- `after.png` uses the PR branch. IMPORT-052 recognizes the Word export's
  nested heading and ordered-list structure, assigning starts of 1, 2, and 4
  so the visible sequence continues from 1 through 6.

The source wording, links, emphasis, headings, and intervening paragraphs are
unchanged.
