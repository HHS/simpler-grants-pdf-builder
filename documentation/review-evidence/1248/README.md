# #1248 — Passive sentence comparison MVP

Tested current in-place submission and interaction captures: 23db532b.

Earlier prototype revisions:
Tested MVP implementation: b976df33cfb20009f0caa62fb71e8dc70fe7ce99.
Tested shared-form UI and full-page interaction captures: b09834c2.
Before baseline: db661721 (upstream main).
This evidence update changes documentation only.

## Current workflow and downloadable screenshots

1. A reviewer analyzes a Word upload in the Readability Checker.
2. On that report, they enter only **Microsoft Word for Windows passive sentences (%)**
   for the same whole-document copy, then select **Save comparison**.
3. The comparison saves in the background, without reloading the document.
   A slim success message appears beside the form; the field becomes read-only
   and the button reads Saved. No other Builder form changes.
4. Authorized metrics viewers can open the saved comparisons and difference chart.

| Capture | Caption |
| --- | --- |
| [Before Readability Checker report](before-checker-report.png) | Original ephemeral report without comparison entry. |
| [After full report](after-checker-save-action.png) | Completed report with the inline comparison section and retention notice. |
| [Populated percentage entry](after-inline-percentage-entry.png) | Full report with an invented 3.3% value, ready to submit. |
| [Invalid percentage](after-percentage-validation-error.png) | Full report after entering 101: red inline field error, preserved report and retry action. |
| [Saving in place](after-comparison-saving.png) | Full report while the background save is pending; duplicate submissions are blocked. |
| [Network failure](after-comparison-network-error.png) | Full report with retry guidance, preserved percentage and no navigation. |
| [Saved confirmation](after-inline-saved-confirmation.png) | Full report with the shared slim success message after background saving. |
| [No-JavaScript fallback](after-no-javascript-fallback.png) | Normal form submission reloads the report and uses the existing larger fixed success alert. |
| [Full report after saving](after-saved-confirmation.png) | Same report after saving; no separate investigation page. |
| [Before usage overview](before-usage-overview.png) | Existing usage page before peer navigation. |
| [After usage overview](after-usage-overview.png) | Default usage reporting with shared metrics text-link navigation. |
| [Difference over time](after-difference-over-time.png) | Individual signed differences, zero reference and accessible chart-data disclosure. |
| [Populated comparison page](after-populated-comparisons.png) | Chart and newest-first table with full product names, calculation versions and unavailable values. |
| [Expanded calculation version](after-calculation-version-details.png) | Full comparison page with the shared Metrics v[number] / View details disclosure open. |
| [Expanded chart data](after-chart-data-expanded.png) | Full comparison page with View chart data open, showing all plotted values. |
| [Narrow comparison page](after-comparisons-mobile.png) | Responsive navigation/chart and focusable scrolling table. |

## Synthetic setup

These are actual implementation renders, not mock-ups. A fresh isolated SQLite
database was migrated locally. An invented reviewer received the Readability
Checker, comparison-save and metrics-view permissions. Both relevant Constance
flags were enabled.

The analyzer was replaced only in this capture environment with a fixed,
content-free synthetic report. The browser used the real multipart report route,
percentage form and background save POST, with controlled transport interception
for pending and connection-failure states. A separate JavaScript-disabled browser
context exercised the normal-submission fallback. All filenames, accounts, percentages and save dates
are invented. Seven seeded comparisons span October 23–29, 2026, including
positive and negative differences and an unavailable Readability Checker result.
Package/profile labels use the implemented measurement identities; the invented
measurements do not validate classifier accuracy or Microsoft Word for Windows.

Before images render the unchanged baseline templates with a controlled report
context. After images use the implemented templates, models, forms and routes.
Chrome viewport: 1440 × 1080 CSS pixels, device scale 1; narrow capture: 390 × 844.
The current PR embeds full-page PNGs for entry, pending save, validation,
connection failure, saved confirmation, the populated comparison page and both
expanded disclosures. The no-JavaScript completion is captured separately. A standalone chart
crop remains available as supplementary evidence, not the PR's main chart image. No real document text, credentials, cookies or desktop content appears.

## Validation

- Current in-place revision: 73 affected Django tests and 67 JavaScript tests
  pass. Browser checks verify stable document/URL/scroll, validation, pending
  duplicate prevention, network retry, saved read-only state and normal no-JS
  completion. The following broader results predate the transport change.

