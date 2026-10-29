# #1248 — Passive sentence comparison MVP

Tested implementation: b976df33cfb20009f0caa62fb71e8dc70fe7ce99.
Before baseline: db661721 (upstream main).
This evidence update changes documentation only.

## Current workflow and downloadable screenshots

1. A reviewer analyzes a Word upload in the Readability Checker.
2. On that report, they enter only **Microsoft Word for Windows passive sentences (%)**
   for the same whole-document copy, then select **Save comparison**.
3. A success alert appears on the same report. There is no next entry page.
4. Authorized metrics viewers can open the saved comparisons and difference chart.

| Capture | Caption |
| --- | --- |
| [Before Readability Checker report](before-checker-report.png) | Original ephemeral report without comparison entry. |
| [After full report](after-checker-save-action.png) | Completed report with the inline comparison section and retention notice. |
| [Inline percentage entry](after-inline-percentage-entry.png) | The single field populated with an invented 3.3% value, ready to save. |
| [Inline confirmation](after-inline-saved-confirmation.png) | Saved percentage and signed difference shown in a standard success alert. |
| [Full report after saving](after-saved-confirmation.png) | Same report after saving; no separate investigation page. |
| [Before usage overview](before-usage-overview.png) | Existing usage page before peer navigation. |
| [After usage overview](after-usage-overview.png) | Default usage reporting with shared metrics text-link navigation. |
| [Difference over time](after-difference-over-time.png) | Individual signed differences, zero reference and accessible chart-data disclosure. |
| [Populated comparison page](after-populated-comparisons.png) | Chart and newest-first table with full product names, calculation versions and unavailable values. |
| [Expanded calculation version](after-calculation-version-details.png) | Shared Metrics v[number] / View details disclosure. |
| [Narrow comparison page](after-comparisons-mobile.png) | Responsive navigation/chart and focusable scrolling table. |

## Synthetic setup

These are actual implementation renders, not mock-ups. A fresh isolated SQLite
database was migrated locally. An invented reviewer received the Readability
Checker, comparison-save and metrics-view permissions. Both relevant Constance
flags were enabled.

The analyzer was replaced only in this capture environment with a fixed,
content-free synthetic report. The browser used the real multipart report route,
percentage form and save POST. All filenames, accounts, percentages and save dates
are invented. Seven seeded comparisons span October 23–29, 2026, including
positive and negative differences and an unavailable Readability Checker result.
Package/profile labels use the implemented measurement identities; the invented
measurements do not validate classifier accuracy or Microsoft Word for Windows.

Before images render the unchanged baseline templates with a controlled report
context. After images use the implemented templates, models, forms and routes.
Chrome viewport: 1440 × 1080 CSS pixels, device scale 1; narrow capture: 390 × 844.
Full-page PNGs are complemented by focused captures of the entry, success alert
and chart. No real document text, credentials, cookies or desktop content appears.

## Validation

- 106 focused Django tests pass, including real Word/PDF analysis, report saving,
  owner/permission isolation, tampering, expiration, CSRF, default-off/live
  enablement, bounds/finite-value validation, retry-safe saving, distinct runs,
  missing/zero values, signed trend arithmetic, single/empty series, chronological
  ordering, all-record chart data independent of table pagination, version details,
  admin permissions and legacy redirects.
- Migration drift and formatting/import hooks pass.
- Desktop and narrow renders checked. Title typography matches existing metrics:
  Merriweather Web, 31.2px, weight 700. Navigation receives keyboard focus;
  fields have labels, confirmation uses role=status, tables have scoped headers,
  the SVG has a title/description and exact values in View chart data.
  The narrow document has no horizontal overflow outside its table container.
- Full local run: 2,923 tests, 3 skipped, one failure: the Constance admin
  breadcrumb test previously reproduced on unchanged upstream db661721 in this
  environment. No other failure occurred. The final focused run includes two
  additional permission tests. This is not a full-suite-green claim.

## Scope after review

This MVP deliberately removes the original proposal's separate manual-entry page,
review statuses, preparation notes, sentence counts, build fields and correction
history. Those can be added later if needed. It also omits filters, sorting
controls, totals and averages. Readability Checker metadata is retained
automatically; the user enters only one percentage. The chart represents saved
individual differences rather than an aggregate score or a quality threshold.

Earlier investigation-page captures remain in Git history at dbf4dfe9 and are
superseded by the inline-entry and inline-confirmation captures above.

[Operator guide](../../readability/WORD_COMPARISONS.md) covers rollout, permissions,
indefinite retention, deletion and rollback.
[TASK-WORD-COMPARISON](../../EDITOR_TASKS.md#task-word-comparison) documents the
current user workflow. No import transformation or metric formula changes apply.
