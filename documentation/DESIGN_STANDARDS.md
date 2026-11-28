# NOFO Design Standards

Design and accessibility guidance for published NOFOs: headings, images,
visual consistency, line breaks, lists, links, and tables, with a checklist to use before
publishing.

> **About this page**
>
> - **Source:** this page reproduces selected guidance from the NOFO design and
>   accessibility standards set by the HHS Office of Grants, in the Office of the
>   Assistant Secretary for Financial Resources (ASFR). It is not the official
>   version and doesn't reproduce every standard.
> - **Applying these standards:** check with your agency's grants policy office
>   for how to follow and comply with them. If needed, refer to the official HHS
>   Office of Grants *NOFO Design and Accessibility Standards for Fiscal Year
>   2027*.
> - **Related guidance:** the [SimplerNOFOs Style Guide](STYLE_GUIDE.md) covers
>   writing and style. The [NOFO Builder FAQ](NOFO_BUILDER_FAQ.md) and
>   [editor tasks](EDITOR_TASKS.md) explain how to make these changes in NOFO
>   Builder.

## On this page

- [Why these standards matter](#why-these-standards-matter)
- [Headings](#headings)
- [Images](#images)
- [Visual consistency](#visual-consistency)
- [PDF Contents layout](#pdf-contents-layout)
- [Line breaks](#line-breaks)
- [Lists](#lists)
- [Links](#links)
- [Tables](#tables)
- [Notes](#notes)
- [Before you publish](#before-you-publish)
- [Related resources](#related-resources)

## Why these standards matter

Simpler NOFOs aims to reduce the burden on applicants and to make NOFOs easier
to read and navigate for everyone, including people who use assistive
technology. These standards support:

- the [Plain Writing Act of 2010](https://plainlanguage.gov/law/);
- [Section 508](https://www.section508.gov/) of the Rehabilitation Act, which
  requires federal electronic documents to be accessible to people with
  disabilities;
- [OMB Memorandum M-24-11](https://www.coffa.gov/assets/files/M-24-11-Revisions-to-2-CFR.pdf),
  which accompanies the 2024 revisions to the federal grants guidance and directs
  agencies to reduce burden for applicants;
- [2 CFR 200.204](https://www.ecfr.gov/current/title-2/section-200.204), which
  calls for funding announcements written in plain language and kept short.

The standards apply to the published NOFO, whatever tool is used to produce it.
Your agency's NOFO template sets the required sections and standard language.

## Headings

The [style guide](STYLE_GUIDE.md#headings) covers heading levels, order, and
capitalization. In addition:

- Keep H3 to H6 headings to 10 words or 80 characters or fewer.
- A "heading" longer than about 20 words or 150 characters is probably body
  text. Format it as a paragraph instead.
- Don't start heading text with a space.
- If content needs a level below H6, use bold text instead of a heading. See
  [What heading levels are supported?](NOFO_BUILDER_FAQ.md#what-heading-levels-are-supported)

## Images

The [style guide](STYLE_GUIDE.md#images-and-alt-text) recommends avoiding
decorative images and requires alt text. In addition:

- If you use an image that's only decorative, mark it as decorative so screen
  readers skip it.
- Any image that conveys information needs alt text, even after import. If an
  image has no alt text when imported, NOFO Builder gives it empty alt text,
  which screen readers treat as decorative.
- To add or change the cover image's alt text in NOFO Builder, see
  [TASK-COVER-ALT-TEXT](EDITOR_TASKS.md#task-cover-alt-text).

## Visual consistency

- Keep spacing, type, and color consistent throughout the document.
- Make links visibly distinct from body text.
- Make sure branding and logos don't compete with the content.

NOFO Builder's design system applies consistent styling, so this matters most
for NOFOs produced outside NOFO Builder.

## PDF Contents layout

This is a NOFO Builder layout pattern for eligible FY27 portrait PDFs. When
the feature is enabled, Contents uses two columns by default. Choose the
single-column layout when long labels or dense step groups make the columns
hard to follow. Let Contents span pages when needed, and use the running step
label to orient readers on continuation pages.

In either layout, keep subsections grouped under their steps and give each
entry its own link. In the exported PDF, check that page numbers match the
destinations and that the reading and navigation order follows the heading
hierarchy. See [Preview a NOFO](EDITOR_TASKS.md#task-preview) for how to select
and preview the layout.

## Line breaks

Use a line break only where the break carries meaning, such as between the
lines of a mailing address or contact block. Don't use line breaks to add space.
Screen readers may read through a line break without a pause.

**Optional:** if a paragraph in the PDF ends with one short word alone on its
last line, or a date, number, or amount splits across two lines, you can add a
line break before the last few words so they stay together. In the NOFO Builder
subsection editor, type `<br>` where the line should break. Make this change
after any other edits to that paragraph, since changing its text can move where
the line breaks.

## Lists

The [style guide](STYLE_GUIDE.md#lists) covers list types and punctuation. In
addition, use real list formatting for bulleted and numbered lists. Don't type
bullet characters (such as •, -, or *) or numbers at the start of a line.
Screen readers announce a formatted list and how many items it has; typed
markers are read as plain text.

## Links

The [style guide](STYLE_GUIDE.md#links) covers link text. In addition:

- Write "Grants.gov" with a capital G, in link text and in body text.
- Format email addresses as email (mailto) links, so readers can select them.
- For links that download a file, include the file type in the link text, such
  as "[PDF]" or "[Word]". You can also include the file size, such as
  "[PDF - 240 KB]". If you include the size for one link, include it for all of
  them, in the same format.

## Tables

The [style guide](STYLE_GUIDE.md#tables) covers captions and simple tables. In
addition:

### Captions

Every table needs a caption: either a descriptive heading directly above the
table, or a bold paragraph in the format "Table: Title of table." See
[style guide: tables](STYLE_GUIDE.md#tables) and
[TASK-TABLE-CAPTION](EDITOR_TASKS.md#task-table-caption).

The following tables don't need a "Table:" caption, because a heading directly
precedes them or their purpose is clear from their type. This list adds to the
style guide's list:

- Callout boxes (single-cell tables).
- Key facts and key dates.
- Table of contents and application contents.
- Narratives, including the project narrative.
- Merit review and scoring criteria, including criteria for subsections of the
  project narrative.
- Research plan sections.
- Attachments.
- Standard and other required forms, such as the SF-424.
- Reporting requirements.
- Application checklist.

### Splitting complex tables

If splitting a complex table means repeating some content, such as a row label
or a shared header, repeat it in each new table. Accessible structure is more
important than saving space.

## Notes

This is a NOFO Builder pattern (#1437). A note is one short caveat for
applicants, such as who a requirement applies to or what they must do. It is
not a summary: use a callout box for key facts, contacts and other
highlights, and keep table-reading notes, such as what an asterisk means,
directly below the table.

**How a note looks.** A light box with a 4px left rule in the theme colour, an
8% tint of that colour and a bold lead-in in the theme colour. Body text stays
black. There is no icon, heading or rounded corner. It sits at the full text
width and doesn't split across pages.

**Writing a note**

- Start with a lead-in that names the note and, if it helps, the audience:
  "Note:", "Note for applicants:" or "Note (competing supplement applicants):".
  Keep the lead-in to one line.
- Say what the applicant must do, if anything.
- Keep it to one short paragraph. Use a callout box for content with headings,
  lists or tables.
- Use notes sparingly. More than about two on a page makes each one easier to
  ignore.
- Place a note after the list or table it qualifies, never inside it. A note
  label inside a list item or table cell stays ordinary text.

**Accessibility.** The lead-in is real text, so the note's meaning doesn't
depend on colour. In HTML the note is `<div class="note-callout" role="note">`.
In the PDF it is tagged `Div` with a `P` inside, not `BlockQuote`, so screen
readers don't announce a quotation. Notes don't add headings or bookmarks.

**Theme colours.** Each OpDiv theme sets `--color--note-rule`,
`--color--note-tint` and `--color--note-label` from its table-header colour.
The rule needs at least 3:1 against white, and the lead-in at least 4.5:1 on
the tint. A test checks every selectable theme. FDA and CDC DHP use a darker
lead-in because their accent blue is too light for small bold text on the
tint.

| Theme | Rule | Tint | Lead-in | Rule on white | Lead-in on tint |
| --- | --- | --- | --- | --- | --- |
| ACF (Light) | `#264a64` | `#eef1f3` | `#264a64` | 9.35:1 | 8.24:1 |
| ACL (Default) | `#08508f` | `#ebf1f6` | `#08508f` | 8.22:1 | 7.22:1 |
| ASPR (Light) | `#155197` | `#ecf1f7` | `#155197` | 7.91:1 | 6.96:1 |
| CDC (Default), also landscape | `#0057b7` | `#ebf2f9` | `#0057b7` | 6.89:1 | 6.10:1 |
| CDC DGHP | `#20263e` | `#edeef0` | `#20263e` | 14.91:1 | 12.85:1 |
| CDC DHP | `#007ac1` | `#ebf4fa` | `#00639e` | 4.61:1 | 5.75:1 |
| CDC IOD | `#672e6b` | `#f3eef3` | `#672e6b` | 9.63:1 | 8.41:1 |
| CDC NCIPC Blue | `#1a3b66` | `#edeff3` | `#1a3b66` | 11.28:1 | 9.80:1 |
| CDC NCIPC Teal | `#004c52` | `#ebf1f1` | `#004c52` | 9.74:1 | 8.53:1 |
| CDC ORR | `#003057` | `#ebeef2` | `#003057` | 13.46:1 | 11.56:1 |
| CDC (Light), also landscape | `#0057b7` | `#ebf2f9` | `#0057b7` | 6.89:1 | 6.10:1 |
| CMS (Default) | `#004a86` | `#ebf1f5` | `#004a86` | 9.04:1 | 7.93:1 |
| CMS (Light) | `#004a86` | `#ebf1f5` | `#004a86` | 9.04:1 | 7.93:1 |
| FDA | `#007cba` | `#ebf5f9` | `#00639e` | 4.57:1 | 5.78:1 |
| HRSA (Default, legacy) | `#00345e` | `#ebeff2` | `#00345e` | 12.71:1 | 10.99:1 |
| HRSA (Light) | `#006699` | `#ebf3f7` | `#006699` | 6.25:1 | 5.56:1 |
| IHS (Light) | `#012f52` | `#ebeef1` | `#012f52` | 13.73:1 | 11.79:1 |
| NIH (Light) | `#08508f` | `#ebf1f6` | `#08508f` | 8.22:1 | 7.22:1 |
| OASH | `#162e51` | `#eceef1` | `#162e51` | 13.60:1 | 11.70:1 |
| ONC | `#081f7a` | `#ebedf4` | `#081f7a` | 14.12:1 | 12.07:1 |
| SAMHSA (Light) | `#1a6986` | `#edf3f5` | `#1a6986` | 6.16:1 | 5.50:1 |

**Pagination.** A note stays on the same page as the content just before it,
such as the table it qualifies, unless the note has its own page break.

**Edge cases**

- **Lead-in without bold.** The note keeps its box and rule, but the lead-in
  isn't coloured. "Note:" still names it, and reimport still finds it.
- **No lead-in.** The note is shown, but only colour marks it as a note
  (WCAG 1.4.1), and a Word export and reimport turn it into a plain
  paragraph. The editor shows a warning until a label is added.
- **More than one paragraph, a list or a heading.** These display, but a Word
  export and reimport keep only the first paragraph as the note.
- **Long notes.** The "lots of content" warning only checks box callouts.
- **Before you get started.** Introductory text can be a note, or plain text,
  but not a box callout or a heading.
- **Headed subsections.** A subsection with a heading can't become a note,
  because its heading can't be removed. Add a new subsection without a heading
  for the note instead.
- **Placement.** Notes always stay in the main text column. They never move
  to the first section's sidebar, even if they start with "Have questions?".

See [TASK-NOTE-CALLOUT](EDITOR_TASKS.md#task-note-callout) to add or edit a
note, and [IMPORT-080](IMPORT_RULES.md#import-080--applicant-note-labels-and-note-callouts)
for how Word imports create them.

## Before you publish

Check the final PDF against this list.

- Headings use H1 to H6 in order, with one H1 for the title
  ([style guide: headings](STYLE_GUIDE.md#headings), [headings](#headings)).
- Metadata author, subject, and keywords are filled in
  ([style guide: metadata](STYLE_GUIDE.md#taglines-and-metadata)).
- Links have descriptive text, and email addresses are linked
  ([style guide: links](STYLE_GUIDE.md#links), [links](#links)).
- Images that convey information have alt text, and decorative images are marked
  as decorative ([style guide: images](STYLE_GUIDE.md#images-and-alt-text),
  [images](#images)).
- Tables have a caption where needed and use simple structure
  ([style guide: tables](STYLE_GUIDE.md#tables), [tables](#tables)).
- Lists use list formatting, not typed bullets or numbers
  ([style guide: lists](STYLE_GUIDE.md#lists), [lists](#lists)).
- Endnotes are numbered in order, without reusing a number
  ([FAQ: endnotes](NOFO_BUILDER_FAQ.md#endnotes)).
- Notes are short, start with a bold lead-in and sit outside lists and tables
  ([notes](#notes)).
- No stranded lines, isolated headings, or excess white space
  ([FAQ: page breaks](NOFO_BUILDER_FAQ.md#when-should-i-add-a-manual-page-break)).

## Related resources

- [Quality review and triage](QUALITY_REVIEW_AND_TRIAGE.md#review-design-accessibility) — Review output, investigate causes and route findings into document help or product improvements
- [SimplerNOFOs Style Guide](STYLE_GUIDE.md)
- [NOFO Builder FAQ](NOFO_BUILDER_FAQ.md) and [editor tasks](EDITOR_TASKS.md)
- [U.S. Web Design System](https://designsystem.digital.gov/), which the
  SimplerNOFOs design system is adapted from
- [Section508.gov testing guidance](https://www.section508.gov/test/)
