# Eligibility organization bullets — issue #1190

## Evidence and limits

The Announcement Module checkbox export omission is requester-reported. The
issue records that `Foa_Content_of_HRSA-27-033.docx` has 15 native bullet
paragraphs and is an existing-list/no-op fixture, not a reproduction of missing
bullets. That file was not present in Downloads or the inexpensive task-scoped
temporary-file search during this implementation. Its actual converted HTML
has therefore **not** been verified here. Do not claim source formatting loss
or original-file validation from the issue's XML description.

A different existing file, `Foa_Content_of_HRSA-26-747 (1) (1).docx`, was inspected
read-only with the current Word conversion entry point on main `8d43eee1`.
The Eligibility H2 / Types of eligible organizations H3 / canonical introductory
paragraph are followed by plain category paragraphs. That block includes an
unreviewed **Others** category and a genuine restriction list after the domestic
definition/additional-eligibility label, before the next peer H3. It deliberately
remains unchanged under both the unknown-category and existing/mixed-list policy.
This is evidence of an unsupported source shape, not evidence that Builder lost
native bullets. Neither original document is committed or rewritten.
Running the new repair directly against that converted source was an exact
HTML no-op (string comparison before/after).

## Approved ambiguity policy

The shared framework-independent content processor is the reusable repair
boundary; native DOCX conversion has already finished. Three exact affirmative
intro patterns plus an active Eligibility heading and the targeted organization
heading are independent evidence. Only complete reviewed category labels qualify.
No unrestricted fuzzy matching, category-word heuristics, first/last endpoint
assumption or agency inference is used.

Unknown substantive paragraphs cannot reliably be classified as prose versus
unfamiliar categories. They cause a whole-candidate no-op. Only an explicit
reviewed domestic-definition prefix or additional-eligibility label safely stops
paragraph scanning. Headings, tables and document end are structural stops.
Existing ordered or unordered lists anywhere in the subsection cause a whole
subsection no-op, even if they appear later in restrictions. This intentionally
favors leaving unsupported material visible for human correction over silently
making a partial list. Future vocabulary/boundary expansion needs representative
source evidence and reviewed fixtures.

## Verification

`test_eligibility_list_import.py` uses only clearly synthetic HTML and in-memory
DOCX fixtures. The DOCX variants differ only in whether category paragraphs have
native bullets; the unbulleted variant is positive repair coverage, not a claim
to reproduce the unavailable HRSA-27-033 source.

Coverage includes actual HTML/DOCX upload and repeated re-import, native-list
no-op, shared Composer/Compare upload, idempotence, reordered/subset lists,
recognized vocabulary, explicit intro variants, NBSP/case/asterisk normalization,
negation/unrelated/missing-context no-ops, unknown-category/prose partial-list
rejection, mixed-list no-op, document/heading/table stops, retained restrictions,
rich emphasis, external links and referenced bookmark targets. Existing text,
attributes and blank separators are not reconstructed by the repair. Ordinary
page reads do not apply another transformation.

The coordinating agent performed actual Chrome upload of the synthetic
unbulleted Word fixture, completed naming and inspected the editor: exactly two
bullets, with the domestic definition, additional-eligibility label and
individual restriction outside the list. It then used **NOFO actions →
Re-import** to upload the synthetic native-bullet fixture and verified the same
two-item structure and exclusions. The implementation agent inspected both
screenshots: [import](import.jpg), [re-import](reimport.jpg). This is editor UI
evidence, not a generated PDF or original HRSA document comparison.

Local checks: full suite from `nofos/`, `DEBUG=False`, isolated SQLite test DB:
2,739 tests, 3 skipped, exit 0. After adding the final ordinary-save check and
explicit embedded-comment no-op guard, 33 focused eligibility/shared-processing
tests pass, exit 0. The coordinating agent runs the combined final regression.
Changed-file Black and isort checks pass. Repository-wide checks report existing, untouched formatting failures in
`policy_language.py`, `test_metrics.py`, and `test_policy_language.py` (Black),
and `test_policy_language.py` (isort); these unrelated files were not reformatted.
No PDF service or Word-export request was made.
