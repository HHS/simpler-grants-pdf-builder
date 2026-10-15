# Word readability uploads (#1111)

Synthetic local checks, October 15, 2026. No real NOFO content is included.

## Design and reuse

Add DOCX input to the existing public and restricted upload workflow, not a new
screen/service or a saved Builder import. Keep the legacy Python function names,
form field and flag/permission names to avoid unrelated compatibility churn.
The existing isolated worker, time/resource limits, global slot, error boundary,
content-free accounting and report/copy/print controls are reused. PDF formulas
and processing remain unchanged. Word uses installed Mammoth, the existing pure
Word transform and XML declaration guard, existing loose recognition, and the
existing HTML measurement profile. No package or dependency was added.

Word measurement intentionally does not apply Builder's full import style map,
introductory-page cleanup, template instruction cleanup or persisted export
projection. Reports disclose that difference instead of promising parity.

## Screenshots and browser verification

The real in-app-browser file picker selected a synthetic DOCX containing a heading,
multiple paragraphs, bullet list, table and footnote. Actual POST/worker processing
returned a Word-specific report. Copy metrics displayed its successful confirmation.
The source label, measurement version, five metric cards, scope, disclaimer and
source caveats are visible. No fabricated PDF pages or PDF-tag extraction claim
appears in the Word report. At 390px, document width equals viewport width.

- [Upload form](upload.jpg)
- [Actual Word report](report.jpg)
- [390px report](report-mobile.jpg)
- [Browser print-media styling](report-print.jpg)

Print-media inspection hides banner, footer and action buttons. This screenshot
is a print-style preview, not evidence of a native Save as PDF dialog or a
downloaded PDF's pagination. Existing JavaScript tests verify that the print
button invokes `window.print`, expands notes and restores their state. No
production/deployed test, accessibility-conformance or clearance claim is made.
Viewport and media emulation were reset after checking. The local isolated
SQLite database enabled only the public flag for synthetic browser testing;
no shared environment flag changed.

## Independent review

An independent reviewer found a validation bypass where relationships could
select XML content under a non-XML filename. The fix scans every bounded archive
member for declarations and validates the selected root relationship, rather
than validating an unused canonical decoy. Regression tests cover DATA/XML
alternate parts, declarations, duplicate members, expanded/entry limits, macros,
malformed/non-NOFO/empty files, disabled external access and cleanup on timeout.
The reviewer rechecked the fix, independently passed 68 focused tests and
verified structured conversion and equality with direct HTML-profile metrics.
No outstanding code blockers were reported. Suite counts overlap.

The permanent synthetic fixture and structured round-trip assertions are in
`nofos/nofos/tests_nofos/test_word_readability.py`. Application tests exercise real
public and authorized authenticated Word POSTs, including no saved NOFO and
content-free attempt records. Existing PDF tests remain in place.
