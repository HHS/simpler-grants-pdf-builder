# PDF readability pilot

This pilot provides an unlinked `/readability/` route: upload one PDF, receive an
immediate readability report, and use the browser's **Print / save as PDF** dialog
to keep a copy. It does not create a NOFO or saved report history. An unlinked URL
is still public; direct distribution is not access control.

## Default-off release

`HHS_NOFO_PDF_METRICS_PILOT_ENABLED` defaults to false. Keep it off in shared
environments until the checks below are complete. This application change does
not install ingress rate limiting or authorize production enablement.

Before enabling:

- Verify request-rate and request-body controls at ingress. Application analysis
  concurrency and size limits are not substitutes for ingress abuse protection.
- Verify the actual deployed dependency, configured processing limits, cleanup
  after failures/timeouts, and cross-worker concurrency protection.
- Test the PostgreSQL advisory lock with independent production-like connections;
  local SQLite file-lock tests do not establish PostgreSQL behavior. Validate Linux
  resource limits in the target container, not only on macOS.
- Test approved representative tagged and untagged PDFs. Confirm the report's
  extraction caveats and unavailable metrics, not just successful uploads.
- Inspect the browser-saved report for readable page breaks and complete warnings.
- Confirm acceptable transient processing and operational log handling for the
  intended documents. Do not claim that processing happens only in the browser.
- Name a support contact and person who can turn the flag off. Use existing
  operational logs/monitoring; do not record filenames, extracted text, or metrics.

For local verification only, enable the flag in the isolated development database
or use the corresponding environment default with a fresh local database. Do not
change a shared environment as part of local testing.

## Measurement scope

Reuse the pinned `hhs-nofo-metrics` package. PDF results are extraction-based
estimates, not identical to Builder's semantic-HTML metrics or a compliance
determination. Untagged PDFs need particularly clear reliability caveats.

At implementation start, the dependency is 0.5.3. Newer merged parity fixes are not
in that release. Adoption requires a separately verified package release and lock
update; a merged source commit alone does not change the deployed dependency.

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
