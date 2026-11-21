# Word downloads for readability metrics

Tracking issue [#1412](https://github.com/HHS/simpler-grants-pdf-builder/issues/1412).
Captured November 20, 2026 in desktop Chrome against local Django. The before
screens use upstream main at `d8aaa657`. The after screens use
`codex/readability-word-download`.

| Surface | Before | After | Word report rendering |
| --- | --- | --- | --- |
| Readability Checker results after uploading a synthetic Word file while signed out | [Before](checker-before.png) | [After](checker-after.png) | [Checker](checker-word-report.png) |
| Readability metrics panel on a synthetic NOFO edit page | [Before](builder-before.png) | [After](builder-after.png) | [Builder](builder-word-report.png) |

The Checker uses **Download Word** as the primary action and offers **Copy
metrics** alongside it. Both Word actions use the existing export progress dialog. See
[Checker progress](checker-word-progress.png), [Builder progress](builder-word-progress.png),
and [Builder conversion error](builder-word-error.png). Both dialogs closed on
success. The simulated error could be dismissed while keeping the metrics open.

The two browser downloads used the app's real export views and report template
with a local LibreOffice converter in place of GrabzIt. The renderings show the
downloaded DOCX files. The Checker report contained only scores, labels, measurement counts, and a
general scope note. The Builder report also contained the sample NOFO title and
opportunity number. Neither download contained the sample filename or body text.
Live GrabzIt conversion and production rendering remain to be verified.

To reproduce, use a local app with synthetic data, enable readability for each
surface and the readability Word export switch, and substitute a local DOCX
converter at the GrabzIt client boundary. Open each surface and download the
metrics report. See [Word export behavior and rollout](../../DOCX_EXPORT.md#readability-metrics-reports).

## Standalone report variations

The Checker shows the same **Download Word** action to everyone who can use
the tool. A signed-in session and a signed-out session downloaded a report
for the same synthetic Word upload. The HTML sent for conversion was identical
in both sessions. See the [signed-out actions](checker-after.png) and
[signed-in actions](checker-signed-in.png).

These single-page examples use synthetic analysis results passed through the
same standalone report template and rendered with the local converter.

| Result | What the report shows |
| --- | --- |
| [Word with recognized exclusions](scope-examples/word-with-exclusions.png) | A short explanation of the recognized content the Checker skips. |
| [Word without recognized exclusions](scope-examples/word-without-exclusions.png) | A note that zero words were recorded as skipped in those categories. |
| [Tagged PDF](scope-examples/tagged-pdf.png) | Extraction via structure tags and the number of pages with extractable text. |
| [Layout-based PDF with partial coverage](scope-examples/layout-pdf-partial.png) | Reconstruction from layout and the proportion of pages with extractable text. |

The [earlier limited-counts example](scope-examples/pdf-limited-counts.png)
was generated from a synthetic payload that omitted the count of pages with
extractable text. A successful analysis in the current PDF worker supplies
that page count. Sentence counts can still be unavailable independently.

## Follow-up: signed-in details, not-saved note and Document check

After the evidence above was captured, the Checker report changed. The
screenshots above show the earlier report. Signed-in Checker reports now add the
file name and recognized opportunity number, or **Opportunity number: Not
found** when no labeled number was recognized. Signed-out reports omit them and
add a note that the document was not saved. All reports add a **Document check**
section. See [Standalone Checker report content](../../DOCX_EXPORT.md#standalone-checker-report-content).
Automated coverage: `test_signed_in_checker_report_adds_document_details` and
`test_document_check_reports_recognized_template_parts` in
`nofos/nofos/tests_nofos/test_readability_word_export.py`.

## Signed-in identifiers and download button

The [signed-in Word report](checker-signed-in-word-report.png) shows the
opportunity and Assistance Listing numbers detected in a synthetic Word upload.
The report excludes the upload filename. Chrome downloaded it through the app's
export view with LibreOffice standing in for GrabzIt. Both readability download
buttons were disabled during the request and re-enabled after success. The
Checker button also recovered after a simulated conversion failure.

## Expired-results recovery

Chrome rendered the actual Word download dialog for a simulated expired
response on the [Readability Checker](checker-word-expired.png) and in the
[NOFO Builder panel](builder-word-expired.png). Each dialog explained how to
get fresh results and dismissed with **OK**. A simulated converter failure
still displayed the generic retry message. Django tests separately verified
that genuinely expired signed reports return HTTP 410 without contacting
GrabzIt, and JavaScript tests verified the messages and heading reset.

See the [UI pattern](../../UI_PATTERNS.md#expired-readability-downloads) for the
current wording and recovery behavior.
