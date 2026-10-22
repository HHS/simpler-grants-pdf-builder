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

## Independent review follow-up: exact qualified Unrestricted label

The independent Astra review identified that the issue's full qualified
Unrestricted label uses curly single quotes around
`‘Additional Information on Eligibility’`, whereas the vocabulary supported
only the curly-double-quoted wording observed in the separate HRSA-26-747
export. The exact issue example therefore caused a whole-candidate no-op.

An independent hard-coded fixture now includes the complete issue label, rather
than deriving it from the implementation's vocabulary. Before the fix, two
regression tests failed in four subtests: direct repair, the shared processing
entry point, actual HTML upload and actual DOCX upload all produced no list
(exit 1). The fix adds only the exact curly-single-quoted label alongside the
existing curly-double-quoted label. Source wording is unchanged; there is no
general quote normalization or fuzzy matching. Straight/mismatched quotes,
changed qualification wording and added punctuation retain whole-candidate
no-op coverage. Both supported spellings have independent literal fixtures.

The exact issue label is tested alongside State governments through actual
HTML/DOCX import and re-import, with domestic definitions and restrictions kept
outside the list. Direct/core checks also verify idempotence. This synthetic
coverage does not depend on retrieving the original HRSA document; no original
document requirement or review blocker is introduced. Editor Tasks was re-read:
TASK-LIST-REVIEW already describes the bounded vocabulary and conservative no-op
behavior, so this spelling correction needs no navigation or task changes.

Follow-up focused eligibility/shared-core/characterization suite: 37 tests pass,
exit 0; changed-file Black/isort and `git diff --check` pass. The follow-up full
suite is running at this commit; its outcome is not yet established by this note.


## Visual review scenarios — actual NOFO Builder

These replace the standalone HTML comparisons from commit `108c03d`. All ten
screenshots are unaltered full-page captures of the real NOFO Builder subsection
editor's **Preview** tab in Chrome, served locally from this PR with an isolated
SQLite database. No production data or production Builder records were changed.
The application logic is unchanged from `a681fed`; later commits add evidence only.

### Setup and scope

Five clearly synthetic Word fixtures are included beside the screenshots.
Each was submitted as a DOCX upload through `nofos:nofo_import` using Django's
request client and a test-only user. This exercises the real Word conversion,
shared processing, persistence, and rendered Builder UI; upload requests were
programmatic, rather than clicks in the browser's file picker.

For **Before**, only `repair_eligibility_organization_lists` was temporarily
replaced with an identity function during that upload request using an in-memory
mock. This isolates the missing-bullets behavior without the new rule; it is not
a screenshot of a separately deployed older release. No persisted content was
manually rewritten to manufacture the result.

For **After**, the same fixture was imported with the normal, unmodified PR
processor, then submitted again through `nofos:nofo_import_overwrite` to exercise
re-import. The browser subsequently opened those persisted records and selected
Preview. All ten screenshots were visually inspected. Saved content comparisons
confirm that only scenarios 01 and 05 gain three organization bullets; 02–04
remain unchanged. Definitions and restrictions stay outside repaired lists.

### Before and after

| Scenario | Before | After |
| --- | --- | --- |
| Recognized categories — bullets restored | [Before](scenarios/01-success-before.png) | [After](scenarios/01-success-after.png) |
| Later restriction list — organization block unchanged | [Before](scenarios/02-later-restriction-list-before.png) | [After](scenarios/02-later-restriction-list-after.png) |
| Unfamiliar Others category — entire block unchanged | [Before](scenarios/03-unknown-category-before.png) | [After](scenarios/03-unknown-category-after.png) |
| Straight quotes in Unrestricted — entire block unchanged | [Before](scenarios/04-straight-quotes-before.png) | [After](scenarios/04-straight-quotes-after.png) |
| Supported alternative intro — bullets restored | [Before](scenarios/05-intro-variant-before.png) | [After](scenarios/05-intro-variant-after.png) |

Scenario 04 uses straight double quotes in its Word source. Builder's Markdown
preview renders those as curly quotes, so their source spelling is not visually
apparent in the Preview screenshot. The source fixture retains straight quotes;
the import repair still skips that category. This makes the UI consequence more
subtle than the earlier standalone rendering suggested.

These synthetic fixtures establish behavior for the review scenarios, not the
frequency of those shapes in untouched Announcement Module exports. The Others
wording is illustrative. They do not establish the original export defect or
replace representative-source validation. No PDF was generated. Anchore fixes
remain separate from this evidence-only update.
