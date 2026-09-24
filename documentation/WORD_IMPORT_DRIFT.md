# Word import drift: code-review findings

This document records likely sources of drift between what an author sees in a
Word document and what NOFO Builder produces after import. It is the initial
code-review deliverable for [issue #974](https://github.com/HHS/simpler-grants-pdf-builder/issues/974).

The findings are grounded in the import pipeline, its tests and fixtures, the
automatic transformations in [`IMPORT_RULES.md`](IMPORT_RULES.md), the blocking
failures in [`IMPORT_ERROR_CODES.md`](IMPORT_ERROR_CODES.md), and the history of
import-related fixes.

## Important limitation

The ordering below is a **code-evidence and likely-impact priority**, not a
measurement of production frequency. Existing code can show where Builder has
needed repairs, warnings, and special cases. It cannot establish how often an
author encounters each pattern or how much time they spend correcting it.

The existing [usage and quality metrics](BUILDER_METRICS.md) can provide context
about blocking import errors, warning volume, and time to first live PDF. They
do not identify the cause of an ordinary correction made after import.

## How Builder reads Word

The main source of drift is that **Builder reads document structure, not visual
appearance**.

1. Mammoth converts the `.docx` to HTML using Word styles and native structures.
2. Builder applies known repairs and conversions for headings, lists, tables,
   notes, links, images, metadata, and other content.
3. The resolved heading hierarchy divides the document into sections and
   subsections.
4. Subsection content is stored as Markdown or preserved HTML.
5. The saved structure is rendered as the web NOFO and designed PDF.

A paragraph that looks like a heading, list, or callout to a person may not
carry the semantics Builder needs to interpret it that way.

## Likely drift patterns

| Priority | Pattern | Likely author-visible result | Confidence |
|---:|---|---|---|
| 1 | Visual headings or inconsistent heading levels | Missing sections, incorrect nesting, body text treated as a heading, or a blocked import | High |
| 2 | Manual or malformed footnotes/endnotes | Plain-text reference numbers, unlinked notes, renamed note sections, or review warnings | High |
| 3 | Metadata arranged visually | Missing or incorrect title, OpDiv, deadline, agency, tagline, theme, or cover suggestions | High |
| 4 | Lists built through formatting rather than native list structure | Flattened lists, restarted numbering, incorrect indentation, or plain paragraphs | High |
| 5 | Tables serving as data, callouts, checklists, or layout | Incorrect header assumptions, unintended callouts, or complex tables preserved as raw HTML | High |
| 6 | Links and bookmarks | Broken internal navigation, rewritten targets, redirected destinations, or unlinked text | Medium-high |
| 7 | Images without complete accessibility information | Images with empty alternative text or uncertain inline-image handling | Medium |
| 8 | Manual spacing, page breaks, comments, or tracked changes | Lost layout intent or editorial artifacts represented differently than expected | Medium-low |

### 1. Visual headings and inconsistent hierarchy

Headings have the widest potential impact because they create the NOFO's entire
section and subsection structure.

Builder relies on real Word heading styles. Enlarged, centered, or bold Normal
text does not become a heading solely because it looks like one. Conversely, a
paragraph accidentally carrying a heading style can become navigation or exceed
the allowed heading length.

Known failure shapes include:

- a Heading 2 before the first Heading 1, which blocks import as ambiguous;
- no usable section headings, which produces `IMPORT-NO-SECTIONS`;
- paragraph-length text carrying a heading style, which produces
  `IMPORT-HEADING-TOO-LONG`;
- inconsistent peer headings that produce a different nesting hierarchy; and
- a visual-only heading that remains ordinary subsection content.

Evidence is strong: Builder has dedicated heading repairs and validations, a
mistagged-heading fixture, specific user guidance, and recent fixes for mixed
heading hierarchies.

**Potential upstream improvement:** Strengthen the Word template's heading
structure and give authors a simple outline or preflight check. Avoid adding
more visual guessing where the author's intended hierarchy is ambiguous.

### 2. Manual or malformed footnotes/endnotes

Notes have one of the largest clusters of specialized import behavior. Builder:

- preserves Word-native note lists and links through Markdown conversion;
- synthesizes a missing Endnotes heading for recognized note structures;
- renames variants such as “Footnotes” to “Endnotes”;
- links unambiguous bracketed references such as `[1]`; and
- warns about missing, duplicate, malformed, conflicting, or non-sequential
  references and citations after import.

Manually superscripted numbers, incomplete reference/citation pairs, or note
lists that only look linked can therefore arrive as plain content requiring
review.

**Potential upstream improvement:** Clearly document the supported Word-native
and bracketed-note approaches, and discourage manually formatted superscript
references without structural links.

### 3. Metadata and page-one layout

Builder extracts metadata from recognizable labels and nearby text. Visual
layouts can separate a label from its value in ways that are obvious to a
person but not safely inferable by the importer.

Examples include:

- `OpDiv:` and its value in different cells, text boxes, lines, or paragraphs;
- renamed or missing metadata labels;
- underscore placeholders treated as apparent values;
- Funding Details labels and values split across paragraphs; and
- opportunity numbers that do not follow expected prefixes, affecting theme
  and cover suggestions.

The code contains special handling for soft line breaks, paragraph breaks,
placeholder values, and split Funding Details fields. `IMPORT-OPDIV-BLANK`
provides a blocking example of this mismatch.

**Potential upstream improvement:** Keep the metadata block in a tested template
pattern and avoid moving labels and values into separate visual containers.

### 4. Lists and indentation

Word can represent visually similar lists using native numbering, paragraph
styles, typed characters, or indentation. Builder repairs several known forms:

- recognized bullet and numbered paragraph styles become real nested lists;
- adjacent lists may be joined or nested;
- redundant wrapper levels are removed;
- non-one starting numbers and lists inside table cells may remain raw HTML;
- checklist hierarchy may be inferred from paragraph indentation; and
- one canonical ACF bullet pattern becomes continuing numbering.

Typed bullets, manually entered numbers, pasted list styles, and complex
multilevel numbering remain likely sources of drift.

**Potential upstream improvement:** Require native Word lists and approved
template list styles, particularly for multilevel or continuing-number lists.

### 5. Tables and callout boxes

Builder must infer a table's meaning from its shape:

- the first row is assumed to be a header row;
- malformed multi-row Word headers are repaired;
- a one-row, one-cell table becomes a callout-box subsection;
- “Key facts” and “Key dates” receive special heading treatment; and
- merged-cell tables are preserved as raw HTML instead of ordinary Markdown.

A layout table can therefore be interpreted as data, a table without a true
header can receive one, or a one-cell visual container can become a callout.

**Potential upstream improvement:** Provide explicit approved patterns for data
tables, callouts, and checklists. Discourage tables used only for page layout.

### 6. Links and bookmarks

Builder removes Google tracking redirects, joins adjacent links with the same
destination, preserves several bookmark shapes, generates new heading IDs, and
rewrites matching internal links. Saved-content checks separately report broken
internal targets and links with no destination.

Internal navigation is especially sensitive to heading-name changes and custom
Word bookmark schemes. Empty or malformed destinations may also become plain
text during conversion.

**Potential upstream improvement:** Validate bookmarks and empty destinations
before publication, and avoid manually constructed internal-link schemes where
heading-based links are sufficient.

### 7. Images and alternative text

Builder preserves an image with no supplied `alt` attribute by adding
`alt=""` and a marker. This prevents malformed output but cannot recover the
image's intended description for assistive-technology users. Inline image-source
rewriting exists in the code but is not currently wired into the import
pipeline, so broader image handling has less supporting evidence than the
patterns above.

**Potential upstream improvement:** Make meaningful alternative text part of the
Word authoring checklist rather than relying on import repair.

### 8. Manual layout and editorial artifacts

Manual blank lines, spacing, and page breaks are visual instructions rather than
content structure, so they cannot be expected to reproduce the Word page in the
designed PDF. Builder has separate post-import page-break behavior, but no
general preservation contract for Word layout.

The import-rule catalog also has no explicit handling for Word comments or
tracked changes. Mammoth may interpret some forms, but the current fixtures and
tests do not provide enough evidence to characterize the author experience.

**Potential upstream improvement:** Define the supported page-break mechanism.
Test comments and tracked changes using representative author documents before
making stronger recommendations.

## Overall finding

The strongest dividing line is not simply Word versus PDF. It is **semantic Word
structure versus visual formatting used as a substitute for structure**.

Headings, notes, metadata layout, lists, and tables are the strongest candidates
for high-impact drift. They have repeated special-case repairs, blocking errors,
fixtures, warnings, or recent bug fixes. Links, images, and manual layout are
credible secondary patterns. Comments and tracked changes remain open questions.

This analysis is sufficient to guide template improvements, authoring guidance,
and targeted qualitative research. It should not be cited as evidence that one
pattern is more frequent than another without additional user or production
evidence.
