# CMS theme selection on import

Captured November 3, 2026 for [PR #1277](https://github.com/HHS/simpler-grants-pdf-builder/pull/1277) in a local Builder instance using headless Chromium.

Run new-import metadata suggestion with a synthetic CMS OpDiv and a placeholder opportunity number. Compare the theme selector from upstream baseline `afb3b595` with the selector from PR commit `5a03ec7b`. Save each result to a local draft and capture the same **NOFO theme options** panel on the editor page.

- [Before](before.png) shows NIH (Light) and its suggested Text only cover.
- [After](after.png) shows CMS (Light) and its suggested Standard image cover.

The capture exercises metadata suggestion and the editor display. It uses synthetic input and a local database. See [IMPORT-042](../../IMPORT_RULES.md#import-042--cover-theme-suggestion) for the theme selection rule.
