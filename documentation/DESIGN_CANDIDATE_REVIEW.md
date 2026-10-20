# Local candidate review and warning acknowledgments

This is a partial implementation of [#1148](https://github.com/HHS/simpler-grants-pdf-builder/issues/1148),
on the [synthetic local host](DESIGN_PILOT_LOCAL_HOST.md). It adds a current-revision
report and attributable human warning acknowledgments. It does not implement
acceptance, deletion, substantive editing, shared hosting or a model runtime.

## Review report

The existing owner-only review URL shows candidate/source identity, current
render-bound revision, local staging status, findings, presentation change reasons,
read-only imported section text and the retained conversion output. Document text
and quoted instructions remain escaped data. A link alone grants no access.

The report reuses Builder's existing offline heading, internal-link and endnote
diagnostics and missing-metadata helper. No external-link requests or new model
assessment are added. Findings record a stable pilot rule, local finding ID,
target, evidence, status, severity and next step; section findings link to the
affected read-only section. A pass describes only that diagnostic's scope.
Unsupported diagnostic input becomes blocking/not assessed, not a pass.

Exact stored-source and imported-record checks reuse the host's integrity guard.
They do not prove source-to-import fidelity. Source-to-import reconciliation and
complete asset/link verification are explicitly not assessed and remain blocking.
No current candidate is called ready for acceptance just because its diagnostics
are clean. The available state is **Ready for review**, with import processing
complete, no model run and no production NOFO. Later processing/acceptance states
must be connected to real services rather than simulated here.

**View current HTML (opens a new tab)** remains optional and revision-bound.
**PDF unavailable** is disabled because DocRaptor stays disabled in lower
environments. Missing PDF pagination evidence is an informational capability
limit, not an acceptance blocker or reason to enable a local renderer.

## Human warning acknowledgment

Only a nonblocking import warning has an **Acknowledge warning** form. The human
provides a reason of 1 to 500 characters. The server checks the current owner/group,
CSRF, candidate/render revision and complete findings evidence before recording
actor, timestamp, reason and exact finding digest. Candidate-only tool credentials
grant no acknowledgment authority.

The acknowledgment is separate from design acceptance. It does not clear blocking
findings, change content, alter ordinary NOFO status or transfer/delete a record.
Retries preserve the original reason/time. After a design or render-input change,
the old acknowledgment is retained as historical local data but is not applied to
the new revision. A changed warning/check result also invalidates an old form,
even if rendered HTML is unchanged. Forms that fail return a recovery link to
the current review page; an unsaved acknowledgment reason is not retained, so
copy it before leaving if needed.

Presentation edits still use the existing bounded theme/table-width controls.
Their earlier operation log has reasons and before/after values, but does not
establish actor/time attribution. Do not represent it as the new human-decision
audit trail. Correct wording, missing metadata and structural problems in the
source, then import a fresh synthetic copy. In-app substantive corrections and
attribution for all presentation edits remain follow-up work.

## Limits and follow-through

The private scratch database retains source bytes and acknowledgment records;
this is not a new retention/deletion policy or real-data approval. Diagnostics
are rerun synchronously; historical rendered artifacts are not archived. This
slice does not close #1148: acceptance/rejection services, complete technical
verification, content corrections, remaining state transitions and their full
walkthroughs remain outstanding. #1149 owns acceptance/transfer and #1150 owns
confirmed discard. No live operation or new provider is authorized by these tests.
