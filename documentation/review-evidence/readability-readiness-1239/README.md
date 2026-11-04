# Readability launch readiness observations

Historical observations recorded October 28, 2026 for
[PR #1239](https://github.com/HHS/simpler-grants-pdf-builder/pull/1239),
Builder #968/#970/#971 and SGG #12568. Source baseline: `8cac8f60`.
These are the existing plan's observations, relocated without rerunning deployment
checks. Action IDs below identify the inspected infrastructure evidence; they do
not establish current configuration or full release readiness. Private delivery
confirmations remain private.

Use the [current launch plan](../../readability/READABILITY_CALCULATOR_READINESS.md)
for procedures and unresolved work.

## Completed evidence to reuse

| Evidence | Established | Does not establish |
| --- | --- | --- |
| [Dev deployment 40701483488](https://github.com/HHS/simpler-grants-gov/actions/runs/40701483488) | PR #13032 deployed successfully. | Public-release readiness or application-error resolution. |
| [Inspection 40706316704](https://github.com/HHS/simpler-grants-gov/actions/runs/40706316704) | All four calculator notification actions enabled, all four alarms OK, expected alarm/recovery topic, one confirmed email subscription, both WAF rules in Count mode; rate 10 per source IP per 300 seconds. | Threshold enforcement, stored public flag, runtime cleanup or content-free logs. |
| [Delivery test 40576048291](https://github.com/HHS/simpler-grants-gov/actions/runs/40576048291) and private inbox confirmations | Both synthetic ALARM and OK emails delivered; test alarm removed. | Actual capacity/WAF thresholds or production delivery. |
| [Synthetic fixture kit](https://github.com/HHS/simpler-grants-gov/blob/main/documentation/infra/nofo-readability-verification-kit.md) | Small fictional PDFs and manifest already prepared. | Tests against the deployed runtime. |

The overnight application-5xx investigation in [PR #13057](https://github.com/HHS/simpler-grants-gov/pull/13057)
is separate. Review any findings that affect test safety or the reliability of
baseline responses; do not attribute those errors to the calculator without
evidence. A green diagnostic only establishes collection, not resolution.

### Preflight finding: renamed route coverage

On October 28, signed-out GET `/health` returned 200 and GET
`/readability-checker/` returned 503 without an upload control, with no-store and
noindex headers. GET `/readability/` returned 308 and the authenticated checker
redirected signed-out access to login. No POST or upload was sent during this
finding. These HTTP observations do not read the stored Constance value.

The reviewed Simpler Grants WAF source still matches only `^/readability/?$`.
That does not cover the renamed public checker directly. Update the two rule
scopes to include current and legacy paths, with tests, through a reviewed
infrastructure change before claiming protection or running the enforcement
card. Keep Count mode and the public application flag unchanged while correcting
scope. Testing only the old redirect would give incomplete coverage.
