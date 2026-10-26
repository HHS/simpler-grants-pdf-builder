# Word readability uploads (#1111)

Synthetic local checks, October 15, 2026. No real NOFO content is included.

## Design and reuse

Add DOCX input to the existing authenticated `/nofos/readability/` workflow, not a new
screen/service or a saved Builder import. Keep the legacy Python function names,
form field and flag/permission names to avoid unrelated compatibility churn.
The existing isolated worker, time/resource limits, global slot, error boundary,
content-free accounting and report/copy/print controls are reused. PDF formulas
and processing remain unchanged. Word uses installed Mammoth, the existing pure
Word transform and XML declaration guard, existing loose recognition, and the
existing HTML measurement profile. No package or dependency was added. The public
`/readability/` route remains PDF-only, with its existing gates unchanged.

Word recognition reuses the existing two-distinct-signal gate. For templates
without filled identifiers, HHS agency context plus an explicit NOFO title or
template label can supply one compound signal; another signal, such as Grants.gov,
is still required. The `HHS-wide` master-template label is recognized. File names
are not evidence, and PDF recognition is unchanged.

Word measurement intentionally does not apply Builder's full import style map,
introductory-page cleanup, template instruction cleanup or persisted export
projection. Reports disclose that difference instead of promising parity.

## Screenshots and browser verification

After login to the authenticated route, the real in-app-browser file picker selected
a synthetic DOCX containing a heading,
multiple paragraphs, bullet list, table and footnote. Actual POST/worker processing
returned a Word-specific report. Copy metrics displayed its successful confirmation.
The source label, measurement version, five metric cards, scope, disclaimer and
source caveats are visible. No fabricated PDF pages or PDF-tag extraction claim
appears in the Word report. Missing reliability evidence is explicitly shown as
not assessed, without inventing a low or high rating. The shared-formula comparison
explanation appears once, and the Word alert covers extraction limitations.
At 390px, document width equals viewport width. Computed heading and alert fonts
were Merriweather Web and Source Sans Pro Web.

- [Upload form](upload.jpg)
- [Actual Word report](report.jpg)
- [390px report](report-mobile.jpg)
- [Browser print-media styling](report-print.jpg)
- [Authenticated PDF regression report](pdf-regression.jpg)

A synthetic PDF was also selected through the same authenticated browser file
picker and returned its PDF report, including page coverage and the existing
generic-extraction low-reliability warning. The browser was then returned to the
synthetic Word report.

Print-media inspection hides banner, footer and action buttons. This screenshot
is a print-style preview, not evidence of a native Save as PDF dialog or a
downloaded PDF's pagination. Existing JavaScript tests verify that the print
button invokes `window.print`, expands notes and restores their state. No
accessibility-conformance or clearance claim is made.
Viewport and media emulation were reset after checking. The local isolated
SQLite database enabled only the authenticated flag for these refreshed screenshots;
no shared environment flag changed. A local test user had the existing
`nofos.use_pdf_readability_pilot` permission.

Read-only deployed checks on October 15 confirmed that both dev and production
redirect signed-out requests for `/nofos/readability/` to login (302), while
`/readability/` returns 503. These checks do not establish signed-in deployed
permission behavior; the signed-in allowed/denied matrix is covered locally.

## Independent review

An independent reviewer found a validation bypass where relationships could
select XML content under a non-XML filename. The fix scans every bounded archive
member for declarations and validates the selected root relationship, rather
than validating an unused canonical decoy. Regression tests cover DATA/XML
alternate parts, declarations, duplicate members, expanded/entry limits, macros,
malformed/non-NOFO/empty files, disabled external access and cleanup on timeout.
The reviewer rechecked the fix, independently passed 68 focused tests and
verified structured conversion and equality with direct HTML-profile metrics.
The same independent reviewer checked the acceptance-criteria follow-up, found
the missing `HHS-wide` alias, and rechecked its fix. They independently passed
73 focused tests and reported no remaining actionable code findings. Suite counts
overlap.

The permanent synthetic fixture and structured round-trip assertions are in
`nofos/nofos/tests_nofos/test_word_readability.py`. Application tests exercise real
authorized authenticated Word POSTs, including no saved NOFO and content-free
attempt records. Both formats are blocked before analysis for signed-out users
and users without the existing permission. Public Word submissions are rejected
before analysis. Existing PDF tests remain in place, including preservation of
supplied PDF reliability ratings and explicit low reliability for generic PDF
extraction. Metrics without their own reliability rating do not inherit one.

## Acceptance-criteria evidence

| Requirement | Evidence |
| --- | --- |
| Existing upload/access gates; both formats | Authenticated upload tests and actual Word browser upload; public route stays PDF-only |
| Safe bounded DOCX parsing | Real worker tests for archive/type/entry/expanded-size, declarations, macros, malformed and empty inputs; external conversion access disabled |
| Shared metrics, no duplicated formulas | Existing HTML profile and metrics 0.5.4; synthetic structured equality test; PDF path unchanged |
| Authentication and permission | Signed-out/denied tests for both formats; authorized real worker test; deployed signed-out route probes above |
| Accurate Word scope/reliability | No page count; no invented reliability; PDF ratings retained; report screenshot and regression assertions |
| Whole-flow copy | Authenticated form/hint/accept, generic heading/title, errors, progress/completion and source-aware report assertions |
| Copy, print, retry, narrow layout | Browser copy confirmation; error/retry coverage; 390px reflow and print-media screenshots; existing print JavaScript tests |
| Regression/security/cleanup | Focused application/worker tests, isolated subprocess, timeout cleanup and content-free accounting assertions |
| Local verification, final review, CI | Refreshed synthetic screenshots, independent review and PR checks at the current head |

## Real-document execution checks

Eight available DOCX files were processed through the actual bounded worker:
three HRSA templates, the cleared HHS master, and four populated examples across
HRSA, CDC, ACF and ACL. All eight succeeded after the recognition adjustment,
including the four previously rejected templates. Local worker times ranged from
0.47 to 2.71 seconds. One previously rejected HRSA template also completed through
the authenticated browser workflow. These are execution checks, not validation
of metric accuracy or production performance. Real content, filenames, files and
screenshots are not committed or published.
