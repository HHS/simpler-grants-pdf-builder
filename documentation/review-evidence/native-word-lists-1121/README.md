# Native Word list verification

Issue: [#1121](https://github.com/HHS/simpler-grants-pdf-builder/issues/1121).
Verified locally on October 16, 2026. All source content is synthetic.

## What was exercised

- Uploaded `synthetic-native-lists.docx` through Chrome's real file chooser,
  using normal sign-in to an isolated local Builder account.
- Named the new draft, opened Activities in the subsection editor and selected
  Preview. Computed list styles were lower-alpha, lower-roman and decimal;
  the separate resumed alpha list had `start="3"`.
- Reimported the revised source through the actual Re-import action. The list
  content, markers, continuation paragraph and resumed numbering remained intact.
- Uploaded an unsupported custom-marker variant and verified successful import
  with **Check list numbering** guidance. Its computed heading matches the
  existing Source Sans Pro Web, weight 700 alert typography.
- Compared the source Word render with the actual generated PDF. All four final
  PDF pages were rendered and inspected, including the cover, contents, section
  cover and list page. The source render is one page.
- Generated `generated-test.pdf` using the existing `generate_nofo_pdf` service,
  with `test=True`, pipeline 11 and PDF/UA-1 request unchanged. Used DocRaptor's
  documented public test key, not account credentials. Static assets used the
  existing dev host as the service's base URL; no shared NOFO was uploaded or
  changed. The result identifies Prince 15.1, is tagged and contains test
  watermarks. Tagging is not an accessibility-conformance determination.

The minimal draft uses a text-only NIH theme and disables its generated
introduction to keep the test focused. Deadline placeholders and test watermarks
are intentional. This is not a complete or publishable opportunity. The local
record is `70563d9b-3d5e-4fed-9b16-285abe506b7b`, port 8913; it remains Draft.

## Independent review and compatibility

A separate implementation review found and verified fixes for loose-list
continuation, literal asterisks in table-cell lists, temporary-marker cleanup,
and preservation of legacy mixed-list/continuation repair. Final independent
focused run: 73 passing tests, with no remaining concrete findings. Earlier
independent compatibility and workflow runs passed 424 and 108 tests.

The module has 30 synthetic real-Mammoth tests. New persistence tests cover
Builder, Composer and Compare Word uploads, configured Markdown/sanitization,
nonblocking unsupported-marker guidance, and repeated reimport. Existing
checklist, note, anchor, ACF and legacy list behavior are retained by regressions.
Final local full suite ran 2,661 tests successfully with three existing skips;
the separately rerun four-test upload suite includes the subsequently added
actual Word upload through Composer and Compare. All 57 JavaScript tests and
pre-commit checks passed. Final CI results are recorded in the PR.

No runtime dependencies, CSS fallback, sanitizer allowlists, database schema,
saved-record migrations, permissions, deployment or shared settings changed.
Manual/ambiguous typed-marker recovery is deliberately separate; unsupported
custom native formats use a review warning and the existing Mammoth fallback.
The short visual fixture is not a long-list page-break stress test or evidence
for arbitrary Word layouts. Real agency content is not included.

## Evidence

- [Source Word document](synthetic-native-lists.docx)
- [Source render](source-word.png)
- [Editor preview](editor-preview.png)
- [Unsupported-marker warning](unsupported-warning.png)
- [Generated PDF](generated-test.pdf)
- [PDF list page](pdf-list-page.png)

Public test-key reference: [DocRaptor documentation](https://docraptor.com/documentation/article/1067924-trying-docraptor-without-an-account-or-credit-card).
