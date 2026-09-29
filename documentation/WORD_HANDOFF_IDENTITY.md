# External Word handoff identity foundation (proposal)

This local foundation addresses part of #953 under the #952 security gate. It is
not an approved cross-system contract and does not enable receiving or processing
real pre-decisional documents. Tests use synthetic identifiers and NOFOs only.

## Receipt identity

`ExternalSourceHandoff` is a separate metadata-only record, not a field on
`Nofo`. Its UUID `id` is the durable handoff/correlation identifier. The exact
`(source_system, source_record_id, source_version)` tuple has a database unique
constraint. For the proposed Announcement Services pilot, source record ID would
be the comp ID, but the schema deliberately avoids system-specific field names.
Each value is an opaque, non-empty string; the service neither normalizes nor
numerically compares version labels. Exact retries return the original receipt
and timestamp without creating a second record. A different version creates a
separate receipt, even if its label looks numerically older or skips a number.
Neither receipt automatically supersedes or overwrites the other.

The immutable receipt row stores a trusted OpDiv group, receipt time, initial
`received` state and state timestamp, but no direct NOFO link. A separate
`ExternalSourceHandoffResult` row records each append-only linkage: a stable
NOFO UUID tombstone, optional live NOFO foreign key, predecessor result,
creation time, and (for replacements) review-decision evidence. Deleting a
Builder NOFO clears only the live foreign key; its tombstone and result remain.
`ExternalSourceHandoffCurrent` is a one-row-per-receipt selector, so at most
one result is current. An initial link is idempotent for the same live NOFO.
It stores no Word document, access URL, checksum, credential, request body, or
intermediate output.

An explicitly supplied `ReviewDecision` and expected current-result ID are
required to append a replacement. The service locks the receipt, verifies
source and OpDiv scope, then atomically appends a result and advances the
selector by compare-and-swap. The predecessor remains traceable through
`supersedes`; the source version and receipt do not change. The review object
is evidence supplied by a future trusted adapter, **not proof of authentication
or authorization by itself**. Same-handoff NOFO UUIDs cannot be linked twice.
A NOFO may still be associated with separate receipts, as the old schema
allowed; cross-version current-selection policy remains unresolved.

Migration `0144` preserves existing live links and deleted-NOFO tombstones as
initial results. It aborts on malformed live/tombstone disagreement instead of
silently dropping a link. A reverse migration is allowed only while the result
and current-selector tables are empty; otherwise it raises an error rather than
discard immutable result IDs or replacement history.

## Trust boundary

`record_handoff` accepts an internal `TrustedHandoffPrincipal` containing the
verified source-system identity and authorized OpDiv group. A future approved
ingress adapter must derive it from authenticated credentials and server-side
authorization policy, **never from a caller's document or metadata body**. This
module does not perform machine authentication, prove the object was constructed
by a trusted adapter, expose an endpoint, or grant any runtime integration access.
It rejects non-OpDiv groups and rejects a duplicate identity tuple attempted
under a different OpDiv group. Initial and replacement link operations also
check both source system and group scope, and cannot change `Nofo.group`.
Because Builder users can later change a linked `Nofo.group`, any future read,
promotion, or artifact access must re-check the current NOFO group against the
current authorized principal. The receipt's historical group and initial link
check are not durable authorization for future access.

## Unresolved contract and security decisions

- Exact same-tuple retries are idempotent by identity only. No payload digest is
  stored, so conflicting document bytes on a retry cannot yet be detected.
- Older, skipped, and out-of-order versions are all retained. Whether any should
  be rejected, queued, or considered current requires source-version semantics
  and explicit policy; no ordering or supersession policy is implied here.
- `state` starts as `received` and is frozen with the receipt; this identity
  service does not advance it.
  The separate #955 lifecycle proposal covers guarded transitions; durable
  state-event/attempt history and production transaction integration remain open.
- Comp ID stability, format, and behavior for modifications or pooled
  announcements remain unconfirmed with Announcement Services.
- File storage, retention, deletion, backup, audit logging, malware scanning,
  authentication, ingress ownership, incident response, and organizational
  approvals remain gated by #952. Retention of receipt metadata and linkage
  tombstones is a proposal, not an approved deletion policy.
- A synthetic PostgreSQL race test covers concurrent same-receipt replacement.
  Future ingress mapping and production authorization need separate tests.
- Model and public-ORM guards prevent accidental mutation. They are not a
  security boundary against raw SQL, privileged admin access, or a compromised
  application process. Deployment permissions and audit remain under #952.

No endpoint, shared-environment connectivity, model execution, or real-document
processing is included in this change.
