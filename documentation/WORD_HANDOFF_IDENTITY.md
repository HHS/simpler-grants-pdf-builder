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

The row stores a trusted OpDiv group, receipt time, initial `received` state and
state timestamp, optional Builder NOFO foreign key, and a stable NOFO UUID
linkage tombstone. It stores no Word document, access URL, checksum, credential,
request body, or intermediate output. The tombstone preserves the association
and prevents relinking if the Builder NOFO is deleted. A NOFO link is one-time,
idempotent for the same NOFO, and requires matching group scope.

## Trust boundary

`record_handoff` accepts an internal `TrustedHandoffPrincipal` containing the
verified source-system identity and authorized OpDiv group. A future approved
ingress adapter must derive it from authenticated credentials and server-side
authorization policy, **never from a caller's document or metadata body**. This
module does not perform machine authentication, prove the object was constructed
by a trusted adapter, expose an endpoint, or grant any runtime integration access.
It rejects non-OpDiv groups and rejects a duplicate identity tuple attempted
under a different OpDiv group. `link_handoff_to_nofo` also checks both source
system and group scope, and cannot change `Nofo.group`.
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
- `state` starts as `received` but this identity service does not advance it.
  The separate #955 lifecycle proposal covers guarded transitions; durable
  state-event/attempt history and production transaction integration remain open.
- Comp ID stability, format, and behavior for modifications or pooled
  announcements remain unconfirmed with Announcement Services.
- File storage, retention, deletion, backup, audit logging, malware scanning,
  authentication, ingress ownership, incident response, and organizational
  approvals remain gated by #952. Retention of receipt metadata and linkage
  tombstones is a proposal, not an approved deletion policy.
- PostgreSQL concurrent retry behavior and any future ingress mapping need
  integration tests after the security and operating boundary is approved.

No endpoint, shared-environment connectivity, model execution, or real-document
processing is included in this change.
