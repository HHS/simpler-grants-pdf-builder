# Proposed Word handoff lifecycle foundation (#955)

This is an **in-process, synthetic-only proposal**, not an operational handoff. It
defines a small pure transition function and tests, but does not receive files,
run an agent, persist lifecycle changes, or promote anything into production
Builder. The #952 security and operating gate remains closed. The separate #953
identity record starts at `received`; it is not yet wired to this function.

The identity tuple `(source_system, source_record_id, source_version)` and the
handoff ID are carried unchanged in each returned snapshot. For Announcement
Services, the current manual pilot uses FON as the source record identity and
actual AM version as source version; the earlier comp-ID mapping is historical.
Exact mapping into this optional foundation remains under #888. Source versions
are opaque: this
module does not compare them, resolve skipped/out-of-order versions, or choose a
current version. The #953 unique identity boundary prevents a second identity
record for the same exact tuple; this pure function cannot enforce database
uniqueness or prevent duplicate downstream work by itself.

## Relationship to the manual S3 pilot

The [current manual pilot record (#950)](https://github.com/HHS/simpler-grants-pdf-builder/issues/950)
is separate from this future automated lifecycle. Its October 21, 2026 written
folder proposal uses `incoming` for AS Word/NB download, `processed` for
NB-published successful results, and optional `failed` for NB processing errors.
AS resolves its publication errors before a document reaches `incoming`.
Folder names do not map directly to these lifecycle states or events.

In particular, download, explicit acceptance of the design handoff, and design
completion are separate. The written processed-results proposal does not settle
handoff acceptance, source-file movement, result contents or permissions.
The `accepted` state below does not record an S3 move or start a retention clock.

AS's written no-repeat-publication/new-version-correction proposal conflicts
with the October 20 pre-pickup overwrite discussion. Topic 3 remains open until
the mid-design update process is finalized under #888/#950. The identity retry
and lifecycle retry behavior here do not implement either exchange policy.
Retention periods, acceptance recording and cleanup responsibilities still
require agreement and approval under #952.

## Proposed transitions

| Current state | Event | Next state | Additional condition |
| --- | --- | --- | --- |
| `received` | `queue` | `queued` | First processing attempt |
| `queued` | `start` | `processing` | — |
| `processing` | `complete_processing` | `awaiting_review` | — |
| `awaiting_review` | `accept` | `accepted` | Review decision supplied |
| `awaiting_review` | `reject` | `rejected` | Review decision supplied |
| `received`, `queued`, `processing`, `awaiting_review` | `fail` | `failed` | Defined failure code supplied |
| `failed` | `retry` | `queued` | Same handoff/source identity; increment attempt |

`accepted` and `rejected` are terminal. No cancellation or supersession policy is
set here. Rejection ends this handoff; cleanup of temporary artifacts is not
implemented. Failure records a finite, non-document-content code and clears it
on retry, but no cleanup, retry limit, or backoff is implemented. Every call
requires the caller's expected state and revision. A mismatch rejects a stale
transition; a future persistence adapter must make that comparison and update
atomic. The function alone cannot address concurrent workers or repeated side
effects. A retry must reuse the same identity record and must not create a new
production NOFO; no production creation path exists in this foundation.

`accept` and `reject` require a `ReviewDecision` with reviewer ID,
authorization reference, and decision ID. These values are **not** proof of a
real authenticated, authorized human: any Python caller can construct them.
A future trusted service must establish reviewer identity and authority for the
specific handoff and OpDiv, bind the decision to a reviewed artifact/version,
audit the decision, and prohibit agent credentials from invoking promotion.
Acceptance here is only a lifecycle label, **not** production promotion.

Before #955 can be considered complete, the approved design must connect
ingress, durable atomic state updates, queue/worker execution, isolated agent
credentials, artifact storage and cleanup, human authorization, and a separately
controlled promotion operation. Those choices depend on the unresolved #888
contract and #952 approvals. Until then, only synthetic documents and local
tests are permitted; do not connect Announcement Services or process real
pre-decisional documents in a shared environment.
