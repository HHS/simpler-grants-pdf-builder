# NOFO Builder FAQ

Answers to common questions about designing a NOFO in NOFO Builder. For
step-by-step instructions, see [NOFO Builder editor tasks](EDITOR_TASKS.md). For
writing and style questions, see the [SimplerNOFOs Style Guide](STYLE_GUIDE.md).

## In this FAQ

- [About NOFO Builder](#about-nofo-builder)
- [Importing and exporting](#importing-and-exporting)
- [Text editor and Markdown](#text-editor-and-markdown)
- [Tables](#tables)
- [Page layout and callout boxes](#page-layout-and-callout-boxes)
- [Endnotes](#endnotes)
- [Appendices and subsections](#appendices-and-subsections)
- [PDF metadata](#pdf-metadata)
- [NOFO status](#nofo-status)
- [Writing and style](#writing-and-style)

## About NOFO Builder

### What's NOFO Builder?

NOFO Builder is a tool that transforms structured NOFO content into consistent,
accessible, and branded outputs, like designed HTML pages and Section
508-compliant PDFs, using the SimplerNOFOs design system.

### Where does NOFO Builder fit in the NOFO process?

NOFO Builder comes in after your NOFO Word document has been drafted, reviewed,
and approved. It replaces the step where a designed PDF would otherwise require
manual formatting work. Your drafting and review process doesn't change.

NOFO Builder doesn't connect to Grants.gov. Publishing always requires
downloading the designed PDF, so a draft or test NOFO can't be published by
accident.

### Can multiple people work on the same NOFO?

Yes. NOFO Builder is a cloud-based application that supports multiple users per
NOFO. Two features help teams coordinate:

- **Status field:** shows where the NOFO is in the design and review process. See
  [NOFO status](#nofo-status).
- **Activity history:** each NOFO keeps a record of recent changes, including
  what was updated, who made the change, and when.

To avoid overwriting each other's work, agree on who is editing at any given
time.

### Can I use NOFO Builder to practice?

Yes. NOFO Builder works well as a practice environment:

- There's no limit on the number of NOFOs you can create.
- You can delete any NOFO from your list when you're done.
- Nothing is published from NOFO Builder, so a practice NOFO can't reach
  Grants.gov.

## Importing and exporting

### What can be imported into NOFO Builder?

NOFO Builder accepts Word documents that use an HHS-approved template or that
were exported from Announcement Module. Don't include a designed cover page or
table of contents. NOFO Builder is for designing NOFOs only; don't use it to
design Application Guides.

You can't import a Word document that was previously designed and exported from
NOFO Builder. To make changes after exporting, re-import your original Word
document, or make the edits directly in NOFO Builder.

### Why am I seeing "400 Error: This field cannot be blank" when importing a Word document?

This error usually means the Word document was previously exported from NOFO
Builder. NOFO Builder doesn't support importing a document that has already been
through the design process. Re-import your original Word document instead, or
make the edits directly in NOFO Builder.

For other import errors, see [NOFO import error codes](IMPORT_ERROR_CODES.md).

### Should I fix an issue in NOFO Builder or in my Word document?

It depends on the issue.

Fix it directly in NOFO Builder if it's:

- A wording, phrasing, or text change.
- A broken or incorrect link.
- A heading level fix.
- A page break or layout adjustment.
- A small number of isolated, well-defined fixes.

Fix it in your Word document and re-import if:

- A merged table cell, nested list, or in-body image didn't import correctly.
- The same formatting problem appears in many places and traces back to how the
  Word document was structured.
- NOFO Builder flagged an error or warning during import. That means the fix
  belongs in the Word document.
- A substantive content change needs to be reflected in the approved Word
  document, which is the source of record.

**Re-importing is not a merge.** It replaces all existing content in NOFO
Builder with the new Word document. Manual edits made in NOFO Builder since the
last import are lost, except page break placements. Before re-importing, use the
**Compare** tool to see exactly what would change.

### What should I check first after importing?

Review these areas before making edits. Problems here usually start in the Word
document and are easier to fix there:

- **Tables:** preview the PDF and compare each table to your Word document. A
  column that's too narrow is easy to fix in NOFO Builder (see
  [column widths](#how-do-i-control-table-column-widths)). If a table looks
  structurally wrong, with columns in the wrong order, merged cells not
  rendering, or content in unexpected places, recreate it in Word and
  re-import.
- **Endnotes:** compare the endnote count to your Word document. Missing or
  out-of-sequence endnotes, or warnings in the **Review endnotes** tab, usually
  mean the endnotes were typed manually in Word. Fix them in Word and re-import.
- **Headings:** select the **Check heading levels** tab under **Before
  publishing, address the following**. Skipped or out-of-order heading levels
  usually come from the Word document. Check that Step titles are Heading 2 and
  that subsection headings follow in order.
- **Internal links:** select the **Check broken links** tab. Many broken links
  usually mean anchor links in the Word document point to headings or bookmarks
  that don't exist or weren't imported.

The **Copy links** and **Copy endnote issues** buttons copy the full list of
problems, so you can share it with whoever maintains the Word document.

### How do I duplicate a NOFO?

Duplicating is useful for a recurring NOFO that needs only minor updates each
cycle.

1. Open the NOFO from the **In progress NOFOs** or **Published NOFOs** list on
   the home page.
2. Select **NOFO actions** in the top right.
3. Select **Duplicate NOFO**.
4. Enter a name for the duplicate.
5. Select **Save NOFO name**.

### How do I delete a NOFO?

On your NOFO page, open **NOFO actions** in the top right, select **Delete
NOFO**, and confirm. Deleted NOFOs can't be recovered. Only Draft NOFOs can be
deleted; see [NOFO status](#nofo-status).

### How do I download a NOFO as a Word document?

Select **NOFO actions** in the top right, then **Export Word doc**. On the page
that opens, select **Download Word**.

The Word document doesn't include the SimplerNOFOs design or accessibility
tagging. For the designed, accessible version, use **Download PDF**.

### What happens if I edit a designed NOFO PDF in Adobe Acrobat?

Editing a designed NOFO directly in a PDF editor such as Adobe Acrobat can break
accessibility tags, reading order, heading structure, bookmarks, links, and other
metadata required for Section 508 compliance. It can also introduce
inconsistent fonts, spacing, and layout that no longer match the SimplerNOFOs
design system.

Make content and formatting changes in the source and generate a new PDF.

### I can't find my NOFO on the home page. Where is it?

By default, the home page shows NOFOs that are in progress. If yours isn't
listed:

- Check the other lists on the home page. NOFOs are grouped by status, so a
  published NOFO, for example, appears in a different list.
- Select **Search NOFOs** in the top right and search by the NOFO's name or
  number.

## Text editor and Markdown

### Why does NOFO Builder use Markdown?

Markdown is a lightweight plain-text formatting language that uses simple
symbols to show structure, such as `**bold**` for bold text, `#` for headings,
and `*` for bullet points.

NOFO Builder uses Markdown because it gives a structured, standard way to write
headings, lists, tables, and links without managing fonts, spacing, or layout by
hand. Because content is stored in a simpler, standard format, NOFO Builder can
reliably turn it into consistent, accessible outputs and move it between Word,
GrantSolutions, PDFs, and future systems with fewer formatting problems.

### How do I add a heading in the text editor?

Start a line with hashtags and a space. The number of hashtags sets the heading
level:

```markdown
## Heading 2
### Heading 3
#### Heading 4
##### Heading 5
###### Heading 6
```

Heading 2 is reserved for top-level NOFO sections: the steps, Contacts and
Support, Appendices, and Endnotes. Start subsections at Heading 3.

Headings must be in order. For example, don't follow a Heading 1 with a Heading
3. Skipping levels makes the document harder to navigate with a screen reader.
To fix a heading level, see
[TASK-HEADING-LEVEL](EDITOR_TASKS.md#task-heading-level).

### What heading levels are supported?

Use heading levels H1 through H6. These are the only heading levels defined by
the HTML standard and recognized by screen readers under WCAG and Section 508.

- **H1:** the NOFO title, once per document.
- **H2:** top-level sections: the steps, Contacts and Support, Appendices, and
  Endnotes.
- **H3 to H6:** subsections within those sections.

If your content needs a level beyond H6, use bold text instead. H7 isn't a
recognized HTML heading and isn't announced by screen readers, so it gives no
accessibility benefit over bold text. For more on headings and accessibility, see
[Accessibility for front-end developers](https://digital.gov/guides/accessibility-for-teams/front-end-development)
on digital.gov.

### How do I continue a numbered list that's interrupted by text?

Use HTML to restart the list at the right number. Replace the `2` in `start="2"`
with the number the list should continue from:

```html
<ol start="2">
<li>List item</li>
<li>List item</li>
<li>List item</li>
</ol>
```

### How do I change list markers to letters or Roman numerals?

Convert the list to HTML and add a `type` attribute to the opening `<ol>` tag:

```html
<ol type="a">
<li>List item</li>
<li>List item</li>
<li>List item</li>
</ol>
```

Available `type` values:

- `a`: lowercase letters
- `A`: uppercase letters
- `i`: lowercase Roman numerals
- `I`: uppercase Roman numerals

### How do I create nested lists?

Always include a blank line between a list and the content before it. Otherwise
the list won't render correctly.

- **Bulleted lists:** start a line with `*` and a space.
- **Numbered lists:** start a line with `1.` and a space.

To nest, add four spaces before the marker for each level:

```markdown
* First-level item
    + Second-level item
        - Third-level item
            * Fourth-level item
```

- First level: no spaces, use `*`
- Second level: four spaces, use `+`
- Third level: eight spaces, use `-`
- Fourth level: twelve spaces, use `*`

Second-level bullets sometimes show `+` instead of `*` after a Word import. That's
expected, and using `+` for second-level items makes the nesting easier to see.
Use the **Preview** tab in the text editor to check your nesting before
downloading the PDF.

### How do I add a link to a website?

Use either format:

```markdown
[text you want linked](URL)
```

```html
<a href="URL">text you want linked</a>
```

For writing clear link text, see
[Links in the style guide](STYLE_GUIDE.md#links) and
[TASK-LINK-TEXT](EDITOR_TASKS.md#task-link-text).

### How do I link to text that isn't a heading?

You can link to any heading by default. To link to other text, add a custom ID
to it first, then link to that ID.

To add an ID to a whole paragraph, add this on the line after it:

```markdown
{: #your-custom-id }
```

To add an ID to a word or phrase, wrap it inline:

```html
<span id="your-custom-id">Text</span>
```

Then link to the ID with a standard Markdown link:

```markdown
[Read about program priorities](#your-custom-id)
```

To fix a broken internal link, see
[TASK-LINK-FIX-BROKEN](EDITOR_TASKS.md#task-link-fix-broken).

## Tables

### How do I control table column widths?

Add a width class to a column's header cell in your Markdown table:

```markdown
| Column header {: .w-40 } | Column header {: .w-40 } | Column header {: .w-20 } |
| --- | --- | --- |
```

Widths go in steps of 5. If you set widths for every column, they must add up to
100. For all width options and the automatic sizing rules, see
[Automatic table styling](TABLES.md#how-users-can-override-these).

### Why is my table showing as plain text instead of a table?

The most common cause is a missing separator row between the header row and the
body rows. Add a `| --- |` separator for each column after the header row:

```markdown
| Column header | Column header |
| --- | --- |
| Cell content | Cell content |
```

Also check that every row has the same number of cells as the header row.
Missing or extra cells break the table.

### My table cell content appears side by side instead of stacked. How do I fix it?

This happens when a cell holds more than one element, such as two paragraphs, or
a paragraph followed by a bulleted list. The PDF renderer places them in
side-by-side columns. Convert the cell to HTML and wrap all of its content in a
single `<ul>`, so the renderer treats it as one element:

```html
<table>
<thead>
<tr>
<th class="w-80"><p><strong>Column header</strong></p></th>
<th class="w-20"><p><strong>Column header</strong></p></th>
</tr>
</thead>
<tbody>
<tr>
<td>
<ul>
<li>Intro sentence here:
<ul>
<li>First sub-item</li>
<li>Second sub-item</li>
<li>Third sub-item</li>
</ul>
</li>
</ul>
</td>
<td><p>10 points</p></td>
</tr>
</tbody>
</table>
```

If a cell has a bold label followed by normal text on its own line and they
appear side by side, add a `<br>` between the bold label and the text.

### Why does a checkbox split from its label in a table cell?

This can happen when a table cell has a checkbox glyph next to a linked label,
such as in an attachments checklist. The checkbox and the link text can wrap onto
separate lines. Converting the table from HTML to Markdown usually fixes it.

### Why did NOFO Builder import my table as HTML instead of Markdown?

NOFO Builder keeps a table as HTML when it's too complex for Markdown. Two
structures cause this:

- **Merged cells** (`colspan` or `rowspan`): Markdown can't span cells across
  rows or columns.
- **Multiple header rows:** Markdown supports only one header row.

These are also what the NOFO design standards call complex tables, and they make
the designed PDF harder to use with assistive technology. To fix one, simplify
the table in your Word document before importing: split it into simple tables,
each with a single header row and no merged cells. See
[TASK-TABLE-SIMPLIFY-MERGED](EDITOR_TASKS.md#task-table-simplify-merged) and
[TASK-TABLE-SPLIT](EDITOR_TASKS.md#task-table-split).

### Do I need to do anything special if a table spans multiple pages?

No. NOFO Builder generates tables with proper header and body structure, which
lets the header row repeat at the top of each new page and be announced
correctly by screen readers.

- Don't repeat the header row manually. That creates duplicate content in the
  document structure and can confuse screen readers.
- Rows aren't split across pages. If a row doesn't fit, the whole row moves to
  the next page.
- Occasionally the header row doesn't repeat when only a few rows carry over.
  That's expected.

It's still worth previewing the PDF to confirm the table reads as expected.

If only the last row or two of a table would land on a new page, you can add a
page break so the whole table starts on a fresh page. Only do this if the entire
table fits on one page. Place the break before the table's caption or before the
heading and introduction that lead into it, so the table and its context stay
together.

## Page layout and callout boxes

### How do I add a manual page break?

Use one of these codes on its own line, with an empty line above and below:

```text
page-break
```

```text
page-break-after
```

When possible, use the subsection's page break setting instead
([TASK-PAGEBREAK-ADD](EDITOR_TASKS.md#task-pagebreak-add)). Subsection page
breaks are easier to track and remove later.

### When should I add a manual page break?

Add one only to fix a specific layout or readability problem you've found while
reviewing the designed PDF:

- A heading appears alone at the bottom of a page, without the content that
  follows it.
- A table would split awkwardly across pages, and the whole table fits on one
  page.
- A single line of a paragraph appears alone at the top or bottom of a page.

Don't use manual page breaks to:

- Add spacing between sections. Margins and spacing are applied automatically.
- Fix layout in the Word document before importing. Page breaks added in Word
  may not carry over predictably.
- Replace empty paragraphs. Use a page break code, not blank lines.

Review the PDF preview before adding page breaks. Excess white space, such as a
nearly empty page in the middle of a section, adds pages and makes the NOFO
harder to read. Correct excess white space before publication. To remove page
breaks, see [TASK-PAGEBREAK-REMOVE](EDITOR_TASKS.md#task-pagebreak-remove).

### When should I use a callout box?

Use callout boxes for short, high-priority content that applicants need to notice
quickly, such as:

- Contact and support information.
- Reminders and post-award requirements.
- Action-oriented information that stands on its own.

Don't use callout boxes for long narrative content, detailed policy
explanations, or table footnotes. If a note only explains how to read a specific
table, such as what an asterisk means, keep it as a footnote directly below the
table.

If you're unsure, ask yourself: would an applicant miss this if it weren't set
apart? If not, it probably doesn't need a callout.

To turn a subsection into a callout box, see
[TASK-CALLOUT-TOGGLE](EDITOR_TASKS.md#task-callout-toggle). When importing from
Word, NOFO Builder treats any 1x1 table as a callout box, so put callout content
in a 1x1 table before importing.

## Endnotes

### Why does NOFO Builder use endnotes instead of footnotes?

NOFO Builder converts all references to endnotes, whether your Word document uses
footnotes or endnotes. You don't need to convert them yourself before importing.

SimplerNOFOs research found that inconsistent formatting across agency NOFOs
increases the burden on applicants. Collecting all references at the end of the
document gives applicants a consistent, predictable reading experience.

### How should I add endnotes in Word?

NOFO Builder supports two formats. Pick one and use it throughout the document.
Mixing them makes numbering hard to maintain and can leave endnotes flagged and
unlinked.

- **Word's endnote tool** (References, then Insert Endnote): Word manages the
  numbering and superscript for you. If Word won't let you insert an endnote, the
  section may be locked; use the bracket format instead.
- **Bracketed numbers** typed in the text, like `[1]`, with a matching citation
  list under an Endnotes heading at the end of the document. Use this format if
  Word's endnote tool isn't available in your template, or if you're working from
  an Announcement Module export.

For both formats:

- Every reference number needs a matching endnote, and every endnote needs a
  matching reference.
- Number references in order, starting at 1, without repeating a number.
- To cite a source again, use the next number and repeat the citation. Don't
  reuse an earlier number.
- The Endnotes heading must use the same heading level as your top-level NOFO
  sections, such as Step 1: Review the Opportunity. A heading that's only bold or
  larger won't be recognized, and your endnotes won't link.

For how NOFO Builder converts endnotes on import, see
[Endnotes in Word imports](endnote-import.md) and the
[import rules for footnotes and endnotes](IMPORT_RULES.md#footnotes--endnotes).

### Why can't I reuse an endnote number to cite the same source twice?

Each endnote number must be unique and in order, for two reasons:

- **Accessibility:** Section 508-compliant PDFs need a unique identifier for each
  endnote in the document's tag structure. Reusing a number can break that
  structure for screen reader users.
- **Readability:** unique, sequential numbers make citations easier to follow.

Each endnote also has only one link back (the ↑ arrow) to a single in-text
reference. If you reused `[2]` in two places, the ↑ link would return readers to
only one of them.

### Why isn't my endnote linking to its entry in the endnotes list?

This is usually caused by changed HTML in the in-text reference. Check that the
code uses straight quotation marks (`"`), not curly quotes (`”`). Curly quotes
break the link.

To fix it, go to the Endnotes section at the bottom of your NOFO and select
**Edit**. In the text editor, find the endnote HTML and replace any curly quotes
with straight ones. The correct format is:

```html
<sup><a href="#endnote-1" id="endnote-ref-1">[1]</a></sup>
```

To investigate other endnote problems, see
[TASK-ENDNOTE-REVIEW](EDITOR_TASKS.md#task-endnote-review).

### How do I add a new endnote to an existing Endnotes section?

Edit the endnote directly in NOFO Builder instead of re-importing.

1. **Add the in-text reference.** Go to the section where the reference belongs
   and select **Edit**. Add the reference as a bracketed number, like `[6]`, or in
   HTML:

   ```html
   <sup><a href="#endnote-6" id="endnote-ref-6">[6]</a></sup>
   ```

   Use straight quotation marks (`"`), not curly quotes.
2. **Add the citation.** Go to the Endnotes section and select **Edit** on its
   subsection. Each endnote is an HTML list item. Add a new one that follows the
   pattern of the others:

   ```html
   <li id="endnote-6" tabindex="-1">
   <p>
   Author, A. (Year). <em>Title of the source.</em> Publisher.
   <a href="#endnote-ref-6">↑</a>
   </p>
   </li>
   ```

   The `id` on the list item must match the `href` in the in-text reference, and
   the `href` on the ↑ link must match the `id` on the in-text reference.
3. **Save and preview.** Select **Save subsection**, then preview the PDF to
   confirm the endnote links both ways: from the reference to the citation, and
   back.

## Appendices and subsections

### How do I add an appendix?

Use **Add Appendix** when you need to add appendix content after importing, for
example when the appendix was kept in a separate Word document. It creates one
empty section named Appendix. You then add each appendix as a subsection.

A NOFO can have only one Appendix section. After it's created, **Add Appendix**
no longer appears in the menu.

**Add the Appendix section**

1. Open the NOFO in the editor.
2. Open the **NOFO actions** menu and select **Add Appendix**.
3. Follow the link in the confirmation message, or scroll to Appendix.
4. Select **Configure section**.

**Add each appendix**

1. On the **Configure section** page, select **Add subsection**.
2. Enter the name of the appendix, such as Funding details table or Sample
   reporting template.
3. Select a heading level. A heading level is required when the subsection has a
   name.
4. Enter or paste the appendix content into **Subsection content**.
5. Select **Save subsection**.

To add more, return to **Configure section** and select **Add subsection** again.
Use the **Add subsection** button next to an existing entry to place the new
appendix right after it.

If the appendix has wide tables, select **Use full-width tables for this
section** on the **Configure section** page. This applies to every table in the
Appendix section.

**Good to know**

- Appendix appears after Endnotes and before Modifications, when those sections
  exist.
- Appendix appears in the table of contents but doesn't get its own title page.
- Appendix content is included in the HTML view, the PDF, and the Word export.
- **Add Appendix** is available only while the NOFO can be edited. It isn't
  available for published, cancelled, or archived NOFOs.

### How do I delete a subsection?

See [TASK-SUBSECTION-DELETE](EDITOR_TASKS.md#task-subsection-delete). Deleted
subsections can't be recovered, and the NOFO must be in Draft status.

## PDF metadata

### How do I write the metadata subject and keywords?

The subject and keywords make your designed PDF easier to find and are part of
the PDF's accessibility metadata.

- **Subject:** one sentence that adds detail beyond the title. Follow the formula
  in the style guide: "A notice of funding opportunity from the [agency] to [the
  purpose of the NOFO]."
- **Keywords:** 8 to 10 specific terms from the NOFO, separated by commas.
- **Author:** the full name of the agency, followed by its acronym in
  parentheses.

For examples, see [Taglines and metadata in the style guide](STYLE_GUIDE.md#taglines-and-metadata).
To enter them in NOFO Builder, see
[TASK-PDF-METADATA](EDITOR_TASKS.md#task-pdf-metadata).

## NOFO status

### What is the status field?

The status field shows where a NOFO is in the design and review process, and it
controls what you can do with the NOFO. It's at the top of each NOFO page, and
each status shows a description when you select it.

Statuses fall into three general groups:

- **Draft:** the NOFO is being designed. You can edit it, re-import it, and
  delete it or its subsections.
- **In progress or under review:** you can still edit the NOFO, but you can't
  delete it or its subsections. Some of these statuses also prevent
  re-importing.
- **Published or cancelled:** you can't edit or delete the NOFO. To change a
  published NOFO, add modifications.

NOFO Builder doesn't send a notification when a status changes, so let your team
know when you update it. For exactly what each status allows, see
[Before you start: NOFO status](EDITOR_TASKS.md#before-you-start-nofo-status).

## Writing and style

### Where can I find guidance on NOFO content, style, and formatting?

The [SimplerNOFOs Style Guide](STYLE_GUIDE.md) covers writing and style for NOFOs,
including plain language, capitalization, dates and times, lists, links, and
tables. Use it for any content or style question not covered here.

[NOFO design standards](DESIGN_STANDARDS.md) adds design and accessibility
guidance for headings, links, line breaks, and tables, with a checklist to use
before publishing.
