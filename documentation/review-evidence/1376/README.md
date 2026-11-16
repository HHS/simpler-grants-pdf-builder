# Footer accessibility statement link (#1376)

Issue: [#1376](https://github.com/HHS/simpler-grants-pdf-builder/issues/1376).
PR: [#1377](https://github.com/HHS/simpler-grants-pdf-builder/pull/1377).
Follows [#1343](../1343/README.md), which added the footer link rows.

Captured November 16, 2026 in a local headless Chromium with Playwright, from
Django-rendered `base.html` with repository CSS, using
`tests/js/footer.browser.cjs`. "Before" is upstream `main` at `8b7f3c2f`; "after"
is this branch. The user is a synthetic template fixture, not a live login, so
the support ticket link shows. These are template renders, not a deployed
environment.

## Change

In row 2 ("HHS policies and resources"), the second link changes from
**Accessibility support** (Grants.gov accessibility page) to **Accessibility
statement** (HHS Digital Accessibility Statement). Position, styling, external
link icon and the visually hidden " (opens in a new window)" text are unchanged.
The rationale is in the [decision log](../../DECISIONS.md#2026-11-16--link-the-footer-to-the-hhs-digital-accessibility-statement),
and the current pattern is in
[UI Patterns](../../UI_PATTERNS.md#hhs-footer-identifier-and-link-rows).

| Width | Before | After |
| --- | --- | --- |
| 1280px | [before-footer-1280.png](before-footer-1280.png) | [footer-1280.png](footer-1280.png) |
| 768px | [before-footer-768.png](before-footer-768.png) | [footer-768.png](footer-768.png) |
| 320px | [before-footer-320.png](before-footer-320.png) | [footer-320.png](footer-320.png) |

## Validation

- `tests/js/footer.browser.cjs` passes on this branch for signed-in and
  signed-out Builder and Readability Checker footers at every width it checks.
  It was run with the bundled Playwright Chromium instead of the `chrome`
  channel, writing screenshots outside the repository so the #1343 captures
  were not overwritten; the images here were then copied in.
- `nofos/bloom_nofos/tests_bloom_nofos/test_footer.py` passes, checking each
  footer link's text and URL.

## Limitations

The link destination was not checked in a deployed environment. A screenshot
does not show the `href`; the Python test covers it.
