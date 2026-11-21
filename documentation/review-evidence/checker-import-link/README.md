# Readability Checker link on the NOFO import page

Captured November 21, 2026 in Chrome against the local app with a synthetic,
signed-in user and the Checker enabled. The [before](before.png) screenshot
uses upstream main at `e3d34504`. The [after](after.png) screenshot uses
`codex/checker-link-on-import` and shows the slim informational alert above
the upload field.

Both screenshots show the same page and interaction state at a desktop
viewport. A separate browser check at 390 pixels confirmed that the page
fit without horizontal scrolling and the link opened the Checker.

See the [UI pattern](../../UI_PATTERNS.md#readability-checker-upload-notice)
for the alert markup and placement.
