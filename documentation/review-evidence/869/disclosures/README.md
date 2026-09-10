# Collapsible monthly data

September 10, 2026. Screenshots use the actual Django dashboard template and
repository styles rendered locally in Chrome with 12 synthetic months
(September 2026–August 2027) and a fictional reviewer account. These are not
production metrics. The history explanation belongs to PR #874 and is not
included in this PR's template.

- [Closed by default](closed.png): six compact “View monthly data” disclosures.
- [Expanded](expanded.png): the first two tables open independently; definitions
  remain visible outside the disclosures.
- [Print styles](print.png): all six monthly tables automatically expanded.
- [Mobile](mobile.png): 375px viewport with the first table expanded.

Verification:

- All 17 JavaScript tests passed, including six dashboard tests covering existing
  zero/missing observations, 12-row disclosures, and repeated print events with
  restoration of mixed open/closed states.
- Chrome verified six initially closed disclosures, all 72 table rows,
  pointer/Enter/Space toggling, independent opening, print expansion, state
  restoration, card bounds at 320/375/768px, and no JavaScript errors.
- Generated an actual three-page A4 PDF through Chrome with five tables initially
  closed. Extracted text contains all six table captions and final-month rows;
  the page's prior disclosure state was restored afterward.
- The print screenshot is a continuous print-media view, not PDF pagination.
  Verification used a rendered fixture page, not a live authenticated database or
  a screen-reader session. No backend code changed or Django test suite rerun.
