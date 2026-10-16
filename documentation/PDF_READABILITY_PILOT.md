# PDF readability pilot

This pilot provides an unlinked `/readability/` route: upload one PDF, receive an
immediate readability report, and use the browser's **Print / save as PDF** dialog
to keep a copy. It does not create a NOFO or saved report history. An unlinked URL
is still public; direct distribution is not access control.

Saved readability checkpoints, per-NOFO history, and the saved-results overview
(#1009 / #1014) belong only to the authenticated Builder feature documented in
[Readability metrics](READABILITY_METRICS.md#saved-review-checkpoints). They are
outside this pilot and its release epic (#968), must not be exposed through
`/readability/`, and do not satisfy the pilot's release acceptance criteria.
Content-free pilot usage monitoring does not store metric results or report
history. Browser **Print / save as PDF** saves a local copy, not server-side history.

## Word uploads (#1111)

Only the authorized `/nofos/readability/` route also accepts unlocked `.docx`
files. The existing public `/readability/` route remains PDF-only, even when its
independent flag is enabled. Existing flag and permission names retain `PDF` for compatibility;
their values and access checks are unchanged. This addition does not enable a
route or authorize a new deployment/document classification. Legacy `.doc`,
macro-enabled documents and other file types are not supported.

The existing isolated worker validates the ZIP container before using the
already installed Mammoth converter. It permits at most 2,000 entries and
45 MiB total expanded data, rejects duplicate/encrypted entries, macros and
DTD/entity declarations in every part regardless of extension, and requires the
root officeDocument relationship to select the validated canonical
`word/document.xml` part with the normal DOCX main content type. Unusual packages
with a noncanonical main-part path are deliberately rejected in this first slice.
External file access and embedded style maps are disabled, and images are not
loaded. The existing pure Word table transform is reused; the saved-NOFO import
workflow, its custom style map and instruction-box cleanup are not invoked.

Word recognition reuses the PDF pilot's loose signals over the first
50,000 characters of converted text. For unfilled templates, one additional
compound signal requires both an HHS agency name (including the explicit
“HHS-wide” alias) and “Notice of funding opportunity” or “NOFO [master] template.”
A distinct existing signal such as Grants.gov is still required. A filename,
agency name alone or repeated signal is insufficient. PDF recognition is
unchanged. This is modest abuse deterrence, not exact template validation.
It does not claim a stable Word page count. The existing HTML
profile `hhs-nofo-fy27-html@0.5.0` measures UTF-8 converted body HTML with the
pinned metrics package and corrected passive classifier. No intermediate
PDF, saved NOFO or report-history record is created.

Reports identify the Word source and explain that conversion may omit headers,
footers, text boxes and images. Template instructions and draft options that
convert to text are included. Paragraphs, lists, tables and notes are measured
according to the existing HTML profile. Word, PDF and Builder draft scores can
differ because they measure different recovered content. Public output contains
only the existing safe metric projection, fixed warnings and scope counts, never
converted document text. Conversion messages are reduced to a fixed warning.
When the engine supplies no reliability rating, reports and metric cards say
that reliability has not been assessed. Missing evidence is not converted into
low (or high) confidence, nor inherited from a different metric. Supplied PDF
ratings and the generic PDF adapter's explicit low-confidence policy remain.

The complete current alert-copy catalog, report headings, metric labels, rating
selection rule and authenticated/public variants are documented in
[UI patterns — Readability estimate reliability alerts](UI_PATTERNS.md#readability-estimate-reliability-alerts).
That catalog also distinguishes an unavailable metric from unassessed reliability.
Source explanations stay in one paragraph; only the authenticated tool suggests
uploading Word instead of a PDF. Historical screenshots may predate copy changes.

Both formats share the existing 15 MiB upload limit, 15-second deadline, global
analysis slot, filtered subprocess environment and Linux resource limits. Word
uses the same temporary-directory cleanup and content-free outcome recording.
There is no page limit for Word, because there is no reliable pagination here;
expanded-size, entry, time and memory bounds apply instead. Existing deployment
safeguards below still apply and are not replaced by ZIP validation.

## Default-off release

### Content-free outcome monitoring (draft approval gate, #985)

Metrics viewers can open `/nofos/metrics/readability-pilot` from **Other metrics**
on `/nofos/metrics`, including while the pilot is disabled. The page shows the
stored pilot flag, recording state, retained daily/weekly attempts, all-attempt
success and capacity rates, nearest-rank durations, outcome meanings, and pages
of 50 recent attempts. JSON uses the same permission and `private, no-store`.
No OpDiv or user attribution is possible. It is a support trend source, not an
infrastructure alarm or evidence that #970's safeguards are deployed.

Recording is separately default-off via
`PDF_READABILITY_ATTEMPT_RECORDING_ENABLED=false`, including disabled POSTs.
Do not turn it on before privacy approves notice wording and a retention window
in #968, and operations configures and verifies cleanup. The proposed 13 months
is **not approved** or a code default. No public privacy notice is changed here.
Set `PDF_READABILITY_ATTEMPT_RETENTION_DAYS` to the agreed positive number of days
only after approval. The management command
`python manage.py cleanup_pdf_readability_attempts --dry-run` previews deletion;
without `--dry-run` it deletes older rows. It refuses an unset/invalid window.
This change installs **no schedule**: operations must agree on a cadence and
schedule this command through the deployment's existing job mechanism, verify
the effective cutoff, and record ownership/evidence in #968 before recording.

When enabled, each handled upload POST stores only a timestamp, outcome,
returned HTTP status and processing duration, plus Django's internal row ID.
No filename, document hash/size/pages/text/signals/metrics, request headers,
IP address, session or user ID is stored. The application inserts rows only;
they are not registered for admin editing or exposed through a write API.
Recording runs after the analysis slot releases. Database failure leaves the
response unchanged and emits only a fixed warning, without exception details.
The duration ends before the database write. GETs, CSRF rejections and upstream
rejections are not upload-analysis outcomes and are not counted; unexpected
uncaught framework failures also remain outside this bounded catalog. Thus
the literal “every POST” acceptance criterion requires that explicit scope
agreement before merge. A disabled route records `disabled` only when recording
has separately been approved/enabled. Zero records with recording disabled is
not evidence of zero use. Retention cleanup concurrent with a page read may
briefly make aggregates differ; refresh for a new snapshot.

Track remaining enablement work in [#968](https://github.com/HHS/simpler-grants-pdf-builder/issues/968).
Reuse the [source-based safeguards inventory](PDF_READABILITY_SAFEGUARDS.md)
and [deployment verification checklist](PDF_READABILITY_RELEASE_CHECKLIST.md)
to record target-environment evidence. Neither document grants approval to enable
the route or certifies current deployment settings.

`HHS_NOFO_PDF_METRICS_PILOT_ENABLED` defaults to false. Keep it off in shared
environments until the checks below are complete. This application change does
not install ingress rate limiting or authorize production enablement.

## Loose NOFO recognition (#969)

The launch approach is a deliberately loose NOFO check, not approved-template
recognition. Before analysis, the bounded worker inspects descriptive PDF
metadata and extractable text from the first two pages for four distinct
signals: an HHS agency or division in metadata, a labeled opportunity number, a
labeled Assistance Listing number, and a Grants.gov reference. Any two signals
allow analysis. Repeating one signal in multiple fields does not increase the
count, and filename alone never counts.

The field shapes are grounded in the [Simpler.Grants.gov Opportunities v1
OpenAPI examples](https://api.staging.simpler.grants.gov/docs#/Opportunity%20v1/post_v1_opportunities_search):
`ABC-123-XYZ-001` for `opportunity_number` and `43.012` for
`assistance_listing_number`. Its Assistance Listing search filter accepts two
digits, a period, and two or three alphanumeric characters, including documented
examples such as `45.C9` and `45.1C9`; its search documentation also shows the
longer opportunity number `EPA-R9-SFUND-23-003`. The pilot uses this contract as
a format reference only; upload processing does not call the Simpler.Grants.gov
API or send document-derived values to another service.

This gate is modest abuse deterrence for the unlinked public pilot. It can admit
an unrelated document that contains two signals and can reject an unusually
formatted NOFO that contains fewer than two. Passing means only "likely HHS
NOFO"; it is **not** template compliance, accessibility, policy, or clearance
approval. The policy and its threshold remain immutable application code in the
worker so they can be adjusted later without creating a classification service
or retaining uploaded content.

Recognition is independent of PDF tagging. A text-based untagged PDF can pass
and is then measured with the existing generic adapter and low-reliability
warning. A document with extractable text on the inspected pages but too few signals is
unsupported. If those pages have no extractable text, recognition is
indeterminate and the user is directed to run OCR. The analyzer still performs
its existing extraction checks after recognition; passing recognition does not
guarantee that enough text can be measured.

Release gates before enabling the anonymous route (merge is not approval to enable):

- Limit use to HHS NOFOs. Before calculation, require any two of the four loose
  recognition signals documented above. Do not use filename, require a template
  marker, or imply that recognition validates format. Test representative
  labeled variants, ordinary line wrapping, unrelated text, and image-only PDFs.
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
  safe or that files are never saved until those checks are complete. The
  [upload privacy notice](#upload-privacy-notice) is not that approval.
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

## Upload privacy notice

The upload page always shows a **Your file and your privacy** notice directly
above the file input. The page invites draft or published NOFOs and asks users to
follow their agency's rules for sharing pre-decisional content. There is one
version of this notice; it does not change when the pilot is enabled.

Every statement in the notice is limited to what the application code
establishes: the PDF is processed temporarily on HHS-operated systems, upload
processing does not call an outside service, and nothing is added to NOFO Builder
or kept as report history. The notice links to the
[HHS Privacy Policy](https://www.hhs.gov/privacy/privacy-policy/index.html) and
uses the same support path as the unavailable page: the user's agency grants
policy office, then the NOFO Builder Feedback Form.

The notice deliberately does not state a data classification, say that
pre-decisional use is approved, or promise deletion timing. Change that wording
only after the security/privacy approval and the logging and temporary-file
retention checks in the [safeguards inventory](PDF_READABILITY_SAFEGUARDS.md)
are recorded in #968.

## Measurement scope

Reuse the pinned `hhs-nofo-metrics` package. PDF results are extraction-based
estimates, not identical to Builder's semantic-HTML metrics or a compliance
determination. Untagged PDFs need particularly clear reliability caveats.

The dependency is pinned to 0.6.0. Builder-native HTML and authenticated DOCX
select HTML profile `hhs-nofo-fy27-html@0.5.0`; tagged PDFs select
`hhs-nofo-fy27-pdf-estimate@0.6.0`, and generic PDFs select
`hhs-nofo-fy27-generic-pdf-estimate@0.5.0`. These profiles opt into passive
classifier `0.4.0-provisional`, correcting unambiguous be contractions and the
`need`/`indeed` false positives. Ambiguous pronoun `'s` forms remain a known
limitation. Sentence-count rules, other metric formulas and targets are unchanged.

The update from Builder's prior 0.5.4 pin also includes the 0.5.5 tagged-PDF
table-cell continuation correction, through tagged adapter `0.1.7`. Therefore
extracted PDF content and resulting nonpassive estimates can change even though
the formulas did not. The passive-method tests compare identical extracted
sentences; they do not establish that every PDF result matches 0.5.4. In Builder's stored
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
