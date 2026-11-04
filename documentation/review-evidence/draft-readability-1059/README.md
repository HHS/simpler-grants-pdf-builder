# Draft readability scope verification

Local authenticated Chrome verification on October 7, 2026, against the branch
for #1059 with an isolated SQLite database and a synthetic pilot participant.
The public pilot was disabled throughout. No private source was uploaded in the
browser or included in screenshots.

- [Upload guidance](upload.jpg): expanded PDF requirements explain draft use,
  writer-note effects, and blank-template recognition limits.
- [Report](report.jpg): real synthetic upload through the subprocess worker;
  reference denominators and all five displayed values; draft scope and readiness
  caveats remain visible alongside the existing reliability warning.

The test fixture contains 17 applicant prose words and six heading words, with
three sentences, two prose paragraphs, 21 syllables, and one passive sentence.
This verifies the small controlled reference, not private-document accuracy.

- [Print-style recognition](print-recognition.jpg): authenticated Chrome upload
  of an untagged, synthetic four-page PDF without descriptive agency metadata.
  The opportunity number is on page one and agency name on page three. The
  subprocess returns a report with the expected low-reliability warning.
  Inferred paragraph boundaries differ from the tagged reference, so this does
  not establish five-metric parity for untagged exports.

After the recognition fix, the six local private exports retain their expected
recognition results: five supported and the blank guide unsupported. The real
Word print export also completes analysis. No private content is committed.

No application flags outside the isolated local database changed. No deployment
or clearance determination was made. See the [current drafting guide](../../readability/DRAFT_PDF_READABILITY.md) and
[historical characterization and matrix gaps](characterization.md).

## Released package adoption

[Cross-page table report](table-055.jpg) was captured from the authenticated local
Chrome route after adopting the published 0.5.5 wheel and tagged adapter 0.1.7.
The real subprocess processes both pages and restores all five controlled
reference values: 23 words, 5.7 words per sentence, 1.5 sentences per paragraph,
grade 1.2, and 33.3% passive sentences. Sentence scope contains 17 words and
three sentences. This fixture uses direct cell tags; nested semantic blocks
remain a documented limitation. Earlier screenshots identify their older
measurement version and are retained as prior evidence.

## Integration with main — October 26, 2026

Integrated main at `b3e23b2f33515fe28482108cff9a2016f9a88ca6` without
rewriting the PR history. The dependency, lockfile and PDF worker match main:
metrics 0.6.0, corrected passive profiles, and tagged adapter 0.1.7. The former
0.5.5 adoption is historical evidence; it is already included in 0.6.0.

The current authenticated Word upload support and Word scope/reliability
presentation remain intact. PDF preparation guidance is conditional on PDF
reports, while draft readiness applies to both formats. Copy behavior follows
the displayed guidance. Regression assertions exercise real PDF and DOCX
uploads using measurement version 0.6.0, the Word absent-rating explanation,
and disabled public access. Word recognition explicitly retains its prior
compound-context rule instead of inheriting the new PDF agency page-text vote.

The fetched main has two migration leaves, `0154_design_pilot_candidate` and
`0155_backfill_document_audit_index`. An empty merge migration joins them with
no database operations, allowing normal migration loading and test setup.
The prior-rollout test now temporarily removes and restores recorded descendant
migrations too, so the simulated older history remains consistent.

Validation on the integrated branch:

- Full Python suite: 2,862 tests completed successfully, with three existing
  skips, using Django’s four-process test runner.
- 136 focused Python checks passed, including real-worker fixtures, Word/PDF
  uploads, recognition boundaries, stored metrics, permissions and report scope.
- All 18 document-history checks passed, including the older-rollout simulation.
- All 57 JavaScript tests passed, including PDF/Word copied guidance.
- Poetry lock validation, touched-file pre-commit checks and whitespace checks
  passed. Migration drift check reports no changes.

The October 7 browser captures above were not recreated in this update. No
private-source extraction or conversion matrix was rerun. The remaining
accuracy limitations in the durable guide still apply. FY27 clearance-guidance
verification is outside scope and is no longer a tracked follow-up. Announcement
Module provenance is handled manually by the team and is no longer a tracked
follow-up for this work.
No public pilot setting or deployment was changed.

## Conflict resolution against updated main — October 26, 2026

Updated again to main at `0ef39ee7`. Main now contains the equivalent empty
merge migration, `0156_merge_20261026_1349`, and the descendant-aware
prior-rollout test. Retained those versions and removed this branch's redundant
`0156_merge_design_pilot_document_audit` migration so the migration graph has
one leaf. The conflict resolution introduces no database operations or changes
to editor instructions. Main's newer privacy, retention, and report changes
remain alongside the drafting guidance.

Validation after resolving the conflicts:

- Full Python suite passed: 2,867 tests, with three existing skips, using
  Django's four-process test runner.
- All 113 focused Python tests passed: document history, real-worker draft
  fixtures, PDF/Word recognition, authenticated uploads, and public boundaries.
- All 61 JavaScript tests passed.
- Migration drift, lockfile validation, formatting of the resolved test, and
  whitespace checks passed.

The historical browser captures and remaining accuracy limitations above still
apply; this update does not add browser or private-source validation.

## Issue disposition — October 26, 2026

[#1059 was closed with the delivered scope and limitations accepted](https://github.com/HHS/simpler-grants-pdf-builder/issues/1059#issuecomment-6424519352).
The broader real-conversion comparisons and independently verified real-source
extraction remain unverified. Closure adds no new validation or release approval.
