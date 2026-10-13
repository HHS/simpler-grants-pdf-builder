# Word metadata import

Builder accepts legacy first-page labels and the newer trailing **Metadata** section.
Detection uses the uploaded document's headings and paragraphs, not dates or filenames.

## New format

Use a real Word heading named `Metadata`, normally Heading 3. Other heading levels are
accepted. Follow it with paragraphs containing these labels and values:

| Label | Builder field |
| --- | --- |
| OpDiv | OpDiv |
| Agency | Agency |
| Sub Agency / Subagency | Sub Agency |
| Sub Agency 2 / Subagency2 | Sub Agency 2 |
| Opportunity name | Title |
| Opportunity number | Number |
| Application deadline | Application Deadline |
| Metadata author | Author |
| Metadata subject | Subject |
| Metadata keywords | Keywords |

Labels ignore case and whitespace. Inline bold or italic formatting does not split the
value. Only the first colon separates label and value, so `Metadata subject: Research:
community health` keeps the second colon. Blank paragraphs may separate fields.

The field block ends at any following heading, table, list, or non-label prose, even
when that heading is lower-level. Put all fields together before an appendix or notes.
The section need not be the last part of the Word document. Import leaves its content,
appendices, and note links intact; suppression in published output is separate work.

If more than one recognized Metadata block exists, the last block is authoritative.
If a label repeats within that block, its first value wins, including a blank value.
Fields are not combined across blocks or with earlier labels.

## Missing fields and placeholders

A recognized block's missing or blank fields follow the existing defaults: the number
defaults to `NOFO #999`, the deadline to `[WEEKDAY, MONTH DAY, YEAR]`, and a missing title
receives a `NOFO: <timestamp>` suggestion on a new import. Agency, subagencies and PDF
metadata default to empty. OpDiv is required; an absent or blank OpDiv still blocks import
or re-import through the existing validation/recovery flow.

Only whole-field `{...}` placeholders in author, subject and keywords become empty.
`Metadata author: {Same as OpDiv.}` does not copy OpDiv into author. The template's
OpDiv, Agency, Opportunity name, Opportunity number and Application deadline `{Insert ...}`
instructions remain literal values, subject to existing field validation. Replace them
with real values before using the document. No subject generation is added.

## Legacy imports and saved records

Without a recognized Metadata block, legacy scanning remains active, including the
guarded next-paragraph OpDiv continuation. Legacy Subagency spellings and spaced aliases
are supported. Tagline and assistance-listing extraction remain independent of this block.

Extraction runs only on explicit import/re-import. Viewing, editing unrelated fields or
exporting existing records does not re-extract metadata. Authorized re-import still uses
the existing overwrite, validation, status checks and transaction rollback behavior. It
preserves stored theme, cover and registration-page variant; a missing incoming title
does not replace an existing title with a timestamp default. No migration or backfill is
required. New-import cover/theme suggestions use the resolved OpDiv and opportunity number.

The shared suggestion functions also supply OpDiv during Composer and Compare imports;
those workflows retain their filename-based document titles and their own stored fields.
Compare's temporary NOFO continues to use the normal NOFO suggestions. Neither workflow
gains new persisted fields or loses source content.

See [IMPORT-041](IMPORT_RULES.md#import-041--labelvalue-field-scanning) for the rule contract.
