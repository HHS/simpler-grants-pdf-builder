# Draft readability characterization and limitations

Historical investigation and integration evidence for [#1059](https://github.com/HHS/simpler-grants-pdf-builder/issues/1059)
and [PR #1060](https://github.com/HHS/simpler-grants-pdf-builder/pull/1060).
Experiments were performed in October 2026; the integrated source baseline was
`0ef39ee7`. This record preserves the reported results, rather than claiming a new
validation run. See the [capture record](README.md) and
[current drafting guidance](../../readability/DRAFT_PDF_READABILITY.md).

## Characterization tests

`nofos/nofos/tests_nofos/draft_pdf_fixtures.py` builds synthetic PDFs with fixed
applicant prose, separate identifier headings, and source-declared block tags.
There is no private source content in these fixtures. Minimal tagged fixtures
test extraction semantics; they are not PDF/UA conformance examples.

The reference has 17 prose words, three sentences in two paragraphs, 21 manually
counted syllables, and one passive sentence. Identifier headings contribute six
additional recovered words. The expected values are 23 recovered words, 5.67
words per sentence, 1.5 sentences per paragraph, grade 1.20, and 33.33% passive
sentences. Grade follows `0.39 * (17 / 3) + 11.8 * (21 / 17) - 15.59`.
Rounded numerical measures use a 0.005 tolerance through two-place assertions;
counts and paragraph ratios are checked exactly.

Controlled variants characterize ordinary font changes, retained writer notes,
notes in a table cell, placeholder fragments, sparse drafts, and untagged output.
Wrapped paragraphs and source-declared paragraphs or list bodies continued across
pages preserve all five reference measures. The multipage fixtures use marked
content references under one structure element, with list and table ancestry.
They do not cover every Word tag structure or establish full table conformance.
Both entry points reuse the same worker, report template, and copy behavior.
Authenticated integration tests use the real subprocess worker while retaining
the per-user permission check and disabled public route.

## Evidence limits and remaining investigation

The October 7 validation found two gaps. This branch repairs recognition;
the direct table-cell continuity repair was first adopted with metrics 0.5.5
and is retained through current main’s 0.6.0 dependency:

- **Cross-page table-cell sentence scope.** With package 0.5.4, the same reference
  prose tagged as table cells loses its four-word opening fragment when a
  sentence continues onto the next page. Recovered word count stays 23, but
  sentence word count falls from 17 to 13, words per sentence from 5.67 to 4.33,
  and grade level from 1.20 to -1.19. The report warns about excluded fragments
  but still labels reliability high. The adapter merges cross-page body/list
  blocks, not table blocks. Package 0.5.5 restores all five controlled reference
  measures for the same directly tagged cell continued across pages. The test
  now checks parity instead of retaining the old defect as its expectation.
  Distinct cells remain separate. Cells with nested paragraphs or headings stay
  page-local because the resolver does not expose their individual identities;
  this includes one nested paragraph that spans pages. Inline spans can join.
- **Conversion-dependent recognition.** One private source's LibreOffice PDF
  was accepted with agency metadata plus an opportunity number. Word for Mac's
  local Print > PDF > Save as PDF output from that source was rejected because
  it retained only the opportunity-number signal. Both have 38 pages; the print
  output has no structure tree. This is a recognition comparison, not a metric
  accuracy comparison. The online accessibility export was not used. Agency
  details appear on page three. The revised bounded five-page check now accepts
  this output using agency page text plus opportunity number. It receives the
  generic profile and low-reliability warning, not a tagged-accuracy claim.

The wrapped and cross-page synthetic fixtures were rendered and every page
visually inspected. A representative table page of the private Word print
output was inspected locally. Private content and screenshots are not committed.

Six private sources were converted locally with packaged LibreOffice. Five were
recognized and returned low-reliability tagged estimates; one instruction-heavy
guide lacked sufficient identification signals. Tags alone do not establish
reading-order accuracy. These observations informed synthetic coverage, but do
not establish metric accuracy for the source documents.

The initial experiments used metrics package 0.5.4 and tagged adapter 0.1.6.
The October 7 follow-up used 0.5.5 with tagged adapter 0.1.7. After integration
with current main, Builder retains metrics 0.6.0, tagged adapter 0.1.7, tagged
profile `hhs-nofo-fy27-pdf-estimate@0.6.0`, and generic profile
`hhs-nofo-fy27-generic-pdf-estimate@0.5.0`. The 0.5.5 table repair is already
included in 0.6.0. Corrected passive profiles from #1123 remain selected; this
branch does not revert their behavior. Representative source pages were
inspected privately. No source files, identifying details, or source
scores are committed here.

Issue #1059 was closed on October 26, 2026 after acceptance of the delivered
scope and documented limitations. Independently checked real-source extraction,
equivalent-prose Word-to-PDF comparisons, and broader multipage coverage remain
unverified; closure did not establish completion of those checks.
FY27 clearance-guidance verification is outside scope and is not a tracked
follow-up. Announcement Module provenance is handled manually by the team and
is outside the tracked follow-ups for this work. No
recognition thresholds, formulas, authorization controls, or deployment flags
change relative to current main in this slice. Do not describe this as complete
draft-format validation.

Authenticated Word uploads from #1112 and the Word scope/reliability guidance
from #1170 remain available. The PDF-specific preparation notice appears only
on PDF reports; the draft-readiness notice applies to both formats. Existing
Word guidance, absent-rating behavior, copy/print controls, and public PDF-only
restrictions are preserved. Direct Word support does not establish parity with
Word-to-PDF exports. Browser captures below the review-evidence directory are
historical October 7 evidence, not new verification of the integrated branch.
