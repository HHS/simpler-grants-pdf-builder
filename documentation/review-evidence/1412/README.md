# Word downloads for readability metrics

Tracking issue [#1412](https://github.com/HHS/simpler-grants-pdf-builder/issues/1412).
Captured November 20, 2026 in desktop Chrome against local Django. The before
screens use upstream main at `d8aaa657`. The after screens use
`codex/readability-word-download`.

| Surface | Before | After | Word report rendering |
| --- | --- | --- | --- |
| Readability Checker results after uploading a synthetic Word file while signed out | [Before](checker-before.png) | [After](checker-after.png) | [Checker](checker-word-report.png) |
| Readability metrics panel on a synthetic NOFO edit page | [Before](builder-before.png) | [After](builder-after.png) | [Builder](builder-word-report.png) |

Both download actions use the existing Word export progress dialog. See
[Checker progress](checker-word-progress.png), [Builder progress](builder-word-progress.png),
and [Builder conversion error](builder-word-error.png). Both dialogs closed on
success. The simulated error could be dismissed while keeping the metrics open.

The two browser downloads used the app's real export views and report template
with a local LibreOffice converter in place of GrabzIt. The renderings show the
downloaded DOCX files. The Checker report contained only scores, labels, and a
general scope note. The Builder report also contained the sample NOFO title and
opportunity number. Neither download contained the sample filename or body text.
Live GrabzIt conversion and production rendering remain to be verified.

To reproduce, use a local app with synthetic data, enable readability for each
surface and the readability Word export switch, and substitute a local DOCX
converter at the GrabzIt client boundary. Open each surface and download the
metrics report. See [Word export behavior and rollout](../../DOCX_EXPORT.md#readability-metrics-reports).
