# Readability panel: remove the Beta tag

Local Chromium verification, November 13, 2026, at a 1100px viewport. The
screenshots show the heading of the readability metrics accordion on the real
Django NOFO edit page, with readability metrics enabled, rendering a synthetic
test NOFO that has an automatic import snapshot. No production data or
services were used.

- [Before, closed](before-closed.png) and [before, open](before-open.png): a
  gold **Beta** tag sits between the heading and the saved-state summary.
- [After, closed](after-closed.png) and [after, open](after-open.png): the tag
  is gone. The saved-state summary ("Last saved Nov 13 automatically on
  import", and "Calculated ·" once open) keeps its spacing from the heading.

The decision is recorded in the [decision log](../../DECISIONS.md#2026-11-13--remove-the-beta-tag-from-the-readability-metrics-panel).
