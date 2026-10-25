# Endnotes in Word imports

NOFO Builder preserves native Microsoft Word footnotes/endnotes and can create
links for manually authored references. Native Word notes and manually bracketed
notes use different authoring conventions.

## FAQ for authors using Microsoft Word on Windows

### Why do some citation numbers import without working links?

A small raised number can be an actual Word endnote, ordinary text formatted as
superscript, or a Word cross-reference field. They may look alike in Word but
store different information. Typing `1` or `1,2` and applying superscript does
not establish an endnote relationship.

### How should I create endnotes?

1. Save a copy of the source document before repairing citations.
2. Place the cursor after the statement you want to cite.
3. Select **References > Insert Endnote**. Word inserts the reference mark and
   opens the corresponding note at the end of the document.
4. Enter the source information in that note. Let Word generate the numbers.
5. Repeat for the other statements. You can insert another endnote and repeat
   the source information under the new number, or use a supported Word
   cross-reference as described below.
6. Save as `.docx`, import it into NOFO Builder, and check the forward and return
   links in the full NOFO HTML preview. A subsection-only preview does not
   contain the body reference destinations for its return links.

For this reported document, replace the manually typed repeated `1` and `1,2`
with real notes. A typed `1,2` needs two note references, with a comma between
them. Keep the source information when making repairs; deleting a genuine Word
reference mark also removes its associated note. Replace the repeated Word
cross-reference to note 3 with another native endnote if compatibility with an
importer predating IMPORT-076 is required.

Microsoft documents the Windows ribbon steps in
[Insert footnotes and endnotes in Word](https://support.microsoft.com/en-au/word/training/insert-footnotes-and-endnotes-in-word).

### Can I reference an existing Word endnote again?

Word supports this using **Insert > Cross-reference**: choose **Endnote** as
the reference type, choose the endnote number (formatted) option, select the
existing note, keep **Insert as hyperlink** checked, and select **Insert**.
This creates an explicit relationship instead of a typed number. See
[Microsoft's cross-reference instructions](https://support.microsoft.com/en-us/word/create-a-cross-reference).

The import fallback in IMPORT-076/IMPORT-072 preserves supported native Word
cross-references and gives each occurrence its own forward and return link.
Availability depends on the deployed release. Unsupported fields and unresolved
bookmarks still need author review. Manual bracketed references do not gain
support for repeated numbers from this fallback.

### Where should I put the References heading?

Keep the title outside the first citation. NOFO Builder creates an Endnotes
section for native Word notes, so an additional title is unnecessary. A bold
References paragraph typed inside the first note belongs to that note in Word's
file structure. IMPORT-073 recognizes a standalone title at that exact location
and moves it into the synthesized Endnotes heading during import.

### Why does NOFO Builder report conflicting IDs after I copied a citation link?

Each in-body link needs its own unique ID, even when several links point to the
same citation. Copying HTML can duplicate that ID and make the return destination
ambiguous. IMPORT-072 repairs unambiguous repeated native links on import or
reimport. Viewing an existing NOFO does not repair saved content automatically.
Repeated links must each have a matching return link in their citation.

## Manually bracketed references

Use the following convention:

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
