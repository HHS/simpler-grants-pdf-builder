# Tagline import and editing

Builder supports two source locations without choosing by filename or template date:

- Legacy documents: the existing metadata paragraph `Tagline: value`. Underscore-only values remain blank.
- New documents: a Tagline heading directly under Step 1: Review the Opportunity → Basic information, with one immediately following paragraph. Heading case and spacing can vary.

The new source takes precedence when present, including when intentionally blank.
Builder does not search past another heading, table, list or empty paragraph for
a value. The field is optional; no period or 15-word limit is imposed. Curly-brace
template guidance is not silently removed.

The consumed heading/paragraph do not become a Tagline subsection or duplicate
body content. Any additional paragraphs remain ordinary, visible body content;
callouts and neighboring headings are preserved. Inline links and emphasis use
the field's existing Markdown representation. A paragraph containing an image
is retained as body content rather than converted into a tagline.

Use the existing Tagline row in Basic information on the NOFO editor to edit the
saved value. It appears through the existing dedicated tagline presentation;
a blank value produces no empty tagline block.

Authorized re-import uses the same metadata contract as before: it re-suggests
the tagline from the incoming source and can replace or clear a previously edited
value. Re-import does not preserve manual tagline edits. Opportunity-number
confirmation retains the chosen new source and blank precedence. Normal status,
permission, metadata-preservation and rollback rules remain in place.

Opening, editing other fields, or exporting an existing record never extracts
or removes stored Tagline subsections. No migration/backfill is included.
Composer and Compare keep their existing import behavior.

Implementation details: [IMPORT-041 and IMPORT-059](IMPORT_RULES.md#import-059--scoped-basic-information-tagline-extraction).
