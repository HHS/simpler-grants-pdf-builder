# #1432 — Word downloads metrics page

- Issue: [#1432](https://github.com/HHS/simpler-grants-pdf-builder/issues/1432).
  Recording shipped in [#1433](https://github.com/HHS/simpler-grants-pdf-builder/pull/1433);
  these captures are for the follow-up that adds the page and its navigation.
- Captured: November 25, 2026.
- After: commit `3e87bff4` (branch `claude/word-downloads-metrics-page`), later
  rebased onto the #1433 review fixes as `7483109b`. The rebase moved the
  recording switch to Constance and did not change the page markup or styles.
  Before: commit `8297a931` (recording only, before the page existed).
- Environment: local `runserver` with SQLite, `DEBUG=True`,
  `HHS_NOFO_METRICS_ENABLED=true`, `WORD_DOWNLOAD_ATTEMPT_RECORDING_ENABLED=true`,
  Chromium via Playwright, signed in as a synthetic superuser
  (`viewer@example.com`, group `bloom`).
- Data: 597 synthetic `WordDownloadAttempt` rows over 84 days, generated with a
  fixed random seed across the four sources, several OpDivs, public and signed-in
  Checker downloads, and a mix of outcomes. No real usage, documents or people.
- GrabzIt, the clearance export and the readability Word report show as
  Disabled in the availability table because this local environment has no
  GrabzIt credentials or those flags set; that table reports live settings.

| Capture | Caption |
| --- | --- |
| [Before: metrics navigation](before-metrics-navigation.png) | Usage & quality metrics before the change: “NOFO readability metrics \| Readability Checker usage”. |
| [After: metrics navigation](after-metrics-navigation.png) | The link row now reads “Readability metrics \| Readability Checker usage \| Word downloads”. |
| [After: Word downloads card](after-word-downloads-card.png) | New Monthly trends card: successful downloads per month, with a “Review Word downloads” link. |
| [After: Word downloads page](after-word-downloads-page.png) | Full page, All sources / All OpDivs, at 1280 px (captured at 1×). |
| [After: Readability Checker filter](after-word-downloads-checker-filter.png) | Choosing the Readability Checker source swaps the OpDiv filter for the Signed in filter. |
| [After: phone width](after-word-downloads-mobile.png) | iPhone 13 viewport (captured at 1×): filters stack and wide tables scroll sideways. |

Also checked in the browser: from `/nofos/metrics?group=cdc`, the Word downloads
link opened `/nofos/metrics/word-downloads?group=cdc`, and its back link returned
to `/nofos/metrics?group=cdc`.

A screenshot alone does not establish accessibility or production behavior.
Automated coverage is in `nofos/nofos/tests_nofos/test_word_download_metrics_page.py`.
