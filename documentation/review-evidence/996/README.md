# Metadata spacing without a tagline

Historical evidence for [PR #996](https://github.com/HHS/simpler-grants-pdf-builder/pull/996),
merged September 30, 2026 as `c154b414`. This context was reconstructed October 28,
2026 from the PR and Git history; the original capture date and environment were
not recorded in this folder. No new capture or validation was performed.

- [Before](before.jpg): agency metadata runs into the first content heading when the tagline is absent.
- [After](after.jpg): the empty-tagline state receives the intended bottom spacing.

The PR reports rendering/CSS regression checks and a passing Django suite. These
screenshots illustrate the reviewed layout; they do not establish current deployed
behavior or every theme. See [tagline behavior](../../TAGLINE_IMPORT.md) for current guidance.
