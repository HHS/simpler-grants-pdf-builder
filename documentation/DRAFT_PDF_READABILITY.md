# Readability checks during drafting

The PDF checker can process a text-based HHS NOFO draft before publication design.
That means the file can receive estimates, not that every Word-to-PDF export has
been validated or that the draft satisfies clearance guidance. The authenticated
pilot remains restricted to approved users. Public-pilot activation is separate.

## Choose the content to measure

The direct PDF path measures recovered text. It does not run Builder's Word import
cleanup or automatically distinguish writer-only notes from applicant-facing
instructions. Complete sentences in writer notes, including tagged table cells,
can affect sentence-based scores. Placeholders and other fragments can increase
word count even when they do not contribute to sentence-based calculations.

For an applicant-facing check, export a working copy without writer-only notes or
template prompts. Preserve instructions applicants need. Compare versions with
the same measurement scope. Shorter or incomplete drafts are not necessarily
closer to publication readiness. Review the reported reliability and denominators.

Recognition currently checks distinct NOFO identification signals on the first
two pages and in descriptive metadata. A blank content guide can lack those
signals. A rejection is not a finding that it is unrelated to HHS, and OCR does
not supply missing identifiers. Use an identifiable draft with genuine available
details; do not invent identifiers to obtain a report.

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

Two reproducible gaps prevent a general draft-export parity claim:

- **Cross-page table-cell sentence scope.** With package 0.5.4, the same reference
  prose tagged as table cells loses its four-word opening fragment when a
  sentence continues onto the next page. Recovered word count stays 23, but
  sentence word count falls from 17 to 13, words per sentence from 5.67 to 4.33,
  and grade level from 1.20 to -1.19. The report warns about excluded fragments
  but still labels reliability high. The adapter merges cross-page body/list
  blocks, not table blocks. A characterization test records this current
  limitation, not desired behavior; update it when the package is repaired.
- **Conversion-dependent recognition.** One private source's LibreOffice PDF
  was accepted with agency metadata plus an opportunity number. Word for Mac's
  local Print > PDF > Save as PDF output from that source was rejected because
  it retained only the opportunity-number signal. Both have 38 pages; the print
  output has no structure tree. This is a recognition comparison, not a metric
  accuracy comparison. The online accessibility export was not used. Agency
  names in visible page text currently do not substitute for agency metadata.

The wrapped and cross-page synthetic fixtures were rendered and every page
visually inspected. A representative table page of the private Word print
output was inspected locally. Private content and screenshots are not committed.

Six private sources were converted locally with packaged LibreOffice. Five were
recognized and returned low-reliability tagged estimates; one instruction-heavy
guide lacked sufficient identification signals. Tags alone do not establish
reading-order accuracy. These observations informed synthetic coverage, but do
not establish metric accuracy for the source documents.

The experiments used metrics package 0.5.4, tagged adapter 0.1.6, tagged profile
0.5.0, and generic profile 0.4.0, as pinned by Builder. Representative source
pages were inspected privately. No source files, identifying details, or source
scores are committed here.

Issue #1059 remains open for independently checked extraction from real conversion
paths, equivalent-prose Word exports, multipage paragraphs and lists, confirmed
Announcement Module provenance, and applicable FY27 clearance guidance. No
recognition thresholds, formulas, authorization controls, or deployment flags
change in this slice. Do not describe this as complete draft-format validation.
