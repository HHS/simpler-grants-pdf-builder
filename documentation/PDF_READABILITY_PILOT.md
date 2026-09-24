# PDF readability pilot

This pilot provides an unlinked `/readability/` route: upload one PDF, receive an
immediate readability report, and use the browser's **Print / save as PDF** dialog
to keep a copy. It does not create a NOFO or saved report history. An unlinked URL
is still public; direct distribution is not access control.

## Default-off release

Track remaining enablement work in [#968](https://github.com/HHS/simpler-grants-pdf-builder/issues/968).
Reuse the [source-based safeguards inventory](PDF_READABILITY_SAFEGUARDS.md)
and [deployment verification checklist](PDF_READABILITY_RELEASE_CHECKLIST.md)
to record target-environment evidence. Neither document grants approval to enable
the route or certifies current deployment settings.

`HHS_NOFO_PDF_METRICS_PILOT_ENABLED` defaults to false. Keep it off in shared
environments until the checks below are complete. This application change does
not install ingress rate limiting or authorize production enablement.

## Format-recognition status (#969, partial)

The application now has a conservative format-recognition gate inside the
existing bounded PDF worker. It reuses the pinned metrics package's tagged-PDF
support check and extracted semantic heading segments, then applies small,
source-code-configured multi-heading rules. A match means only that the PDF
resembles an approved pilot format; it is **not** template compliance,
accessibility, policy, or clearance approval. Untagged PDFs and PDFs with an
unreadable tag tree remain indeterminate; the generic metrics adapter is still
available internally but does not by itself confer supported-format status.

No approved formats or rules have been recorded yet. The rule tuple is empty,
so an otherwise valid PDF receives a service-configuration-unavailable message
and **no readability report**, even if the route flag is enabled locally.
Invalid rules also fail closed. Rules are immutable application code imported
by the worker, not a runtime environment variable, request parameter, database
value, or secret passed across the subprocess boundary. The route flag must
remain off in shared environments. No user should interpret this partial work
as satisfaction of the #969 release gate.

To complete #969, the product owner and grants-policy representatives must
identify the accepted HHS FY27 template and development-tool output variants,
approve tagged/untagged handling, and review representative positive and
negative synthetic or approved-public PDFs (including ordinary edits,
incomplete structure, and misleading headings). Only then should rules and
their tolerances be configured and tested. No filename or required
template-version marker is used. Recognized documents may cost two metrics
package extraction passes—one for format recognition and one for analysis—both
inside the existing 15-second subprocess deadline; tune this with approved
fixtures before enablement.

Release gates before enabling the anonymous route (merge is not approval to enable):

- Limit use to draft NOFOs made from an approved HHS FY27 template. Tell users to
  obtain the correct template from their agency grants policy office. Before
  calculation, recognize a supported format using the expected tagged-PDF profile
  and validated canonical heading/section coverage. Do not assume today's PDFs
  contain a template/version marker; adopt one only if approved templates add it.
  Recognition is not a clearance or accessibility determination. Test against
  approved representative PDFs and reject unrelated or unsupported PDFs.
- Return `X-Robots-Tag: noindex, nofollow, noarchive, nosnippet` on all route
  responses, including errors and the disabled state; add equivalent page metadata.
  Keep the route out of navigation and sitemaps. `robots.txt` and an unlinked URL
  are not access controls.
- Verify ingress request/body limits, per-client rate limiting, burst protection,
  monitoring, and a tested infrastructure-level route block. The application
  analysis slot and upload limit are not substitutes for these controls.
- Run the analyzer with a minimal allow-listed environment and without application
  secrets. Review a separately contained, nonprivileged task with no outbound
  network, a read-only application filesystem, and narrow temporary storage.
  Current subprocess time and resource limits alone are not a security sandbox.
- Obtain security/privacy and operations approval for the intended data
  classification, deployed logging, crash dumps, observability, temporary-disk
  cleanup and retention, and incident handling. Do not claim pre-decisional use is
  safe or that files are never saved until those checks are complete.
- Confirm the *stored* Constance value of `HHS_NOFO_PDF_METRICS_PILOT_ENABLED` is
  off in every deployment environment; an existing database value overrides the
  environment default. Name the owner who can disable it, test the route-level
  infrastructure backstop, and provide a purpose-built 503 without an upload form
  for disabled GET and POST. Preserve `no-store` and noindex; use `Retry-After`
  only with a credible restoration time. Name a support path.
- Align the public report with the authenticated readability panel: scope counts,
  five displayed metrics and their definitions, a visible extraction-reliability
  caveat, and a Calculation notes disclosure for secondary warnings. Add an
  accessible Copy metrics action and keep HHS/NOFO Builder identity and the
  estimates disclaimer in the saved report. Self-host fonts for this page.
- Verify the deployed metrics dependency, processing bounds, failure/timeout
  cleanup, and cross-worker concurrency. Test the PostgreSQL advisory lock with
  independent production-like connections and Linux resource limits in the target
  container; local SQLite/macOS results do not establish deployment behavior.
  Inspect browser-saved reports for readable page breaks, identity, disclaimer,
  and complete notes. Do not log filenames, extracted text, or metrics.

For local verification only, enable the flag in the isolated development database
or use the corresponding environment default with a fresh local database. Do not
change a shared environment as part of local testing.

## Measurement scope

Reuse the pinned `hhs-nofo-metrics` package. PDF results are extraction-based
estimates, not identical to Builder's semantic-HTML metrics or a compliance
determination. Untagged PDFs need particularly clear reliability caveats.

The dependency is pinned to 0.5.4, including the tagged-PDF parity fixes for
producer-declared cover/contents scope, cross-page paragraphs and lists, inline
word ordering, and numeric list markers. Profiles and formulas are unchanged;
extracted content and resulting PDF estimates can change. In Builder's stored
readability snapshots, package identity distinguishes previous scores from new
calculations. The PDF pilot does not store report history; each report identifies
its measurement version. This dependency update does not enable the
pilot or replace the deployment checks above.

## Stop the pilot

Turn `HHS_NOFO_PDF_METRICS_PILOT_ENABLED` off to prevent new analyses. Investigate
timeouts, sustained busy responses, unexpected parser failures, or resource
pressure before re-enabling. If the application cannot respond, use the existing
infrastructure incident procedure to block the route. Disabling new requests does
not cancel an already-running bounded analysis.

No navigation/login-page link, account flow, report archive, external PDF-generation
service, or batch-processing system is part of this pilot.

## Temporary processing limits

Initial application bounds are 15 MiB per upload, 150 pages, a 15-second analysis
deadline, and one active analysis. The Linux child has a 1.5 GiB address-space
ceiling, 20-second CPU ceiling, 2 MiB file-size ceiling, and 64 open-file ceiling.
These conservative pilot choices must be tuned against approved representative
PDFs and the target ECS capacity; byte size alone does not bound parser memory.
PostgreSQL advisory locking provides the production cross-worker analysis slot.
The SQLite development path uses a local file lock and is not a cross-host control.

Normal completion and handled failure/timeout paths remove the parent-owned request
directory and nested parser copies. A forced termination of the web worker or host
can interrupt that cleanup. Before enablement, verify the environment's stale-temp
cleanup or ephemeral-task replacement policy and its retention implications. Do not
describe the implementation as a guarantee of immediate deletion after a crash.
