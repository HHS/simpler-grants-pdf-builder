# Synthetic design-candidate operation rules

Original component slice for #1147. Status reviewed October 28, 2026: the
[local host](DESIGN_PILOT_LOCAL_HOST.md), [candidate interface](DESIGN_CANDIDATE_INTERFACE.md)
and [review slice](DESIGN_CANDIDATE_REVIEW.md) now provide integration described
separately. The limitations below describe this in-memory component alone.

First implementation slice for #1147. This is a pure in-memory rules component,
not a running agent pilot, authentication layer, persistence adapter or security
sandbox. It creates no NOFO record and changes no existing import/editor route.

`nofos/design_candidate.py` holds immutable candidate snapshots and validates
three presentation operations. `nofos/design_candidate_choices.py` supplies
theme/cover values from current Builder model choices, not a copied catalog.
Retired themes are excluded from new selection. Calling
`design_capabilities(candidate=current_candidate)` also retains that candidate's
current legacy theme, so an existing design can keep it. Once changed away, the
retired theme is no longer offered. Rebuild choices from the authoritative current
candidate before each operation; do not reuse a previous revision's choice list.

### Permission policy for integration

The agreed integration policy is to constrain agent design choices using the
initiating person's group permissions plus the document's design restrictions.
The host must derive those permissions from authenticated user context, never
imported OpDiv text or an agent-supplied group. Apply the existing Builder rules
for the resulting theme/cover combination as well as individual field values.
Access remains limited to the assigned candidate and supported design operations;
the person's broader account permissions do not grant the agent access to other
NOFOs or acceptance/transfer authority.

This slice supplies a catalog, not permission enforcement. The host must further
filter and validate its choices using that policy. Agent authentication and access
mechanisms remain integration work; no normal Builder user account for the agent
is assumed or implemented here. These internal changes do not alter editor tasks
or the existing Builder editing screen.

## Trusted-host boundary

The host constructs `DesignCandidate` with its selected candidate identity,
original source SHA-256, imported content and initial presentation settings. The
content object is opaque JSON: this component does not define a universal NOFO
schema or turn parser output into a complete rendering model. The host must
include separately stored metadata, introduction ownership and other fidelity
fields when building that content snapshot.

The host owns the authoritative current snapshot. Agent requests cannot construct
or replace it, supply application choices, or choose another host identity. Do
not give an agent a Python interpreter or direct access to these objects.
An agent-facing transport must authenticate and bind access separately. A
candidate ID or content digest is not an authentication credential.

`apply_design_request` validates an exact JSON request shape:

```json
{
  "operation": "set_theme",
  "candidate_id": "synthetic-candidate-a",
  "expected_revision": "revision returned by the host",
  "value": "a theme value declared by Builder",
  "reason": "Match the explicit preference in the source"
}
```

The value above is illustrative, not a legal hardcoded theme. `set_cover` uses
the same fields. `set_table_width` adds a `section_id` already present in the
host's `section_table_width` map and requires a real JSON boolean. No arbitrary
HTML classes, body markers, URLs or file paths are accepted as operations.

Successful changes return a new snapshot without modifying the old one. Content
and source identity stay unchanged. Revisions bind the source, candidate identity,
opaque content, presentation, change log and sequence. Each change records the
before/after value, rationale and prior revision; returning to an earlier setting
does not revive its old revision. A no-op returns the same snapshot. Reads return
detached JSON values. These are technical records, not a guarantee that an agent's
rationale is correct or that its branding choice matches the author's intent.

The component rejects cross-candidate requests, stale revisions, unknown or extra
fields, invalid choices, out-of-candidate sections and substantive writes.
Acceptance, discard, publication, arbitrary fetches, CSS and PDF operations are
not supported. Document instructions remain opaque content, not permission.

## Bounds and limitations

- Requests are limited to 4,096 UTF-8 bytes, rationale to 500 characters and actual
  presentation changes to 100 per candidate. These are conservative synthetic
  operation limits, not measured production document/model resource limits.
- The trusted host must atomically compare and replace its current snapshot.
  This pure function cannot prevent a caller from replaying an obsolete object
  or resolve concurrent database writes. Restart durability and idempotent run
  creation are not implemented here.
- This component does not parse Word, validate source fidelity, sanitize assets,
  render HTML, inspect PDFs, contact a model or enforce process/network isolation.
  It makes no database, file or network calls. Its operation tests do not prove
  that an agent runtime cannot escape a future host.
- This in-memory component does not render HTML. The separate local host now
  provides revision-bound HTML review. DocRaptor remains disabled in all lower environments.
  Do not add a local renderer, broker or tunnel. Missing local PDF capability
  is not a pilot blocker or an acceptance/transfer prerequisite.

## Integration status and remaining work

The [local host](DESIGN_PILOT_LOCAL_HOST.md) connects synthetic Word import,
candidate persistence and revision-bound HTML review. The [candidate-only
interface](DESIGN_CANDIDATE_INTERFACE.md) adds scoped transport access, and the
[review slice](DESIGN_CANDIDATE_REVIEW.md) adds findings and warning acknowledgments.
These contracts own their current capabilities and limits; the pure operation
component alone does not establish them.

#1147 is closed. Closure does not establish a model runtime, proven runtime
isolation or production authorization. Complete source fidelity, runtime isolation,
trusted acceptance/transfer and confirmed discard remain separate capabilities;
follow the [boundary ADR](../adr/2026-10-20-agent-design-pilot-boundary.md) and the
current slice guides rather than the original component's future-work list.

## Checks

From `nofos/`, using Builder's locked development environment:

```sh
python manage.py test nofos.tests_nofos.test_design_candidate --noinput
```

Tests cover content/source preservation, legal choices, detached reads, change
history, stale/ABA revisions, candidate/section binding, rejected authority and
path/URL operations, input bounds and the operation budget. No browser behavior
has changed in this slice, so it has no new UI screenshot or PDF evidence.
