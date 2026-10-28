# Readability Calculator: ready to launch with public uploads disabled

Prepared October 28, 2026 for [SGG #12568](https://github.com/HHS/simpler-grants-gov/issues/12568)
and Builder [#970](https://github.com/HHS/simpler-grants-pdf-builder/issues/970),
[#971](https://github.com/HHS/simpler-grants-pdf-builder/issues/971) and
[#968](https://github.com/HHS/simpler-grants-pdf-builder/issues/968).

**Standing instruction: keep public uploads disabled in every environment.**
This plan does not authorize a flag change, a production test or public launch.
There is no shared-dev scheduling dependency: the requester confirmed no other
users need this dev environment. Request limits, restoration and effective
operating access still matter.

## Documentation ownership

This is Builder's overall readiness and launch plan. The infrastructure
implementation and operator procedures remain in
[the Simpler Grants infrastructure guides](https://github.com/HHS/simpler-grants-gov/tree/main/documentation/infra).
Use this plan alongside Builder's
[deployment safeguards](PDF_READABILITY_SAFEGUARDS.md) and
[release checklist](PDF_READABILITY_RELEASE_CHECKLIST.md); it does not replace
their evidence or approval requirements. Maintain one overall plan here, and
link to infrastructure procedures rather than copying their implementations.

## Completed evidence to reuse

See the [October 28 evidence record](../review-evidence/readability-readiness-1239/README.md)
for deployment, alarm/email inspection and route observations. Reuse only evidence
that matches the target revision and runtime; it does not establish public-release
readiness. Record new completed runs under review evidence and link them here.
The separate [application-5xx investigation](https://github.com/HHS/simpler-grants-gov/pull/13057)
may affect baseline interpretation; collection success alone does not establish
resolution or attribute failures to the calculator.

## 1. Preflight: no control changes

Target only `https://nofos.dev.simpler.grants.gov` / `infra-dev`. Record deployed
application/image revision, infrastructure revision, date, operator, source of
requests and evidence links. Existing **Inspect Readability Calculator** is the
read-only configuration tool. **Deploy NOFOs → dev** maps to infra-dev.

Read the effective and stored database-backed value of
`HHS_NOFO_PDF_METRICS_PILOT_ENABLED`, and its default if no stored row exists,
through an approved runtime/admin path. Record only absent/false/true and the
effective boolean, never an arbitrary settings dump. If effectively true, stop
and arrange an authorized correction; this plan does not change flags itself.
Repeat the check at the end. The existing inspection does not read Constance.

Check the canonical signed-out GET and empty POST `/readability-checker/`: expect the
disabled 503, no upload form, no-store and noindex headers. Record both exact
current route forms (`/readability-checker` and `/readability-checker/`) and
legacy forms (`/readability` and `/readability/`) without automatically following
redirects. The legacy route redirects to the renamed checker, and a slashless
request may have Django redirect/error behavior: record
it; do not mistake it for WAF enforcement or assume both forms return 503.
Confirm `/health` responds normally. If the baseline is unexpected, stop before
rate/block testing and investigate.

### Route coverage follow-through

The [October 28 preflight record](../review-evidence/readability-readiness-1239/README.md#preflight-finding-renamed-route-coverage)
found that the reviewed WAF source covered only the legacy route. Recheck the
current infrastructure revision; until current and legacy route coverage is
verified, do not claim protection or run the enforcement card. Correct scope
through a reviewed infrastructure change while keeping Count mode and the public
application flag unchanged. A legacy redirect does not prove target protection.

## 2. WAF test card: synthetic empty requests, no file uploads

Use [the existing WAF procedure](https://github.com/HHS/simpler-grants-gov/blob/main/documentation/infra/nofo-pdf-readability-waf.md) and leave the
application flag false throughout. No real documents, multipart file bodies,
slow uploads, oversized requests or parser work are included in this card.
Do not enable production rules as part of dev testing.

| Phase | Requests and ceiling | Passing evidence |
| --- | --- | --- |
| Baseline / Count | One GET and one empty POST for each of the four exact current/legacy forms, plus one GET `/health` (9 total). | Baseline responses recorded, unrelated route available, matching Count signals inspected where available. |
| Rate block only | Set rate action to Block, keep emergency off. Up to 44 empty POSTs across the four exact forms from one stable source, at most one every two seconds. Also one GET per exact form and one GET `/health` (49 total). Stop sending POSTs once sufficient interception evidence is obtained. | Verified effective configuration; WAF rate-rule blocks and 429 responses for all four forms where observed; GET and unrelated route unaffected. A 429 alone cannot identify which component generated it. |
| Rate recovery | Stop the burst. At most one empty POST per minute, at most 10 probes, plus one GET per exact form (14 total). | Eventually returns to the disabled application's baseline; no analysis enabled. |
| Emergency block | With the reviewed emergency setting active, one GET and one empty POST per exact form and one GET `/health` (9 total). | All four forms/methods intercepted with 403, corresponding emergency-rule block evidence, unrelated route available. |
| Restoration | Restore emergency false and rate Count, verify through inspection, then repeat the nine baseline requests (9 total). | Original WAF modes restored, canonical disabled responses/headers and unrelated-route availability restored. |

**Whole-card ceiling: 90 HTTP requests, no automatic retries.** Request timeout
is at most 10 seconds; each active rate/recovery phase has a 10-minute wall-clock
ceiling excluding infrastructure deployment time. Stop early on unexpected
impact, upload enablement, configuration mismatch, repeated 5xx outside the
known disabled baseline, or a request/time ceiling. Do not increase traffic to
force a result. Mark each unverified form explicitly; a redirect is not protection of its target.

Rate evaluation is approximate, not a guarantee that request eleven blocks.
Allow configuration propagation and record actual timings. No observed block
within the ceiling means inconclusive, not permission to increase load. Inspect
how the deployed topology identifies the test source; do not publish client IPs
or infer shared-IP fairness from a single-source test. Count/block counters and
HTTP responses should corroborate each other, accounting for publication delay.

### Control path and restoration requirement

The existing approved control path is reviewed Terraform configuration plus
**Deploy NOFOs**. There is no dedicated short-lived WAF test switch/restore
workflow in the reviewed tools. The inspection role cannot change WAF settings.
Do not improvise direct AWS updates, deploy unreviewed code or bypass approvals.

Before beginning phase 2, establish a reviewed way to perform rate activation,
emergency activation and restoration, plus a usable fallback if deployment or
restoration fails. Using only the current path entails staged configuration
changes/deployments. To avoid separate PRs for every toggle, consider one
consolidated reviewed verification change for narrowly bounded test controls
and any required runtime probes, or an existing authorized operator mechanism.
Do not build that mechanism unless the existing path cannot meet the test needs.
Document the selected path and its effective permissions before executing it.

On any interrupted/failed test, restoration is the next operation: emergency
false, rate Count, application flag still false, inspect and repeat baseline.
If permissions/deployment prevent restoration, report the precise failure and
use the agreed infrastructure fallback; do not delete the ACL or managed rules.
Record measured activation/restoration time. There is no emergency-response SLA
until this mechanism has been exercised.

## 3. Runtime checks without opening public uploads

Reuse current source tests and prior evidence only where the target revision
and runtime match. Saved-document readability metrics are not automatically
equivalent to the PDF upload/analyzer path. Confirm code-path coverage before
using an authenticated experience as evidence for that path.

| Check | Method with the public flag off | Evidence / remaining boundary |
| --- | --- | --- |
| Supported and rejected PDF processing | Approved probe invoking the deployed PDF analyzer with the existing small synthetic fixtures, one at a time. Prefer an existing authorized authenticated PDF-calculator route if it exercises the same handler. | Safe outcome labels/counts and deployed dependency versions; does not establish the signed-out enabled HTTP form. |
| Temporary-file cleanup | Observe only probe-owned synthetic files/directories before and after success, handled failure and a deterministic timeout. | Removal of analyzer and upload temporary files, including parser children. Current task declarations and local tests alone are insufficient. |
| Linux limits and admission | Approved deployed-runtime probe of child limits/environment and PostgreSQL contention using independent connections. | Sanitized pass/fail per limit/admission check; no credentials, settings dumps or raw task output. |
| Interrupted worker | Explicitly reviewed, isolated disposable task/probe if possible; do not terminate the normal service as a first test. | Actual survival/cleanup behavior and response procedure. A disposable task does not by itself prove cleanup in an existing long-lived service task. |
| Logging | Restricted search for synthetic body marker/fixture names and inspection of actual logging destinations and retention/access. | Public report contains only presence/counts and a decision; raw messages stay restricted. No match is limited to the destinations/time window searched. |
| Request-size and slow-upload protection | Reuse the assessment in [SGG #12678](https://github.com/HHS/simpler-grants-gov/pull/12678) and identify remaining deployment-dependent checks before any bounded ingress test. | Rate limiting does not establish these controls. No pathological PDF, resource-exhaustion or unbounded upload test. |

These are proposed probes, **not claims that an approved runtime runner exists**.
The inspection cannot read temporary storage or run container commands. Confirm
an existing mechanism first; otherwise include only the missing probes in the
consolidated reviewed verification change. Required security/privacy reviewers
must accept the actual runtime handling boundary, not just the test outputs.

The enabled signed-out form, recognition messages and browser-saved report still
need end-to-end validation if equivalent evidence is unavailable. Mark these
**deferred: public enablement prohibited**. Do not turn the flag on to complete
this plan. A future brief upload test requires the requester's separate explicit
authorization, a duration/request cap and verified disabled-state restoration.

## 4. Production setup: separate from public launch

After relevant dev verification and handling review, prepare one consolidated
production safeguards/private-email change where feasible. First inspect the
actual production account, region, service, existing controls and credential
path; dev permissions/settings do not prove production access. Keep the effective
public flag false before and after any deployment.

Provision/select the production private parameter through an approved secret
path, configure the production monitoring subscription, and have the inbox holder
confirm it. Verify controlled production alarm/recovery delivery without enabling
uploads, inspect actual production controls and agree responder/escalation paths.
Use separate production authorization and review; this dev plan is not a
production mutation approval. Do not copy dev account IDs or assume its workflows
support production. Keep recipient values/confirmation links out of public code.

Record verified controls, open limitations and which checks are deferred by the
disabled-state constraint. Only claim **ready, awaiting leadership approval**
when required safeguards/handling approvals and tests are complete or their
explicitly limited deferrals have been accepted by the release decision-maker.
Office of Grants leadership launch approval remains separate; no automatic
flag activation follows email setup, a successful deploy or a green test.

## Evidence record and completion

For every row use pass / fail / not run / deferred, with timestamp, environment,
application/infrastructure revisions, operator, method, sanitized evidence link
and limitation. Do not close SGG #12568 or Builder #970/#971 solely because alerts are enabled.
Link results across the existing trackers when authorized; no issue updates or
external messages are made by writing this plan. Keep raw runtime/log evidence
in an approved restricted location and make that location/access explicit before
collecting it. Content-free usage records remain indefinite; uploaded files,
logs and backups have separate requirements.
