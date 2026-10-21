# Candidate-only local interface

This extends the [isolated synthetic host](DESIGN_PILOT_LOCAL_HOST.md) under
[#1147](https://github.com/HHS/simpler-grants-pdf-builder/issues/1147).
It is an HTTP authorization boundary for invented local candidates, not an agent
runner, OS sandbox or approval to process real documents. There is no model call
or provider integration in this slice. Do not give a client broad Builder cookies,
the existing global API token, provider credentials or a shell to replace this
interface. A client with access to the host's database/files is **not contained**
by an HTTP credential. Runtime filesystem/process/network isolation remains work
to do before an actual agent runs against anything beyond synthetic test data.

## Human control

On **Review synthetic candidate**, **Create or replace agent access** is a
CSRF-protected, owner-only POST. It generates 256 random bits, shows the key in
that response only, and stores only its SHA-256 digest. It replaces the previous
key immediately. Do not put a key in a screenshot, URL, issue, chat, command-line
argument or log. The response and tool responses are marked `no-store`.

**Revoke agent access** invalidates the current key. A key expires after 20
minutes or 100 admitted requests, whichever comes first. Expiry/revocation and
current account/group ownership are checked on every request. Replacing a key
resets its request counter, but cannot reset the kernel's 100-change candidate
limit. Invalid design requests consume the admitted request's quota. Invalid
credentials do not gain access through an authenticated browser session.

Creation/revocation does not change content, accept a design, delete a candidate
or start a model. An active key is not shown again on the review page.
The private scratch database still contains source content and local audit data.
This is not a new retention or audit-approval policy.

## Protocol

Use only the isolated profile bound to `127.0.0.1`. Send the private key as
`Authorization: Bearer <key>` in the HTTP header, never a URL/query parameter.
The API ignores session cookies for authorization. Middleware rejects
authorization-header requests to ordinary human pages and other Builder routes.
Do not expose this localhost service through a proxy or tunnel.

| Method and path | Result |
| --- | --- |
| `GET /design-pilot/<candidate-id>/tools/capabilities` | Allowed operations/choices and fixed limits; PDF and acceptance are unsupported |
| `GET /design-pilot/<candidate-id>/tools/read` | Selected candidate content/presentation, warnings, change log, source identity, host revision and authenticated human review URL |
| `POST /design-pilot/<candidate-id>/tools/operation` | One bounded JSON design request; returns the new candidate snapshot |
| `GET /design-pilot/<candidate-id>/tools/html?revision=<revision>` | Filtered native HTML for the exact current revision; sandboxed CSP, no active scripts or external navigation |

No list-all, arbitrary fetch, file-path, shell, body/metadata edit, cover mutation,
acceptance, publication, transfer, discard or PDF endpoint is provided.
Candidate text and quoted instructions remain data, not authority.

Capabilities and writes use the host's current authenticated-owner and document
theme/cover policy, reusing `NofoThemeOptionsForm`. The token does not grant all
themes in the model catalog. A broader session cookie, imported OpDiv or a
submitted group cannot expand the token owner's choices. Legacy themes are
retained only while currently selected and permitted by that policy.

Copy the opaque `revision` from `read` into `expected_revision`; do not use an
internal audit-log revision or infer one from the change count. The host revision
binds the candidate and current rendered HTML/dependencies. Requests preserve the
same revision and identity checks used by human presentation changes.

An operation must be `application/json`, at most 4,096 bytes, with unique fields
and finite values. For a theme change, these are the exact fields:

```json
{
  "operation": "set_theme",
  "candidate_id": "<candidate-id>",
  "expected_revision": "<revision-from-read>",
  "value": "<theme-from-capabilities>",
  "reason": "Explain the proposed presentation change."
}
```

For `set_table_width`, add `section_id` from that candidate's presentation map
and use the JSON boolean `true` or `false` as `value`. Reasons are limited to 500
characters. Unknown/missing fields and unsupported operations are rejected.
The client cannot request a fresh key or supply ownership/authorization fields.

Read the candidate again after HTTP 409; do not blindly replay a write. HTTP 401
means the credential is invalid, expired or exhausted, or ownership no longer
matches. Only the human owner can decide to issue another key. A rejected
render/design request rolls back the design change while retaining the admitted
quota charge; an unexpected server error may roll back the entire request.
SQLite contention can return 409 without consuming a request; retry only after
reading the current candidate. Keys are not durable job identities, and this is
not comprehensive model/time/memory rate limiting.

## Evidence and limits

The transport tests exercise owner/group revocation, cross-candidate denial,
rotation/expiry/quota, cookie-only rejection, JSON bounds, stale revisions,
rollback and forbidden operations. The concurrency test uses two threads with
actual separate SQLite transactions: competing writes cannot both succeed at an
old revision, and competing requests cannot exceed the fixed quota. A busy
request may fail closed and need a sequential retry. These tests do not validate
other database engines, a reverse proxy, a real agent runtime or production use.

HTML filtering retains the existing host's declared fidelity limitations. It is
not PDF pagination evidence or a completed readiness review. Human decision
attribution, historical render archives, findings/readiness, comprehensive resource
limits, acceptance/transfer and confirmed discard remain separate work.
