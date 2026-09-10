# OpDiv filter review evidence

Captured September 10, 2026 in local Chrome against the running Django app and an
isolated SQLite database. A fictional metrics-viewer account and 12 months of
synthetic CDC, NIH, and ACF records exercise the actual HTML/JSON view and query
layer. The local clock is fixed at August 12, 2027 so all sample months appear.
These are not dev or production records.

- [All OpDivs](all-opdivs.png): default filter, above the monthly summary.
- [CDC applied](cdc.png): same dashboard updated without navigation.
- [CDC print styles](cdc-print.png): applied OpDiv label and all monthly tables.
- [CDC mobile](cdc-mobile.png): 375px viewport with one table expanded.

Validation:

- Full Django suite: 1,920 tests passed (SQLite).
- PostgreSQL: all 25 metrics/history/filter tests passed with fresh migrations.
- All 17 JavaScript unit tests passed; migration drift and whitespace checks passed.
- `tests/js/metrics_opdiv.browser.cjs` checked nine dropdown choices, 72 monthly
  rows, actual filtered JSON updates without a document navigation, URL reload,
  failure/retry preserving applied results, an empty agency, keyboard disclosure
  opening, responsive bounds at 320/375/768px, print expansion/restoration, and
  no JavaScript errors. Set METRICS_URL, METRICS_COOKIE_FILE (local Playwright
  cookie JSON), CHROME_PATH, and make Playwright available to Node to rerun with
  the same 12-month synthetic dataset and a metrics-viewer session.
- An actual three-page A4 PDF contains the applied CDC label, all six monthly
  table captions and final-month rows, despite an unapplied NIH dropdown choice.
  The PNG shows continuous print styles, not PDF pagination.

This does not claim a manual screen-reader audit. The historical attribution
baseline and deployment instructions are in documentation/BUILDER_METRICS.md.
