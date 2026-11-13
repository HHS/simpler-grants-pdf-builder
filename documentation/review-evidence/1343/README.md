# Footer link rows (#1343)

Issue: [#1343](https://github.com/HHS/simpler-grants-pdf-builder/issues/1343).
Follows [#1240](https://github.com/HHS/simpler-grants-pdf-builder/issues/1240) and
[#1340](https://github.com/HHS/simpler-grants-pdf-builder/pull/1340).

Captured November 13, 2026 in a local headless Chromium with Playwright, from
Django-rendered `base.html` and `pdf_readability_base.html` with repository CSS.
"Before" is upstream `main` at `d1f6644`; "after" is this branch. The user is a
synthetic template fixture (`sample@example.com`), not a live login. These are
template renders, not a deployed environment.

## Change

The footer now has three bands: the HHS identifier, row 1 with Builder links,
and row 2 with HHS policy links like the simpler.grants.gov footer. Privacy policy
moves from row 1 to row 2, and row 2 ends with the HHS Vulnerability disclosure
policy. Both base templates include the shared
`includes/footer.html`; the Readability Checker still omits the support ticket link.
The current pattern is documented in
[UI Patterns](../../UI_PATTERNS.md#hhs-footer-identifier-and-link-rows).

| Width | Before | After |
| --- | --- | --- |
| 1280px | [before-footer-1280.png](before-footer-1280.png) | [footer-1280.png](footer-1280.png) |
| 768px | [before-footer-768.png](before-footer-768.png) | [footer-768.png](footer-768.png) |
| 320px | [before-footer-320.png](before-footer-320.png) | [footer-320.png](footer-320.png) |

Full-page after captures: [320px](after-320.png), [768px](after-768.png),
[1280px](after-1280.png). All captures are signed in with the support ticket link.

## Layout finding

Row 1's four signed-in links need about 760px including gutters. At 640px they
wrapped onto two lines with Back to top alone on the second, so row 1 stays a
column until the USWDS tablet-lg breakpoint (880px). Row 2 wraps naturally and
becomes a row at the tablet breakpoint (640px).

## Validation

- `tests/js/footer.browser.cjs` passes for signed-in and signed-out Builder and
  Readability Checker footers at 320, 375, 480, 576, 639, 640, 768, 879, 880, 1023,
  1024 and 1280px. It checks for no horizontal scrolling, link text and order per row, row
  backgrounds, white link text, column versus row layout at each breakpoint, Back
  to top on the right of row 1, band order and the existing identifier checks.
  It also fails if the keyboard focus ring drops below 3:1, or link text below
  4.5:1, against the identifier band or either row. The USWDS focus color
  `#2491ff` measures 3.97:1, 3.004:1 and 5.00:1 on the three bands, so row 1 has
  almost no margin. A temporary run with row 1 lightened to `#0e4c80` failed at 2.78:1.
  The script launches the `chrome` channel; locally it ran against Playwright's
  bundled Chromium with that option removed.
- `nofos/bloom_nofos/tests_bloom_nofos/test_footer.py` checks link order, URLs,
  `target="_blank"` and the screen reader new-window text on the login page, a
  signed-in NOFO list and the Readability Checker.
- Contrast is calculated from browser-computed colors with the WCAG formula: white
  text is 12.71:1 on the identifier, 9.60:1 on row 1 and 15.98:1 on row 2.
- **Not checked:** screen reader output, a deployed environment, and whether the
  external destinations resolve.

To reproduce, run `node tests/js/footer.browser.cjs` with Playwright available to
Node and `PYTHON` set to the project's Python environment. Before captures used
the same script on upstream `main`, writing to a scratch folder.
