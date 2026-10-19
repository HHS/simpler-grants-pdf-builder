# Bounded document history

Issue [#1142](https://github.com/HHS/simpler-grants-pdf-builder/issues/1142).

## Why this changes

The old history page searched serialized subsection snapshots across the audit
table, loaded a document's entire history, filtered and sorted it in Python,
then displayed 25 events. Every Load More request repeated that work. Row
formatting fetched related objects individually, and the page computed full HTML
comparisons merely to decide whether to show links.

History now uses an indexed projection of existing audit events. The original
`easyaudit.CRUDEvent` records and payloads remain unchanged. The shared NOFO,
Composer and Writer history view all use this path, without new UI components.

## Ownership and queries

- `AuditObjectDocument` records object content type/UUID and owning document
  content type/UUID. It survives section/subsection deletion. Root content type
  distinguishes Composer and Writer, which share child model types.
- `DocumentAuditEvent` records original event ID, owning document, timestamp
  and visibility. Its partial composite index covers visible events for one document in
  descending timestamp/event-ID order. It copies no document bodies or users.
  Both projections are excluded from easy-audit to prevent recursion.
- The page selects 26 indexed IDs, then loads only those events with users and
  content types. It displays 25 and uses the extra event for Load More. Live
  subsection/section labels are fetched together. Deleted objects retain audit
  descriptions but have no live comparison link.
- Visibility is calculated when indexing, retaining existing exclusions for
  updates to internal fields only. Creates/deletes remain visible.
- Ordering is exact timestamp, then event ID, replacing minute/action grouping.
  Ties are deterministic. Existing offset URLs remain; concurrent new edits can
  shift offsets between requests. This is not snapshot or keyset pagination.
- A changed body gets a comparison link if its live subsection exists and its
  two stored values differ. HTML comparison happens only when opening the link.
  Formatting-only changes may lead to a comparison with no visible diff.
- The modifications report remains an explicit whole-document report: it uses
  indexed ownership but is not a paginated history page.

Event-save hooks maintain the projection; pre-delete hooks preserve ownership
before cascade deletion. Snapshots and retained ownership supply the root after
objects disappear. Bulk event inserts bypass signals and require backfill.

## Migration and deployment

1. Apply migrations `0154` and `0155`. The second is a frozen, non-atomic
   backfill using bounded batches. It recovers section ownership before projecting
   document/section/subsection events. It changes only new lookup tables.
   Its duration and storage grow with the existing audit log; measure on dev
   before production. Empty databases have nothing to backfill.
2. Complete application rollout and let all old workers stop. Old workers do not
   maintain the projection. Catch up events they wrote after the migration scan
   before declaring history validation complete.
3. In that environment and database, run from `nofos/`:

   ```sh
   poetry run python manage.py backfill_document_audit_index --chunk-size 100
   ```

   This bounded-memory command can be repeated safely. It fills missing rows and
   reports resolved events and unresolved ownership. It scans historical events
   outside HTTP requests, not on page loads. It is not a scheduled requirement
   for normal new-worker writes. `--database` selects a configured database alias.
4. Investigate unresolved ownership before signing off on completeness. Malformed
   snapshots with no live object or usable retained parent cannot safely be
   assigned. Originals remain stored; the index never guesses ownership from
   arbitrary text. Counts contain no document bodies.
5. Validate the production example in #1142: first page and Load More, deleted
   events, access restrictions and the roughly two-second target. Inspect the
   PostgreSQL plan for `document_audit_page_idx`. Local SQLite timings do not
   establish production PostgreSQL performance.

For rollback, roll application code back first. Added lookup tables can remain
unused; originals are unaffected. Do not drop tables while new workers use them.
Rebuilding the projection requires backfill and a completeness check.

## Verification

`test_history_pagination.py` checks SQL LIMIT/lookahead, non-overlapping pages,
constant warmed query counts for one versus 25 rows, no HTML diff work,
excluded-event pagination, document/group isolation and deleted objects.
`test_history_index.py` checks live/cascade hooks, Composer/Writer ownership,
frozen migration recovery, unresolved records and post-rollout catch-up.
Existing audit/history tests remain applicable.

See [local evidence](review-evidence/bounded-history-1142/README.md). No production
data is published.
