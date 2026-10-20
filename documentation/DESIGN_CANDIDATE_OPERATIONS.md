# Synthetic design-candidate operation rules

First implementation slice for #1147. This is a pure in-memory rules component,
not a running agent pilot, authentication layer, persistence adapter or security
sandbox. It creates no NOFO record and changes no existing import/editor route.

`nofos/design_candidate.py` holds immutable candidate snapshots and validates
three presentation operations. `nofos/design_candidate_choices.py` supplies
legal theme/cover values from current Builder model choices, not a copied catalog.

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
- HTML review is honestly declared unsupported by this slice until host
  integration exists. DocRaptor remains disabled in all lower environments.
  Do not add a local renderer, broker or tunnel. Missing local PDF capability
  is not a pilot blocker or an acceptance/transfer prerequisite.

## Next integration work

Connect a trusted, isolated synthetic host to existing Word import and HTML
rendering. Preserve immutable source/import baselines and render-input identity;
map validated presentation settings onto candidate-only storage. Enforce current
authorization, authoritative revision replacement, retry identity and controlled
assets. Then add revision-bound HTML review references and demonstrate negative
tests with another candidate and blocked credential/network/production access.
The broader #1147 acceptance criteria remain open. Human review, trusted transfer
and confirmed discard belong to #1148, #1149 and #1150, not agent operations.

## Checks

From `nofos/`, using Builder's locked development environment:

```sh
python manage.py test nofos.tests_nofos.test_design_candidate --noinput
```

Tests cover content/source preservation, legal choices, detached reads, change
history, stale/ABA revisions, candidate/section binding, rejected authority and
path/URL operations, input bounds and the operation budget. No browser behavior
has changed in this slice, so it has no new UI screenshot or PDF evidence.
