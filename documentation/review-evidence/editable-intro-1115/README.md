# Editable introduction verification

Issue #1115. October 15, 2026. This branch is stacked on the PDF snapshot fix
#1113/#1116 so migrations form a single 0152 -> 0153 chain. No merge, deployment
or production-record changes are part of this evidence.

## Design and compatibility

See [the durable behavior guide](../../EDITABLE_INTRODUCTION.md) for ownership,
classification, editor constraints, re-import outcomes and output policy.
Wording family and ownership are separate. A new explicit introduction role at
order zero leaves existing main-section orders unchanged. Existing records
retain their generated workflow and saved family/variant, including None and
blank/default numbers. Composer and Compare do not opt in.

The actual October 13 cleared Word master was converted and processed locally,
without sending its contents to any provider. It selected imported ownership,
retained four introductory subsections, and kept Step 1 at order one. That check
is local source recognition, not a claim about deployed import or final layout.
No private source or output is committed here.

## Automated scenarios

`test_editable_introduction.py` covers:

- T01/T03/T04/T20: compound recognition at both H1/H2, unsupported HTML/new
  documents, missing/repeated/empty intro, unsafe prelude rejection, source
  private-attribute spoofing and required-mode cross-family mapping.
- T02/T07/T08/T23: all three prior families and all five variants remain
  generated; settings stay accessible; blank/default numbers never select mode.
- T05/T06/T18/T24/T25: Metadata boundaries, ordinary source lists/tables,
  authored child bookmarks, canonical Step 2 links, note forward/return targets,
  unique rendered IDs, and no false broken-link warnings.
- T09/T10/T11: mode, family and role survive re-import, duplication and archival;
  missing introductory content stops before any overwrite/archive.
- T12/T13/T21/T27: settings GET/POST denied only in imported mode; lead body
  title is blank/disabled and has no heading control; direct heading/callout
  manipulation rejected; genuine named children remain editable; metadata
  changes do not rewrite source text; fixed role/name/order and unique parent.
- T14/T16/T18: parent-only compact TOC/icon, no numbered divider, Step 1 metadata
  and sidebar, preserved main numbering, and Endnotes insertion without moving
  the introduction. Historical noncontiguous-order rendering remains unchanged.
- T17/T19: guidance with/without authored equivalent text, content included once
  in full/export/readability HTML, and generated legacy body excluded.

Existing family/import, Metadata, forms, shared content-processing,
Endnotes/Appendix, Composer/Compare, and policy-export suites provide regressions.
Final suite counts, browser captures and independent review results are recorded
in the PR after verification completes. Do not read this list as proof that all
T01-T27 environments or actual provider outputs have been tested.

## Actual synthetic PDF checks

Three outputs were generated through the actual DocRaptor test API using its
[documented public test key](https://docraptor.com/documentation/article/1067924-trying-docraptor-without-an-account-or-credit-card),
test mode, pipeline 11 and PDF/UA-1 profile request. Only synthetic content was
sent; current local CSS was inlined and public dev URLs resolved static fonts.
Production credentials were not used. Requesting a PDF/UA profile does not prove
accessibility conformance.

- Portrait HRSA/solid icon: eight pages, imported body on page 3.
- Landscape CDC/thin icon: eight pages, imported body on page 3.
- Long portrait source: twelve pages, intro spanning pages 3-7 without forced
  shrinking. Step 1 follows on page 8. Introductory footer remains consistent.

PDF pages and navigation annotations are inspected separately from HTML. The
vendor's test watermarks are expected. Short main sections intentionally leave
substantial whitespace on section-divider pages.

## Remaining verification limits (AC16/T26)

- Actual GrabzIt DOCX bytes, bookmarks, TOC and footer have not been generated
  in this local environment. Its allowlist remains intact and production
  credentials are not used. Local Word-export HTML is not provider DOCX proof.
- No deployed cleared-master import/export has been performed for this branch.
- Synthetic representative layouts are not a review of every theme, source
  document, long table, browser or assistive technology.

These are explicit verification limits for maintainers, not a request to invent
another approval owner or broaden access to complete a local development task.
