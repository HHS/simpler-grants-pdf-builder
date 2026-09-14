# Readability accordion before and after

Captured in headless Chrome at 1280 × 900 on September 14, 2026.
Both views render the actual Django accordion template, repository styles,
and readability JavaScript with identical synthetic metric responses.
These are isolated component previews, not production data.

- `before.png`: template from PR base 9f76194d; six cards when the optional
  sentences-per-paragraph value is available.
- `after.png`: template from implementation commit 425aad98; four Tier 2
  clearance cards in two columns.

Visually checked both images for card count, labels, targets, and layout.
