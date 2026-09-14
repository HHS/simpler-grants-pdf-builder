# Metrics dashboard review fixes

Local browser verification, September 8, 2026. Screenshots use the Django-rendered
dashboard template and repository styles in Chrome, with synthetic September–November
data substituted into the dashboard JSON. They are not production or dev metrics.

- [Desktop](desktop.png): all-zero series have no positive-height bars; missing
  observations remain distinct from zero in the monthly-value tables.
- [Mobile, 320px viewport](mobile.png): dashboard cards and tables fit the viewport.
- [Print-media view](print.png): monthly values remain visible without tooltips.
  This checks browser print styles, not PDF pagination.

Automated browser assertions checked zero-height bars, omitted null bars, all 18
historical table rows, table visibility under print styles, dashboard bounds at
320/375/768px, and no JavaScript errors. The shared footer still extends 8px beyond
the 320px viewport; that existing shared-layout issue is outside this dashboard fix.

Regression tests: `node --test tests/js/builder_metrics.test.cjs` (4 passing).
Django metrics and supplemental permission/query checks: 8 passing.
The browser check uses a rendered page with fixture data, not a live authenticated
server or a screen-reader session.
