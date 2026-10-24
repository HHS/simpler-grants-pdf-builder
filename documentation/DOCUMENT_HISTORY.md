# Bounded document history

Issue [#1142](https://github.com/HHS/simpler-grants-pdf-builder/issues/1142).

## Why this changes

The old history page searched serialized subsection snapshots across the audit
table, loaded a document's entire history, filtered and sorted it in Python,
then displayed 25 events. Every Load More request repeated that work. Row
formatting fetched related objects individually, and the page computed full HTML
comparisons merely to decide whether to show links.

History can use an indexed projection of existing audit events after an explicit
post-rollout cutover. The default `DOCUMENT_HISTORY_INDEX_ENABLED=False` retains
the legacy reader until the index has been populated and checked. The original
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

1. Keep `DOCUMENT_HISTORY_INDEX_ENABLED=False` (the default). Apply migrations
   `0154` and `0155`: 0154 creates the small lookup-table schema; 0155 now has
   **no operations**, so deployment never scans the historical audit table.
   The original migration identities and dependencies are retained for databases
   where the earlier deployment applied 0154 or both migrations before #1166's
   application rollback. Django skips already recorded migrations. Do not fake,
   delete or reverse those records, or drop existing projection tables.
   Retiring 0155's data operation is intentional: it changes no model state,
   and the separate repeatable command replaces that deployment-time work.
2. Complete application rollout and let all old workers stop. Old workers do not
   maintain the projection. New workers maintain it even while indexed reads
   are disabled. The legacy reader remains available during the backfill with
   its existing performance and deleted-event limitations.
3. In that environment and database, run from `nofos/`:

   ```sh
   poetry run python manage.py backfill_document_audit_index --chunk-size 100
   ```

   Run **one** backfill job at a time, outside the deployment/migration task.
   Stop it if database load affects users; rerun it later to fill missing rows.
   It is idempotent and bounded in memory, but is not a checkpointed job: a rerun
   scans historical events again. Its duration and storage grow with the audit
   log. Measure duration/load on dev before production; a smaller chunk size
   bounds write batches but does not guarantee low database load.
   It fills missing rows and
   reports resolved events and unresolved ownership. It scans historical events
   outside HTTP requests, not on page loads. It is not a scheduled requirement
   for normal new-worker writes. `--database` selects a configured database alias.
4. Investigate unresolved ownership before signing off on completeness. Malformed
   snapshots with no live object or usable retained parent cannot safely be
   assigned. Originals remain stored; the index never guesses ownership from
   arbitrary text. Counts contain no document bodies.
5. Run `poetry run python manage.py backfill_document_audit_index --check`.
   This read-only anti-join checks that **every relevant original event** has
   a projection row; missing rows cause a nonzero exit and must be investigated.
   It does not inspect or repair payloads. Do not delete original events or
   ignore unresolved records to make it pass. Old workers or bulk writers can
   invalidate completeness; stop/coordinate them before the final check.
6. Only after a successful check, set `DOCUMENT_HISTORY_INDEX_ENABLED=True` in
   that environment and roll application workers. Do not combine initial schema
   rollout and indexed-read enablement. All workers in this second rollout
   maintain the projection. No new permission or data access is introduced.
7. Validate the production example in #1142: first page and Load More, deleted
   events, access restrictions and the roughly two-second target. Inspect the
   PostgreSQL plan for `document_audit_page_idx`. Local SQLite timings do not
   establish production PostgreSQL performance.

For read-path rollback, set `DOCUMENT_HISTORY_INDEX_ENABLED=False` and roll
workers. Live index maintenance remains active; the legacy reader returns with
its old performance/deletion limitations. If rolling application code back to
#1166, rerun backfill/check before a future cutover, because those old workers
do not maintain the projection. Added lookup tables can remain
unused; originals are unaffected. Do not drop tables while new workers use them.
Rebuilding the projection requires backfill and a completeness check.

## Verification

`test_history_pagination.py` checks SQL LIMIT/lookahead, non-overlapping pages,
constant warmed query counts for one versus 25 rows, no HTML diff work,
excluded-event pagination, document/group isolation and deleted objects.
`test_history_index.py` checks live/cascade hooks, Composer/Writer ownership,
frozen migration recovery, unresolved records and post-rollout catch-up.
Existing audit/history tests remain applicable.

Restoration tests also check default-off reads with an empty projection,
read-only completeness failure/success, and the absence of operations in 0155.
The original frozen migration helper remains as historical reference and a
recovery test fixture; it is not executed by `migrate`.

See [local evidence](review-evidence/bounded-history-1142/README.md). No production
data is published.
