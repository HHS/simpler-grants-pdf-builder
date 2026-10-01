# Saved readability checkpoints: local verification

Synthetic local NOFO and users only. No production records, provider exports,
shared feature flags or deployment changes.

## Browser evidence

- `panel.jpg`: deliberate save, recent checkpoints and improved-metric summary.
- `history.jpg`: both saved revisions, provenance and comparison values.
- `overview.jpg`: cross-agency Metrics viewer sees latest saved results.
- `mobile.jpg`: 390px viewport; wide table scroll stays within the table region.
- `history-print.png`: browser print output after correcting clipped columns.

Root exercised calculation-only, first save, repeated save, subsection edit,
new calculation/save, saved detail and full-history navigation. A separate
agent verified cross-agency read-only access, denied editor access, native
disclosure keyboard operation, horizontal keyboard scrolling and mobile layout.
Chrome print exports were rendered and inspected; native print-dialog interaction
and screen-reader speech were not verified.

## Automated checks

- Full Django suite: 2,273 tests passed, 2 skipped.
- JavaScript suite: 42 tests passed.
- PostgreSQL 17.5: 33 focused checkpoint/history/overview tests passed.
- Real two-thread probes: concurrent saves produce one checkpoint; a committed
  edit during save causes stale-save rejection.
- Migration drift and diff whitespace checks passed.
- Independent code review found no production blocker. Its incremental review
  caught a stale test fixture, which was corrected and passed in the full suite.

Local runtime: existing `codex-word-882:sep30` image, Django 6.0.8,
`hhs-nofo-metrics` 0.5.4. CI must validate the current locked dependency build.
The existing non-atomic child-edit/parent-revision sequence remains a limitation;
this change does not promise document-wide snapshot isolation.

The implementation preserves Builder's current six history metrics and supported
target operators. The issue's characters-per-word range example is not implemented.
