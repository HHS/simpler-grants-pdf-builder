# Metadata consumption import review

Issue: [#802](https://github.com/HHS/simpler-grants-pdf-builder/issues/802).
Implementation: `1248ea63`; additional Word-bookmark regression: `54562930`.
This change is stacked on the Metadata extraction and introductory-family work
in #1099 and #1101. It adds no migration or render-time suppression.

## Browser verification

Chrome, isolated local app at `127.0.0.1:8909`, synthetic draft
`d1d79fb5-cb8d-4ce6-897e-5e390cd4187f`, October 13, 2026.
No production records or private source documents were uploaded or changed.

The draft already had a saved Metadata subsection. Re-importing the same
synthetic combined compatibility Word fixture through the actual UI consumed
the incoming Metadata source while keeping the resolved title, number, agency
and author in existing field controls. There were zero Metadata editor rows,
public headings or TOC links afterward. The Step 2 introductory-page link still
navigated to the generated Before you get started page.

- `before-editor.jpg`: saved Metadata source before authorized re-import.
- `after-editor.jpg`: editor after re-import, with no Metadata subsection.
- `after-fields.jpg`: existing metadata controls retain resolved values.
- `after-html.jpg`: public HTML after re-import, with no duplicate source.

## Actual PDF verification

Generated through Builder's existing PDF service using DocRaptor's documented
public test key and synthetic content only. Styles/fonts/logos came from the
public dev static base. This was a watermarked Prince 15.1 test conversion, not
a production PDF generation/deployment test.

The resulting PDF had eight pages and embedded all seven fonts. Its PDF title
was `Synthetic combined compatibility QA`; its PDF author remained
`Synthetic QA Office`. Text extraction found no Metadata source heading or
field paragraphs. All eight rendered pages were visually inspected; excerpts:

- `pdf-contents.png`: page 2, TOC contains program sections, not Metadata.
- `pdf-basic-information.png`: page 6, program content/agency retained.
- `pdf-registration-link.png`: page 8, introductory-page link retained.

## Automated and Word verification

Focused Metadata + introductory-family tests cover capture authority, blanks,
all supported heading levels, repeated blocks, incidental mentions, bounded
prose/table/list/image/native-note/manual-note handling, consumed IDs,
number-mismatch confirmation, archives, rollback, saved design choices and
actual Composer/Compare import POSTs retaining source content. A separate
actual-import regression covers Word-style bookmark targets in consumed
headings/field paragraphs.

Editor, public HTML and normal Word-export HTML have no imported Metadata
heading. Word export's existing generated Basic information fields remain
intentionally. Actual GrabzIt DOCX bytes were not generated: no dedicated
non-production credentials were available, and the export allowlist remains
enforced. No production credentials or allowlist bypass was used.
