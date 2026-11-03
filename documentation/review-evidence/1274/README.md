# NOFO Group dropdown comparison

Captured November 3, 2026 for [issue #1274](https://github.com/HHS/simpler-grants-pdf-builder/issues/1274) and [PR #1275](https://github.com/HHS/simpler-grants-pdf-builder/pull/1275).

- [Before](group-dropdown-before.png) shows the PR base revision `07703b0b` with Bloom and All.
- [After](group-dropdown-after.png) shows the PR branch with the configured groups and All.

Both images were captured in Chrome on macOS against local Django instances. To reproduce, sign in with a synthetic Bloom account, open the in-progress NOFO list, and open **NOFO Group** with Bloom selected. The screenshots use the same synthetic record and crop. Chrome confirmed the label rendered with Source Sans Pro Regular on both revisions. At a 390 CSS pixel viewport, the updated select was checked separately for fit.

These captures describe local UI behavior. See [Editor Tasks](../../EDITOR_TASKS.md#how-to-use-this-page) for current usage instructions.
