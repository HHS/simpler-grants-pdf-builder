# #1248 — Word passive sentence comparison tracker

Implementation: 2ad8466ad60517babb3d25879c2a4a9fd26eddda.
Admin permission toggle: 34eb3eb4. Evidence commit changes documentation/images only.
Before baseline: db661721 (upstream main).

## Downloadable screenshots

| Image | Caption |
| --- | --- |
| [Before Checker report](before-checker-report.png) | Existing ephemeral Word report, before the save action. |
| [After Checker report](after-checker-save-action.png) | Authorized user sees Save for Word comparison, retention explanation and 30-minute handoff window. |
| [Saved confirmation](after-saved-confirmation.png) | The save action navigates to the retained record URL; status confirmation and manual Word entry are visible. |
| [Before usage overview](before-usage-overview.png) | Existing Readability Checker Usage page before tabs. |
| [After usage overview](after-usage-overview.png) | Default usage reporting with independent comparison navigation. |
| [Populated comparisons](after-populated-comparisons.png) | Filters, both tabs, three review states, signed nonzero differences and missing values. |
| [Word measurements and history](after-word-measurements-and-history.png) | Word percentage field, separate sentence counts, same-copy confirmation, immutable Checker details and investigation notes. |
| [Narrow comparison layout](after-comparisons-mobile.png) | Filters stack; the data table scrolls within its container. |

## Controlled synthetic capture

These are actual browser renders of implementation templates and routes, not
mock-ups. All document names, agency labels, accounts, measurements and review
notes are invented. No real uploaded document, account, Word measurement,
credential or desktop content appears.

A fresh isolated SQLite database was migrated locally. An invented Bloom reviewer
received Checker, metrics-view and explicit comparison-management permissions.
Both authenticated Checker and comparison Constance flags were enabled.
The analyzer was replaced in this capture environment with a fixed, content-free
synthetic report; the upload filename was invented and upload bytes synthetic.
The browser used the real multipart report flow, explicit save POST and detail
redirect. Seeded rows exercise awaiting, ready and reviewed states. Screenshot
data are illustrations, not evidence of classifier accuracy or actual Windows
Word measurements. Comparison detail fingerprints in seeded rows are invented.

Before captures render the unmodified upstream report/usage templates with the
same controlled report context. After captures use the implemented templates,
models, forms and routing. Screenshots were captured in headless Chrome at
1440 × 1080 CSS pixels, device scale 1, with full-page PNGs; the narrow capture
uses 390 × 844. No debug overlay is present.

## Validation

- 95 focused Django tests passed, including metrics/pilot user-admin regressions.
  The worker report-contract tests were rechecked after updating the expected
  safe scope fields to include the actual passive numerator.
- 61 JavaScript tests passed.
- Migration drift check and commit formatting/import hooks passed.
- Feature tests cover signature tampering, owner isolation, expiration, CSRF,
  disabled access, explicit write permission, immutable repeated saves, distinct
  runs, correction history, missing/zero values, validation, filters, database
  sorting, pagination, audit exclusion and legacy query-preserving redirects.
- Desktop and narrow rendering checked. The title computes to Source Sans Pro Web,
  32px, weight 700 in this app's current stylesheet. Navigation can receive
  keyboard focus; labels are associated with inputs, column headers have scope,
  current navigation uses aria-current, and saved confirmation uses role=status.
  The narrow document has no horizontal overflow outside the table container.
- The full local run completed 2,921 tests (3 skipped). It found a Constance
  admin breadcrumb failure plus an old worker-scope expected-field assertion;
  the latter was updated for the added passive numerator and rechecked.
  The identical test fails on unchanged upstream db661721 in the same environment;
  this is not a green full-suite claim. See PR for full-run results.

## Rollout and editor instructions

See [operator guide](../../readability/WORD_COMPARISONS.md) for default-off rollout,
permission assignment, retained-name visibility, indefinite retention, superuser
deletion (including manual revisions), backup caveats and non-destructive rollback.

Editor Tasks updates cover TASK-READABILITY-UPLOAD and the new
[TASK-WORD-COMPARISON](../../EDITOR_TASKS.md#task-word-comparison).
No import transformation or metric formula changes are included.
