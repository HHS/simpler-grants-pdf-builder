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
The section need not be the last part of the Word document. Builder captures its fields,
then consumes the recognized heading and its field/blank paragraphs before creating
stored sections. Appendices, unrelated prose, tables, lists, media and note links remain
intact. A paragraph containing images/media ends the block, not a blank separator.
The containing program section remains. Ordinary Metadata discussion is not consumed.

If more than one recognized Metadata block exists, the last block is authoritative.
If a label repeats within that block, its first value wins, including a blank value.
Fields are not combined across blocks or with earlier labels.
All recognized blocks are consumed, including earlier non-authoritative blocks. Links
whose only destination is consumed Metadata become plain text, retaining their wording.
No hidden Metadata subsection is generated to hold an obsolete destination.

## Capture and confirmation

Builder keeps an intact extraction source separate from the content copy used to build
sections and choose their heading level. The same source travels through the existing
opportunity-number confirmation session, so validation and later field reads cannot
fall back to front-page labels after consumption. No additional persistent fields or
session format are needed. Introductory-page capture/cleanup runs first and preserves
recognized Metadata for extraction. Its independent family choice survives confirmation.

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

### ACL theme selection

On a new import, a resolved OpDiv of `Administration for Community Living`,
`Administration for Community Living (ACL)` or standalone `ACL` selects
**ACL (Default)** (`portrait-acl-white`), ignoring case. The opportunity number
does not need an `ACL-` prefix: blank, generic and template-placeholder numbers
still select ACL from that OpDiv, as do conflicting number prefixes. Existing
NIH, HRSA and SAMHSA OpDiv checks retain their priority for mixed agency text.
The Author field is extracted separately and does not select the theme.

Previously, ACL theme detection depended on `acl-` in the opportunity number,
so an ACL template with `{Insert opportunity number.}` fell through to
**NIH (Light)** even when its OpDiv and Author were correctly populated as ACL.
The fix applies to new imports using either legacy labels or a recognized
Metadata block. It does not replace placeholder values or change metadata
block precedence.

Saved records are not backfilled. Reimport preserves the existing theme,
including a previously suggested NIH theme. For an already imported ACL NOFO,
use its theme settings to choose **ACL (Default)** explicitly.
See [IMPORT-042](IMPORT_RULES.md#import-042--cover-theme-suggestion).

### Saved-record behavior

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
