# Temporary dev candidate without PR #1143

This branch starts at NOFO Builder 3.52.3
(`60f1b5e2c73f3bba2d22eb7cdd306f17c7d874a8`) and reverts only the
code/documentation introduced by [PR #1143](https://github.com/HHS/simpler-grants-pdf-builder/pull/1143)
(`33552ed202e8f5e611e864d162cfa0dfcacff8b9`). Other changes in 3.52.3
remain included. This is a temporary deployment candidate, not a new numbered
release or a confirmed fix for the timeout. The existing 3.52.3 changelog and
version metadata are retained; identify this candidate by branch or exact SHA.

Related investigation: [simpler-grants-gov #12845](https://github.com/HHS/simpler-grants-gov/issues/12845).

## Behavior

- Restore the previous NOFO, Composer and Writer history reader and formatting.
- Remove the new audit projection models, write hooks, migrations 0154/0155,
  and catch-up command from this candidate.
- Restore previous history performance and limitations, including the lack of
  #1143's indexed pagination and improved retention of deleted-object history.
- Keep original audit events. Do not run reverse migrations or drop any lookup
  tables already created by an earlier deployment. Normal forward migration
  with this branch does not explicitly unapply the absent migrations.

## Dev deployment

No deployment is performed by preparing this branch or opening its draft PR.
Do not merge this temporary revert into main without a separate decision.

1. Confirm that the original migration task has finished or has been safely
   handled. A failed workflow wait does not stop the task; do not overlap it
   with another migration. If task status cannot be established, resolve that
   prerequisite through the deployment workflow/maintainer before retrying.
2. In [Deploy NOFOs](https://github.com/HHS/simpler-grants-gov/actions/workflows/cd-nofos.yml),
   keep the workflow branch at main, choose **dev**, and enter
   `codex/dev-without-history-1143` (or its reviewed exact commit SHA) in
   **git reference to deploy**. This is a branch in the PDF Builder repository.
3. Confirm CI, image scans, migrations and application rollout succeed. Record
   the resolved application SHA and migration duration.
4. Check dev health and the retained import fixes, editor table-point formatting,
   and NOFO/Composer/Writer history access. Long-history performance returns to
   the earlier behavior; success does not validate #1143's improvements.

Production deployment is outside this candidate's scope. A successful dev run
would show that this candidate deploys against the database's then-current
state; it would not establish the root cause of the original timeout.

## Returning to the history-index version

Old workers do not maintain the new projection tables. Before restoring the
history-index version, follow the deployment and post-rollout catch-up guidance
in that version's `documentation/DOCUMENT_HISTORY.md`. Do not fake-apply 0155
or assume a partially completed backfill is complete. Coordinate the change
with the investigation in #12845.

## Validation

Local validation on October 20, 2026:

- Full Django suite: 2,695 tests run, no failures (3 existing skips).
- JavaScript suite: 57 tests passed.
- Migration drift check: no model changes detected.
- Changed Python files pass Black and isort; whitespace checks pass.
- Synthetic SQLite compatibility check: apply reference migrations 0154/0155,
  insert a projection sentinel, then run this candidate's migration plan and
  forward migrate. The candidate plans no operations; all tables, the sentinel,
  and both migration records remain intact. This does not establish PostgreSQL
  behavior or the actual state of dev's database.
- The code files restored by the revert match #1143's parent versions. Other
  3.52.3 application changes remain unchanged.
- Repository-wide `make lint` is blocked by pre-existing isort formatting in
  untouched `nofos/nofos/tests_nofos/test_policy_language.py`; its content matches
  release 3.52.3. No unrelated formatting changes were made.

GitHub CI and any later dev deployment are separate checks; see the draft PR
for their status.
