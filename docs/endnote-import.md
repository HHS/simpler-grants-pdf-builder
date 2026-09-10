# Endnotes in Word imports

NOFO Builder preserves native Microsoft Word footnotes/endnotes and can create
links for manually authored references using the following convention:

- Use `[1]`, `[2]`, etc. in the body, with no spaces inside the brackets.
- Use each reference number once, in sequence throughout the document.
- Put citations under one actual **Endnotes** heading, in reference order.
  Capitalization, a trailing colon, and Footnote/Footnotes headings are normalized
  during import. Bold paragraph text alone is not a structural heading.
- Begin each citation with its matching marker on a new paragraph. Continuation
  paragraphs, lists, tables, and links belong to that citation until the next
  citation entry or the section boundary.
- When citing the same source again, use the next reference number and repeat the
  citation information under that number.

Complete, unique pairs become forward and return links. Numbering gaps or order
differences are advisory; they do not prevent otherwise unambiguous linking.
Missing, duplicate, empty, or ambiguous manual pairs are left for review. NOFO
Builder never silently renumbers notes. Ordinary bracketed content is not enough
on its own to establish an endnote relationship.

## Existing documents and reimports

Viewing a saved NOFO recalculates advisory warnings without changing stored
content or IDs. Correct issues in the system where the source is maintained, or
correct an issue introduced by an edit in NOFO Builder at the affected location.

Automatic conversion happens only on import/reimport. Reimport retains the parent
NOFO record and the existing revision/transaction behavior; it replaces sections
and subsections as before. It does not guarantee stable child IDs or stable anchor
names across changes to the source Word document.

Native relationships are preserved even when visible numbers differ from internal
link identifiers. Mixed native/manual documents may need author review when their
visible numbers collide. The source Word file is never modified by import.

## Release validation

Automated tests use constructed Word documents and saved HTML to exercise the
conversion and rendering paths. Before production rollout, also verify:

- A representative, unmodified Announcement Module-designed Word export preserves
  the agreed markers, actual heading, and multi-paragraph citation boundaries.
- Forward and return links work in the preview and a PDF produced by the deployed
  DocRaptor integration, including citations that span pages.
- Existing native-note documents still render correctly.

A later Word export is outside this change's output guarantees.
