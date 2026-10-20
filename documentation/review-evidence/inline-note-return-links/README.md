# Inline native-note return-link repair

The screenshots demonstrate the exact HTML shape targeted by IMPORT-068 using
an invented citation. They are browser renders of the checked-in before/after
HTML, not screenshots of an original Word import or the NOFO Builder UI.

- Before: the final paragraph contains only the native note's matching return arrow.
- After: `inline_native_note_return_links` moves that same anchor after the citation.
- `before-fragment.html` is the synthetic input. `after-fragment.html` is the
  helper's actual output; the surrounding pages add only presentation and labels.
- The supplied source Word document had trailing empty paragraphs in all 44
  nonempty endnotes. Current upstream conversion (Mammoth 1.12.2) produced zero
  arrow-only paragraphs before this repair. The historical cause is unconfirmed.
- No source Word document or actual citation text is included in this evidence.

Validation covers footnotes/endnotes, legitimate multi-paragraph citations,
matching destinations, link attributes, idempotence, already-inline content,
manual/nonnumeric notes, additional text/elements/images/comments, paragraph
attributes, nested notes, and shared import through Markdown storage. A synthetic
Word fixture with three trailing blank paragraphs per note characterizes the
source pattern without claiming it reproduces the reported issue.
