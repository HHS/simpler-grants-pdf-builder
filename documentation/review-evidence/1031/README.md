# Quiet PDF downloads and flush sticky captions

Historical evidence for [PR #1031](https://github.com/HHS/simpler-grants-pdf-builder/pull/1031),
merged October 5, 2026 as `baa2b29a`. Context reconstructed October 28, 2026 from
the PR: actual templates and JavaScript in Chrome with a synthetic local NOFO and
simulated PDF/metrics responses. Screenshot links in the PR pin source at
`2f6ddf220958cdaaa35bcbda1683bff965d8c078`. The original capture date was not
recorded separately; these are local review examples, not production captures.

- [Download in progress](download-in-progress.png): no additional progress text.
- [Completed, panel collapsed](download-success-collapsed.png): saved heading updates without a new success message.
- [Completed, panel expanded](download-success-expanded.png): existing automatic-save notice and history show saved results.

The PR reports desktop/narrow-width/larger-text scrolling checks and 53 passing
JavaScript tests. It supersedes #1030's added download-message behavior. No new
validation was performed while adding this README. See
[current checkpoint guidance](../../readability/READABILITY_METRICS.md); historical
captures alone do not establish current deployed behavior.
