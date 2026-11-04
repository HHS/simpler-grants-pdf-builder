# PDF-download checkpoint refresh and sticky captions

Historical evidence for [PR #1030](https://github.com/HHS/simpler-grants-pdf-builder/pull/1030),
merged October 5, 2026 as `85bf5f03`. Context reconstructed October 28, 2026 from
the PR: a synthetic local example at the same viewport/scroll position compared
production styling with the proposed caption positioning. The original capture
date was not recorded separately. No new verification was performed.

- [Before](sticky-caption-before.png): the section caption is obscured by the toolbar.
- [After](sticky-caption-after.png): the caption clears the toolbar and readability hint.

The PR reports Chrome checks with rendered templates and stubbed PDF/metrics
responses, plus Python/JavaScript tests. #1031 subsequently changed the caption
offset and removed the new download status messages; see its
[evidence record](../1031/README.md). These captures preserve the #1030 state and
must not be used as the current status-message specification. Current checkpoint
behavior is described in [readability metrics](../../readability/READABILITY_METRICS.md).
