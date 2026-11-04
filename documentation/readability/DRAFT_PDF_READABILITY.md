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
five pages and in descriptive metadata. An agency name in opening-page text can
replace agency metadata lost in print exports, but never counts twice. A blank content guide can lack those
signals. A rejection is not a finding that it is unrelated to HHS, and OCR does
not supply missing identifiers. Use an identifiable draft with genuine available
details; do not invent identifiers to obtain a report.

## Validation limits

Controlled synthetic tests establish specific extraction and recognition behavior.
They do not establish accuracy for every real Word-to-PDF conversion, independently
verified real-source reading order or parity across all five metrics. Nested
semantic blocks within table cells remain a documented limitation. Direct Word
support does not establish parity with Word-to-PDF exports.

[#1059 was closed on October 26, 2026 with these limitations accepted](https://github.com/HHS/simpler-grants-pdf-builder/issues/1059#issuecomment-6424519352).
Closure does not establish complete draft-format validation or public-release or
clearance approval. Historical experiments, package versions and remaining
coverage gaps are preserved in the [characterization record](../review-evidence/draft-readability-1059/characterization.md)
and [browser verification](../review-evidence/draft-readability-1059/README.md).