- 106 focused Django tests pass, including real Word/PDF analysis, report saving,
  owner/permission isolation, tampering, expiration, CSRF, default-off/live
  enablement, bounds/finite-value validation, retry-safe saving, distinct runs,
  missing/zero values, signed trend arithmetic, single/empty series, chronological
  ordering, all-record chart data independent of table pagination, version details,
  admin permissions and legacy redirects.
- Migration drift and formatting/import hooks pass.
- Desktop and narrow renders checked. Title typography matches existing metrics:
  Merriweather Web, 31.2px, weight 700. Navigation receives keyboard focus;
  fields have labels, the shared success component uses role=alert, tables have scoped headers,
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


## Form-pattern review

Compared the import/upload error pattern, the NOFO short-name form, and shared
success notifications on the NOFO index/edit pages. The final form directly
reuses _text_input.html and includes/alerts.html. The browser capture verifies
a full page navigation on invalid and successful POSTs, red error focus/recovery,
and no repeat analysis-ready modal. No save request is intercepted with AJAX.

After this review, 73 affected Django tests, 6 shared-form tests and 61 JavaScript
tests pass. The full-suite result above predates this small UI component review.


## Numeric-control follow-up

The percentage entry now uses the shared field component's native NumberInput
variant, with increment/decrement controls in 0.1-point steps. Server validation
and shared success feedback remain unchanged. Fifteen comparison/shared-form
tests pass. Browser capture verified ArrowUp changes 3.3 to 3.4 and ArrowDown
returns to 3.3, followed by a successful submission. Full-page entry/error/saved
captures were refreshed; the populated-entry capture shows the hovered control.


## Compact success-feedback review

The existing NOFO readability panel provides text-only “Snapshot saved.” feedback
for asynchronous saving. This report continues to use a normal POST/reload, with
the shared alerts component's optional slim success variant: no separate heading,
just “Comparison saved.” and the entered percentage. Existing alert callers
retain their current appearance. Full-page success captures were refreshed. All 23 affected comparison, readability-history and shared-form tests pass.


## Expanded chart-data layout review

The expanded data now uses a compact, unbordered date/value definition list,
matching the metrics landing page's View monthly data text size and spacing.
Document names appear beneath dates. There is no nested table in the disclosure;
the separate saved-results table remains below the chart. The full-page expanded
capture has been refreshed. Fifteen comparison/metrics tests pass, including a
check that the disclosure contains no table and includes every plotted value.


## Page hierarchy review

The comparison page now has its own **Passive Sentence Comparisons** H1 and
**Back to Readability Checker Usage** back link. The usage page contains one
related-page link, **Passive Sentence Comparisons**; the former peer navigation
is removed. Full-page default and expanded-state captures reflect this hierarchy. All 32
affected comparison/usage/metrics tests pass, including the H1, back-link target
and single-link navigation assertions.


## Consistent numeric-control captures

The initial, populated and invalid entry states all render the same native
type=number input (0–100, arrow steps of 0.1). Chrome can hide the arrows when the
pointer leaves the field, making an idle number input look like a text box.
These full-page captures now show the hovered control consistently. The browser
capture checks type=number before and after validation and verifies keyboard
increment/decrement behavior. The populated-field image is captured before the
invalid-submission variation, so it does not show a stale validation error.
No application behavior changed in this screenshot follow-up.


## Sentence-case follow-up

The comparison H1 and navigation link use **Passive sentence comparisons**.
The back link reads **Back to Readability Checker usage**: the product name
retains its capitals, while “usage” is lowercase. Comparison-page captures and
the full usage-page capture were refreshed; the PR displays the latter directly
so the single comparison navigation link is visible without opening a gallery.


## In-place comparison submission supersedes the reload prototype

The current comparison form saves through a background POST without document
navigation. Slim success feedback is reserved for this small in-place step.
Normal reload/navigation completion uses the existing larger alert; the
no-JavaScript fallback follows that pattern. No other form's behavior changed.
Earlier notes describing a POST/reload prototype are historical and superseded.

Capture checks preserve the report DOM node, URL and scroll position during
validation and successful saving, verify duplicate prevention while saving,
and exercise network-error retry. Updated full-page captures include pending,
validation, network-failure, saved, and no-JavaScript fallback states.


Final in-place submission checks: 73 affected Django tests and 67 JavaScript
tests pass. Browser checks confirmed no document navigation or scroll jump during
validation and success, a single pending request despite repeat submission,
safe retry after a dropped connection, a read-only saved value, and the larger
success alert in the no-JavaScript fallback.
