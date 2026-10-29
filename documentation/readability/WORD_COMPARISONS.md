# Passive sentence comparisons

The MVP compares passive sentence percentages from the Readability Checker and
Microsoft Word for Windows. It does not change formulas, Builder exclusions,
ordinary usage records or portfolio scores.

## User workflow

On a completed Word-upload report, an authorized user enters one value:
**Microsoft Word for Windows passive sentences (%)** for the same whole-document
copy, using the compact number field with increment/decrement controls. **Save comparison** explicitly retains the completed Readability Checker
result and entered percentage in the background. The page does not refresh.
The action shows **Saving…**. After confirmation, the entry field, label,
helper text, button and expiry notice are replaced by a slim **Comparison saved**
message showing the saved percentage and a permitted results link. Focus moves
to the confirmation without a programmatic scroll. If saving fails, the form
and entered value remain available for correction or retry.
Nothing is saved while typing. A connection failure lets the user retry without
saving the same report twice. An expired report requires analyzing again.
If JavaScript is unavailable, normal submission reloads the report with the
existing larger success alert instead. Invalid values show the shared text-field's red
inline error; correct the value and submit again.
No separate entry or investigation page is required. The percentage is required,
including an explicit zero when appropriate, and must be between 0 and 100.

The saved run automatically records the user and save date. Its Readability Checker
measurements, analysis date, calculation version, input-processing identity and
upload fingerprint remain fixed. Repeated submission for the same run keeps the
first saved comparison. To compare a corrected measurement, analyze and save a new
run; the MVP has no correction/editing interface.

Metrics viewers can open **Readability Checker usage → Passive sentence comparisons**.
The table shows saved results, newest first, with Calculation version / View details
matching saved NOFO readability history. There are no filters or sort controls.

## Difference over time

Each plotted point is one saved paired comparison, dated when saved:
**Readability Checker minus Microsoft Word for Windows**, in percentage points.
A positive difference means the Readability Checker percentage is higher.
Zero means the percentages agree. Negative values mean it is lower.

The chart uses all retained paired comparisons, independently of table pagination.
Unavailable Readability Checker percentages are excluded, never plotted as zero.
A single pair appears as a point; no pairs show an empty state. Exact values are
available in **View chart data** for keyboard and screen-reader access.
The line is not a total, rolling average, quality threshold or proof that the
measurement method is improving: different documents and calculation versions
can change the differences. Inspect calculation details before interpreting a trend.

## Rollout and permissions

1. Apply migration 0160. This feature is unmerged; its initial migration reflects
   the MVP schema. Local reviewers who applied an earlier draft should rebuild
   their disposable comparison database rather than treating it as deployed data.
2. **HHS_NOFO_WORD_COMPARISONS_ENABLED** is a default-off Constance flag and takes
   effect without restarting workers. Authenticated Readability Checker enablement
   and its separate permission remain required to analyze a Word upload.
3. In user admin, grant **Can save passive sentence comparisons** to selected reviewers.
   This grants nofos.manage_word_comparisons, independently of metrics viewing.
   Bloom membership neither grants nor blocks this permission.
4. Grant nofos.view_builder_metrics separately to people authorized to see retained
   document names, scores and the trend chart. Confirm this audience and the
   backup policy before enabling the feature.

Usage remains the default at /nofos/metrics/readability-checker-usage.
The legacy /nofos/metrics/readability-pilot redirects with its query string preserved.

## Retention and deletion

Explicitly saved comparisons have **no automatic expiration**. They are separate
from temporary uploads and ordinary content-free attempt cleanup. No uploaded
DOCX or extracted sentence text is retained. Unsaved reports are not persisted:
a signed, compressed, owner-bound handoff expires after 30 minutes.

Do not log request bodies; the handoff contains report metadata and document name.
Superusers can inspect and delete comparisons in Django admin. Comparisons are
excluded from EasyAudit copying. Database backups have their independent retention;
deletion does not immediately purge backups. Deleting an account leaves the saved
comparison with no user identity.

Disable the Constance flag to hide saving and the comparison page while retaining
data. Keep the migration applied on code rollback; do not use ordinary attempt
cleanup on deliberately retained comparisons.

## Deferred beyond MVP

Manual sentence counts, Microsoft Word for Windows build/version, preparation
notes, same-copy checkboxes, review statuses, correction history and dedicated
investigation/detail pages can be added later if needed. The MVP deliberately
asks only for the passive percentage. The inline instruction asks for the same
whole-document copy; a fingerprint identifies the Readability Checker input but
cannot independently prove which copy was measured in Microsoft Word for Windows.

[Editor task](../EDITOR_TASKS.md#task-word-comparison) ·
[Synthetic screenshots and validation](../review-evidence/1248/README.md)
