# Historical Builder metrics

The six metrics use durable facts rather than joins to currently existing users
and NOFOs. This addresses #873 under #865.

- `MetricsActor` records signup time and signup eligibility, keyed by a random
  UUID. Deleting the account clears its optional link; no name, email, original
  user ID, or audit payload is copied into the fact. This is a pseudonymous
  reference, not a claim that all aggregate activity is anonymous.
- `MetricsActivity` records one eligible actor/month/group, using the application's
  local timezone. Eligibility is the user's group when activity occurs. A later
  move into or out of Bloomworks/staging affects future activity only.
- `MetricsNofo` records the NOFO UUID, creation time, creation eligibility, and
  earliest live PDF timestamp. It has no foreign key to the deletable NOFO.
- `ImportAttempt.metrics_included` freezes import-time user eligibility. Null
  means unknown, which is excluded from both import-quality calculations.

Total users is eligible signups, not the number of currently existing accounts.
Creation counts include subsequently deleted NOFOs. Distinct activity counts
survive account and audit-record deletion. First-PDF duration is grouped by
creation month: a first print in a later month intentionally adds a contribution
to that earlier cohort. Reprints do not replace the first timestamp.

## Baseline and limits

Migration 0137 freezes available users, NOFOs, import attempts and audit events.
It uses current groups because historical group membership is unavailable. It
cannot restore deleted records or earlier unrecorded import failures/warnings.
This is a best-effort baseline, not a complete reconstruction. Unknown import
eligibility is not assumed to be external. Empty import-quality denominators
produce `None` (displayed as “No data”), not zero.

Run migrations with application writes paused during deployment so a creation or
group change cannot race the baseline. The baseline scans historical audit events
and may take time on a large database. Its data step is intentionally irreversible;
do not drop/rebuild facts to refresh a report. Validate backups before deployment.

Normal Django saves capture facts through signals. `bulk_create`, raw SQL, and
fixture loading bypass this capture and require an explicit historical import
procedure. Group updates need no special handling: already captured facts never
read current groups again. Facts are excluded from EasyAudit to avoid duplicating
history or retaining the actor/account link in audit payloads.

There is no scheduled expiration for metric facts. This is separate from log and
backup retention. Deliberate data corrections require a reviewed migration or
management procedure identifying affected facts and the reason; there is no
automatic reclassification or correction interface.

## OpDiv filtering (#886)

The dashboard defaults to All OpDivs and offers the eight agency groups from
`GROUP_CHOICES`, excluding Bloomworks and staging. Changing the dropdown updates all six
metrics in place and stores `?group=cdc` (for example) in the URL. Both HTML and
JSON responses require the existing metrics-viewer permission. Invalid/internal
group values are rejected. The applied group label appears only in print, with all monthly tables expanded.
Completion messages are available to screen readers without visible repetition.
The dropdown retains focus; only the latest request can update the report. Failed
requests display an error and reset the dropdown to the last successful group.

Signup facts retain the user's signup group; activity and import attempts retain
the user's group at the time; NOFO facts retain their creation group. These are
expected to match in the normal workflow. Activity is stored per actor/month/group,
while All OpDivs counts distinct actors per month, not the sum of group counts.
Rates, warning averages, and median durations are calculated over the selected
records, never by averaging agency aggregates.

Migrations 0138–0139 add indexed group fields and backfill from surviving eligible
users and NOFOs. Run with application writes paused, as for the earlier baseline.
This data step is irreversible. Missing attribution stays blank: eligible records
still contribute to All OpDivs, but not an individual agency. Therefore agency
counts can sum to less than the all-agency count for older history. Current groups
are a best-effort baseline, not a reconstruction of historical membership. Once
captured, group facts survive account/NOFO deletion and are not refreshed from
current records. No agency-transfer workflow or correction UI is introduced.
