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
- [Line breaks](#line-breaks)
- [Lists](#lists)
- [Links](#links)
- [Tables](#tables)
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

## Line breaks

Use a line break only where the break carries meaning, such as between the
lines of a mailing address or contact block. Don't use line breaks to add space.
Screen readers may read through a line break without a pause.

**Optional, at final PDF review:** if a paragraph ends with one short word alone
on its last line, or a date, number, or amount splits across two lines, you can
add a line break before the last few words so they stay together. In NOFO
Builder, type `<br>` where the line should break. Make this change only when
reviewing the final PDF: if the text changes later, the break may land in the
middle of a line.

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
- No stranded lines, isolated headings, or excess white space
  ([FAQ: page breaks](NOFO_BUILDER_FAQ.md#when-should-i-add-a-manual-page-break)).

## Related resources

- [SimplerNOFOs Style Guide](STYLE_GUIDE.md)
- [NOFO Builder FAQ](NOFO_BUILDER_FAQ.md) and [editor tasks](EDITOR_TASKS.md)
- [U.S. Web Design System](https://designsystem.digital.gov/), which the
  SimplerNOFOs design system is adapted from
- [Section508.gov testing guidance](https://www.section508.gov/test/)
