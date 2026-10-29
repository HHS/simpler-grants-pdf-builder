# NOFO Builder editor tasks

Step-by-step instructions for common tasks in NOFO Builder. NOFO writers,
editors, support staff, and agents can use this reference to understand how
to complete tasks through the interface. Stable task IDs also let other
guides and tools link to the relevant instructions.

**Source-reviewed against:** upstream `main` at `5fe16ad6` (October 20, 2026),
after reviewing PRs closed October 6–20, 2026. Instructions describe merged
source; availability in a deployed environment depends on its version and settings.
The additions in this refresh are source-reviewed only.

**UI validation:** October 9, 2026, local instance at `036d6684` with synthetic content.
Verified subsection opening, renaming, saving and return navigation; callout and
page-break setting persistence; subsection creation; delete confirmation labels
(without submitting deletion); section-wide table-width persistence; metadata
saving; and Find & Replace search/results. Other tasks are source-reviewed only.
PDF generation requires the configured external PDF service and is not verified by local screen checks.

For support staff investigating a problem rather than performing a known edit,
see [quality review and triage](QUALITY_REVIEW_AND_TRIAGE.md). It explains how to
distinguish document corrections, learning needs and product improvements.

## How to use this page

- Each task has a stable ID (for example, `TASK-SUBSECTION-DELETE`). Link to
  the ID, not the heading text. IDs don't change when the wording does.
- Button and link labels are written exactly as they appear on screen, in
  **bold**.
- Tasks start from the **NOFO edit page**: the page you see after opening a
  NOFO from **All NOFOs**, unless a task names another starting point.
- Steps describe the current UI only. If a label on screen doesn't match this
  page, trust the screen and report the mismatch.

### For agents and tools referencing these tasks

When you use a task in a suggestion, report, or comment:

1. Use the **Steps** list without inventing actions. Expand referenced tasks
   so the comment includes the navigation needed to perform the fix. Fill in placeholders like
   `<subsection name>` with the relevant subsection name.
2. Keep instructions short. Include at most 6 steps and link to the explicit task anchor for
   the rest.
3. Check **Before you start** first. If the NOFO is published, most tasks
   need the status changed, or need modifications added, before anything can
   be edited.
4. Don't invent steps. If no task here covers the fix, describe the problem
   and leave out the steps.

## Key concepts

| Term | What it means in NOFO Builder | How it looks in the PDF |
| --- | --- | --- |
| Section | A top-level part of the NOFO (for example, "Step 1: Review the Opportunity"). Shown as a table on the NOFO edit page. | Usually starts on its own cover page, and is a Heading 2 |
| Subsection | A heading and its content, or a headingless body. This is the main unit you edit. | Usually Heading 3–7 and the content under it; lead introductory prose has no heading |
| Heading level | Set on headed subsections; the selector offers Heading 2 to Heading 7. | The size and nesting of the heading; follow the design guidance's H1–H6 limit |
| Callout box | A subsection styled with an accent color to draw attention. | Shaded or colored box |
| Subsection content | Written in **Markdown** in a text editor. Simple tables and lists are Markdown; merged-cell tables and lists requiring source marker semantics are stored as HTML. See [Word list editing](WORD_LIST_IMPORT.md). | Body text, lists, tables |
| Page break | A per-subsection setting that starts it on a new page. | New page before the heading |

### Before you start: NOFO status

The status shows in the summary box near the top of the NOFO edit page.

Statuses fall into three general groups:

| Status group | Can edit content? | Notes |
| --- | --- | --- |
| Draft | Yes | Can also be re-imported; NOFOs and subsections can be deleted |
| In progress or under review | Yes | Can't be deleted. Some of these statuses also prevent re-importing |
| Published or cancelled | **No** | To change a published NOFO, change the status or select **Add modifications** first. Cancelled NOFOs can only be exported |

Each status shows a description when you select it. If a task isn't available,
check the status first.

Archived NOFOs cannot be edited or have subsections deleted. Access also depends
on your account permissions and OpDiv group. **Delete subsection** is available
only for Draft NOFOs; being able to edit does not imply being able to delete.

For complex fixes, contact your grants policy office first. If additional help
is needed, contact the SimplerNOFOs team.

---

## Importing and reviewing Word documents

<a id="task-import-word"></a>

### TASK-IMPORT-WORD — Import a new Word NOFO

**Starting point:** **All NOFOs**, rather than an existing NOFO edit page.

**Steps**

1. Select **Import NOFO**.
2. Under **Select NOFO file**, choose the Word `.docx`, then select **Import**.
3. On the naming page, review the suggested name and select **Save NOFO name**.
4. If prompted for an opportunity number, enter the correct value and select
   **Save opportunity number**. The interim-number option is temporary; replace
   it before publishing.
5. Open the NOFO from **All NOFOs**. Review **Basic information**, **NOFO metadata**,
   **NOFO theme options**, and any import warnings before checking the PDF.

**Notes**

- A recognized Word **Metadata** block supplies structured fields and is removed
  from the imported content. When several recognized blocks exist, the last is
  authoritative; fields are not combined with earlier blocks or legacy labels.
  Replace template placeholders before import. See [Word metadata import](WORD_METADATA_IMPORT.md).
- Builder can omit a leading Word **Title** paragraph during import. The NOFO
  title suggestion comes from metadata, not that omitted paragraph; check it
  before saving the name.
- Word text using the **Strong1** character style imports as bold, retaining
  explicit bold-off overrides and separately applied italics. This applies only
  to a directly defined bold-only style. Other Strong1 definitions retain the
  existing conversion warning behavior; compare their formatting with Word.
  Redundant bold
  formatting imports as a single bold level. Review the result against Word;
  existing saved content receives this handling only when reimported.
- Consecutive Word bullets at the same numbering level import as one list even
  when their internal list IDs differ, avoiding extra gaps between bullet groups.
  Paragraphs still separate lists; numbered-list restarts remain separate.
- Import also repairs clear groups of typed `•` bullets (at least two items).
  Following `o` lines become nested bullets when their parent bullet ends in a
  colon. Standalone `o` lines, isolated bullets, existing lists, and table content
  stay as supplied. Check the nesting after import; other ambiguous marker styles
  need correction in the source. This applies on import/reimport only.
- Empty **Appendix**, **Endnotes**, and **Footnotes** headings at Heading 1 or
  Heading 2 are omitted when they form an unused run at the end of the document.
  Capitalization and a trailing colon do not matter. Text, images, tables, lists,
  child headings, and referenced bookmarks preserve the heading. You can add an
  Appendix or Endnotes section afterward using the existing NOFO actions.
  This cleanup applies on new import and reimport; it does not remove sections
  from already saved NOFOs automatically.
- For an existing NOFO, reimport replaces sections and subsections and can lose
  manual edits. It is not a way to apply import repairs to saved edits in place.
  Reimport preserves saved theme, cover and introductory ownership choices.
- Adjacent bullet and numbered lists remain separate HTML lists after import,
  including within a nested list. Compare their markers and nesting with Word;
  this conversion does not repair previously saved content automatically.

<a id="task-import-recover"></a>

### TASK-IMPORT-RECOVER — Resolve a blocked Word import

**Starting point:** the import error page.

**Steps**

1. Read the error details and **What to do next**. Keep the error code if you
   need support.
2. For a long-heading error, use **Search Word for:** to find each affected
   passage. Check its Word style: use body text for prose, or shorten a real
   heading while preserving its meaning. Use the character limit shown on the
   error page. If a heading and paragraph were joined with Shift+Enter, replace
   that line break with a paragraph break and apply **Normal** to the prose only.
3. For an introductory-structure error, start with the identified content or
   heading. Remove template-only guidance from the import copy, or move
   applicant-facing content into the appropriate section. Change heading levels
   only when the details identify a heading-level problem.
4. Save the corrected Word file. Select **Try the import again**, choose the
   corrected file, and submit it again.
5. If the problem is unclear, use the **NOFO Builder Feedback Form** or email
   link under **Need help resolving this error?** Include the error code and
   what you were trying to do.

**Notes**

- Recoloring a General instructions table pale blue does not make it a supported
  Word instruction text box and does not resolve an introductory-structure error.
- For `IMPORT-INTRODUCTION-STRUCTURE`, no content is saved or replaced; an
  existing NOFO remains unchanged. See [import error codes](IMPORT_ERROR_CODES.md)
  for the recovery that applies to other errors.

<a id="task-template-instructions-review"></a>

### TASK-TEMPLATE-INSTRUCTIONS-REVIEW — Remove leftover template guidance

Use this when **Check for leftover template instructions** appears after import
or reimport, or when you find writer-only notes in the content.

**Steps**

1. For a new import, finish saving the NOFO name and open it from **All NOFOs**.
2. Find the subsection containing writer instructions or unused template options
   and select **Edit** ([TASK-SUBSECTION-EDIT](#task-subsection-edit)).
3. Remove only template guidance and unused options. Keep application deadlines,
   key facts and instructions applicants need. If an option requires a policy
   decision, resolve it with your grants policy office.
4. Select **Save subsection**, then **Preview PDF** to check the result.

Automatic cleanup removes verified blue instruction boxes even when Word’s compatibility copies differ only in spacing before commas or full stops.
Single-cell instruction tables beginning “Instructions for template managers” are also removed from applicant content, including tables that combine manager and writer guidance.
Cleanup does not remove every instruction container. The warning is
an invitation to review, not evidence that all highlighted content is disposable.

---

## Subsections

<a id="task-subsection-edit"></a>

### TASK-SUBSECTION-EDIT — Open a subsection for editing

All subsection-level tasks start here.

**Steps**

1. On the NOFO edit page, find the section table that contains
   `<subsection name>`. Use the side navigation to jump to the section.
2. In that subsection's row, select **Edit**.

You are now on the page titled **Subsection: `<subsection name>`**.

<a id="task-subsection-resolve-conflict"></a>

### TASK-SUBSECTION-RESOLVE-CONFLICT — Recover a save blocked by newer changes

Use this when saving shows **This subsection changed since you opened it.** or
**The editor was updated while this page was open.** Your submission has not
been saved; the page preserves it alongside the latest saved version.

**Steps**

1. Compare **Your unsaved version** with **Latest saved version**, including the
   heading, content, callout and page-break settings.
2. Select **Review and combine changes**. This opens the editor with the latest
   saved version and retains your unsaved version for reference; it does not save.
3. In **Version to save**, bring over the changes you want to keep, preserving
   newer work that should remain.
4. Select **Save combined version**. If someone saved again during your review,
   compare and combine the versions again.

To abandon your unsaved work, select **Discard my changes and return** instead.
Do not refresh away the preserved work or assume that opening the review saved it.

<a id="task-subsection-delete"></a>

### TASK-SUBSECTION-DELETE — Delete a subsection

**Before you start:** The NOFO must be Draft and not archived.

**Steps**

1. Open the subsection ([TASK-SUBSECTION-EDIT](#task-subsection-edit)).
2. Scroll to the bottom of the page and expand **Other actions**.
3. Select **Delete subsection**.
4. On the confirmation page, select **Yes, delete it**.

**Notes**

- Deleting is permanent. There's no undo.
- You can also delete from the section page: select **Configure section**,
  then select **Delete subsection** in the subsection's row.

<a id="task-subsection-add"></a>

### TASK-SUBSECTION-ADD — Add a new subsection

**Steps**

1. Open the subsection that the new one should come **after**
   ([TASK-SUBSECTION-EDIT](#task-subsection-edit)).
2. Expand **Other actions**, then select **Add subsection**.
3. Fill in the heading text, choose a **Heading level**, and add the content.
4. Select **Save subsection**.

**Notes**

- To add a subsection at the very top of a section, select
  **Configure section** on the NOFO edit page, then select the first
  **Add subsection** button.

<a id="task-subsection-split"></a>

### TASK-SUBSECTION-SPLIT — Split a long subsection into two

Use this when a subsection covers more than one topic or is too long to scan.

**Steps**

1. Open the subsection ([TASK-SUBSECTION-EDIT](#task-subsection-edit)).
2. In the content editor, cut the text that should move to the new
   subsection. Select **Save subsection**.
3. Saving returns to the NOFO edit page. Reopen the original subsection,
   expand **Other actions**, then select **Add subsection**.
4. Enter a heading, choose a **Heading level**, and paste the text.
5. Select **Save subsection**.

<a id="task-subsection-rename"></a>

### TASK-SUBSECTION-RENAME — Change a heading's text

**Steps**

1. Open the subsection ([TASK-SUBSECTION-EDIT](#task-subsection-edit)).
2. Edit **Subsection name**.
3. Select **Save subsection**.

**Notes**

- Other parts of the NOFO may link to this heading. After renaming, check the
  **Check broken links** tab on the NOFO edit page if it appears. Renaming
  a subsection keeps its existing heading ID.
- A subsection with no heading shows as **(#`<number>`)**. Its name field
  can't be edited.

---

## Headings and structure

<a id="task-heading-level"></a>

### TASK-HEADING-LEVEL — Fix a skipped or wrong heading level

Use this when headings skip a level, for example going from Heading 3 straight
to Heading 5. Screen reader users rely on heading levels to understand how a
document is organized.

**Steps**

1. On the NOFO edit page, look for **Check heading levels** under
   **Before publishing, address the following**. It lists each heading with
   a problem.
2. Open the subsection that has the problem ([TASK-SUBSECTION-EDIT](#task-subsection-edit)).
3. Change **Heading level** so it's no more than one level deeper than the
   heading above it.
4. Select **Save subsection**.

**Notes**

- The current UI offers Heading 7, but the supplied design/style guidance
  limits structural headings to H1–H6. Do not recommend H7 as an accessibility fix.
- The selector offers Heading 2 through Heading 7 for headed subsections.
  Ordinary section names are Heading 2 and can't be changed here. Opening
  introductory prose is headingless and has no heading-level selector.
- Headings inside the content editor (lines starting with `#`) are separate
  from the **Heading level** setting. Check those too.

<a id="task-callout-toggle"></a>

### TASK-CALLOUT-TOGGLE — Make content a callout box, or remove one

**Steps**

1. Open the subsection ([TASK-SUBSECTION-EDIT](#task-subsection-edit)).
2. Check or uncheck **Is callout box?**.
3. Select **Save subsection**.

**Notes**

- Use callout boxes sparingly. When too much is highlighted, nothing stands
  out. The checkbox is disabled for headingless introductory prose.
- Both **Application Due Date** and **Application deadline** can identify
  imported deadline sidebar callouts. Check the saved content and PDF rather
  than changing the heading just to make it match a different template.

---

## Introductory content

<a id="task-introduction-edit"></a>

### TASK-INTRODUCTION-EDIT — Edit imported Before you get started content

**Before you start:** this task applies when **Before you get started** appears
as a section table with subsection **Edit** links. Qualifying new FY27 Word
imports retain their introductory text this way. Older and unrecognized records
can still use a generated introduction; reimport does not convert those records
into editable introductions.

**Steps**

1. On the NOFO edit page, find the **Before you get started** section table.
2. Select **Edit** in the row containing the prose or child heading to change.
3. Edit the content. Opening prose has a blank, disabled name and no heading-level
   selector; edit its body rather than trying to add the parent heading there.
4. Select **Save subsection**, then **Preview PDF** to check the introduction
   and its links.

**Notes**

- The parent heading and position are fixed. Genuine child headings can be
  edited normally; lead headingless prose cannot be turned into a callout.
- Imported introductory records do not offer the generated **BYB page setting**
  control. A generated record's template control, where available to your
  account, does not edit imported prose.
- Changing structured fields alone does not update authored introductory text.
  For deadline replacements, use [TASK-DEADLINE-UPDATE](#task-deadline-update).
- Keep one populated introduction when reimporting an editable-introduction NOFO.
  Missing, repeated, empty or unsafe introductory structure blocks the replacement.
  See [editable introductory content](EDITABLE_INTRODUCTION.md).

---

## Lists

<a id="task-list-review"></a>

### TASK-LIST-REVIEW — Check imported numbering and nesting

Use this after import, especially when **Check list numbering** appears.
The warning does not block import; it means some source numbering could not be
fully preserved.

**Steps**

1. Finish any new-import naming steps, then open the NOFO from **All NOFOs**.
2. Compare list markers, nesting, continuation paragraphs and restarts with Word.
   Include lists inside table cells.
3. Open the affected subsection ([TASK-SUBSECTION-EDIT](#task-subsection-edit)).
4. Correct the list in its existing Markdown or HTML representation. Preserve
   nested lists inside their parent item and retain required `type` and `start`
   attributes. Do not type a second number inside an automatically numbered item.
5. Select **Save subsection**, then **Preview PDF**. Check any list crossing a
   page boundary.

Supported native Word lists retain letter, Roman or decimal markers and starts
where needed. Unsupported custom numbering and typed marker-like text need
review. Existing records are not converted just by opening or saving them.
See [Word list import and editing](WORD_LIST_IMPORT.md).

Under **Eligibility → Types of eligible organizations**, import/reimport can
restore bullets for explicitly recognized organization-category paragraphs after
a supported domestic-organization introduction. Compare the list with Word,
including definitions and restrictions that must remain outside it. Existing or
mixed lists and unfamiliar category/intro wording are left unchanged; no repair
runs when ordinary edits are saved. See [the bounded eligibility import rule](IMPORT_RULES.md#import-070--missing-eligibility-organization-bullets).

---

## Tables

Most tables are written in Markdown, like this:

```markdown
| Column A | Column B |
| --- | --- |
| Value | Value |
```

**Exception:** tables with merged cells (cells that span more than one row or
column) are stored as **HTML** (`<table>`, `<tr>`, `<td rowspan="2">`). They
look more complicated in the editor, but you edit them the same way.

<a id="task-table-simplify-merged"></a>

### TASK-TABLE-SIMPLIFY-MERGED — Remove merged cells from a table

Use this when review identifies a specific problem with merged cells. Preserve
header relationships and all information; do not remove merges merely because
they exist. If the HTML repair is unclear, contact your grants policy office
first, then the SimplerNOFOs team if additional help is needed.

**Steps**

1. Open the subsection that contains the table ([TASK-SUBSECTION-EDIT](#task-subsection-edit)).
2. In the content editor, find the cells with `rowspan` or `colspan`.
3. Delete the `rowspan="…"` or `colspan="…"` attribute, then add the missing
   `<td>` cells so that every row has the same number of cells. Repeat the
   value in each cell where needed.
4. Select **Save subsection**.
5. Select **Preview PDF** to check the result.

**Notes**

- Editing saved content does not automatically convert HTML to Markdown.
  You can rewrite a simple table in Markdown by hand. Reimport processes the
  uploaded source document, replacing sections and subsections; it does not
  convert your saved edits in place.

<a id="task-table-split"></a>

### TASK-TABLE-SPLIT — Split a large table into smaller tables

Use this when a table has too many columns or rows, or groups more than one
idea.

**Steps**

1. Open the subsection that contains the table ([TASK-SUBSECTION-EDIT](#task-subsection-edit)).
2. In the content editor, find the row where the new table should start.
3. Add a blank line and a short introduction, such as a sentence or a bold
   label, to describe the new table.
4. For Markdown, place a copy of the header and divider lines above the
   moved rows. For HTML, create two complete `<table>` elements, each with
   its own header and body, and move the rows into the correct body. Close
   all table, row, and cell tags; place the introduction between the tables.
   If this HTML change is unclear, contact your grants policy office first,
   then the SimplerNOFOs team if additional help is needed.
5. Select **Save subsection**, then select **Preview PDF** to check.

<a id="task-table-header-row"></a>

### TASK-TABLE-HEADER-ROW — Add or fix a table's header row

**Steps**

1. Open the subsection that contains the table ([TASK-SUBSECTION-EDIT](#task-subsection-edit)).
2. Markdown table: make sure the second line is the divider row
   (`| --- | --- |`). The line above it becomes the header row.
3. HTML table: use `<th>` for header cells, changing both opening and
   closing tags (`<td>…</td>` to `<th>…</th>`). Preserve any attributes
   and check that each header describes its column.
4. Select **Save subsection**.

<a id="task-table-caption"></a>

### TASK-TABLE-CAPTION — Describe a table above it

**Steps**

1. Open the subsection containing the table ([TASK-SUBSECTION-EDIT](#task-subsection-edit)).
2. Check whether a nearby heading above the table describes its contents.
3. If it does not, add a caption on the line directly above the table. Start it
   with "Table:" followed by a short description, and make it bold, for example
   `**Table: Research plan details**`. Or update the nearby heading to describe
   the table accurately.
4. Select **Save subsection**, then **Preview PDF** to check the result.

**Notes**

- A “Table:” prefix is optional when a nearby descriptive heading already serves
  as the caption.
- NOFO Builder turns a paragraph that starts with “Table: ”, directly above a
  table, into the table's caption. See
  [Automatic table styling](TABLES.md#captions).
- Apply the review guidance's caption exemptions before requesting a change.

<a id="task-table-full-width"></a>

### TASK-TABLE-FULL-WIDTH — Make tables full width

Tables are sized automatically using column counts, body-cell word counts,
and special header rules. These are layout rules, not table-complexity criteria.
You can make every table in a section use the full page width.

**Steps**

1. On the NOFO edit page, find the section and select **Configure section**.
2. Check **Use full-width tables for this section**. It saves automatically.

**Notes**

- This applies to every table in the section, not just one.

---

## Page layout

<a id="task-pagebreak-add"></a>

### TASK-PAGEBREAK-ADD — Start a subsection on a new page

**Steps**

1. Open the subsection ([TASK-SUBSECTION-EDIT](#task-subsection-edit)).
2. Check **Add a page break**.
3. Select **Save subsection**.

<a id="task-pagebreak-remove"></a>

### TASK-PAGEBREAK-REMOVE — Remove unnecessary page breaks

**Steps**

1. Open the subsection ([TASK-SUBSECTION-EDIT](#task-subsection-edit)).
2. Uncheck **Add a page break**.
3. Select **Save subsection**.

**Notes**

- If you see the warning "This heading's class is …", unchecking will
  overwrite that class. Contact your grants policy office before changing it; contact the
  SimplerNOFOs team if additional help is needed.
- Import and bulk page-break removal restore breaks for **Eligibility** and
  **Program description** in Step 1, and **Application checklist** in Step 5.
  The subsection checkbox itself can be cleared; a later import or bulk
  removal can restore these defaults.
- To remove many at once, there is a **Remove Page Breaks** page at
  `/nofos/<NOFO id>/remove-page-breaks`. Nothing in the app links to it yet;
  contact your grants policy office first, then the SimplerNOFOs team
  if additional help is needed.

---

## Links

<a id="task-link-fix-broken"></a>

### TASK-LINK-FIX-BROKEN — Fix a broken internal link

**Steps**

1. On the NOFO edit page, open the **Check broken links** tab under
   **Before publishing, address the following**. It lists each broken link
   and where it is.
2. Open that subsection ([TASK-SUBSECTION-EDIT](#task-subsection-edit)).
3. In the content editor, find the link. It looks like `[link text](#some-id)`.
4. To get the target heading ID, open that heading's subsection and select
   **Copy** next to its ID. Keep a copy of any unsaved edits before navigating.
   Return to the broken link and replace its entire destination with the
   copied ID (which already starts with `#`); do not add another `#`.
5. Select **Save subsection**.

<a id="task-link-check-external"></a>

### TASK-LINK-CHECK-EXTERNAL — Check external links

**Steps**

1. On the NOFO edit page, select **Check external links** when it appears
   (the button is shown only when external links are present).
2. Fix any failing links using the content editor ([TASK-SUBSECTION-EDIT](#task-subsection-edit)).

**Missing destinations:** the **Check missing link destinations** tab under
**Before publishing, address the following** lists each affected link and its
subsection. Open that subsection, add the intended destination inside the link's
parentheses (for example, `[See eligibility](#eligibility)`), then select
**Save subsection**. If ordinary text is intended, remove the link markup instead.
Clearing only the destination leaves a warning; these are separate from broken
internal links and are not requested over the network.

<a id="task-endnote-review"></a>

### TASK-ENDNOTE-REVIEW — Investigate a broken endnote relationship

**Steps**

1. On the NOFO edit page, open **Check endnotes** under
   **Before publishing, address the following**.
2. Follow the affected subsection or section link and locate the reference
   and its matching citation entry.
3. Check that each reference has an entry and each entry has a reference;
   identify missing or repeated numbers and broken destinations.
   For a content-format warning, use the quoted block to locate content that
   is not recognized as a citation. Keep valid citation continuation content.
4. If the correction is unclear, contact your grants policy office first.
   If additional help is needed, contact the SimplerNOFOs team.

**Notes**

- Builder supports native Word notes and unambiguous manually bracketed notes.
  Do not recommend adding or removing an Endnotes heading without identifying
  the source authoring workflow.
- Supported Word cross-references reuse a native citation with a unique link ID
  and a return link for each occurrence. Typed superscripts have no relationship
  to recover; replace them with actual Word endnotes or cross-references.
  Import repairs unambiguous duplicate native IDs and extracts a standalone
  References title from the first note. See the [Windows Word FAQ](endnote-import.md#faq-for-authors-using-microsoft-word-on-windows).
- Explicit URLs and DOI identifiers in eligible imported citations are linked
  automatically; incomplete references are not guessed. A native note's isolated
  return arrow is moved inline only when it matches the narrow import rule.
  Existing saved citations are not backfilled.
- Automatic linking happens during import/reimport, not simply when saved
  content is viewed. Correct source-maintained issues in the source; reimport
  replaces sections and subsections and can change child IDs.
- See [the import rules](IMPORT_RULES.md#footnotes--endnotes) for conversion
  behavior. This task identifies the issue; it does not prescribe a universal
  raw-HTML repair.

<a id="task-link-text"></a>

### TASK-LINK-TEXT — Make link text descriptive

Link text like "click here" or a bare URL doesn't tell screen reader users
where the link goes.

**Steps**

1. Open the subsection ([TASK-SUBSECTION-EDIT](#task-subsection-edit)).
2. Change `[click here](https://…)` to text that names the destination, such
   as `[Grants.gov application guide](https://…)`.
3. Select **Save subsection**.

---

## Text across the whole NOFO

<a id="task-find-replace"></a>

### TASK-FIND-REPLACE — Replace text everywhere

**Steps**

1. On the NOFO edit page, select **NOFO actions**, then **Find & Replace**.
2. Enter at least 3 characters in **Find text** and select **Find**.
3. Enter the new text in **Replace with**.
4. In the results table, uncheck any subsections you don't want to change.
5. Select the **Replace** button. Its label describes the selected scope,
   for example **Replace in all subsections**.

**Notes**

- Find & Replace doesn't search NOFO metadata (number, agency, subagency,
  and so on). Use the **Basic information** table for those.

---

## Cover, theme, and PDF metadata

<a id="task-cover-alt-text"></a>

### TASK-COVER-ALT-TEXT — Add or fix cover image alt text

**Steps**

**Before you start:** A cover image must already be present. Otherwise the
**Edit** link opens the upload page.

1. On the NOFO edit page, scroll to **NOFO cover image** and select **Edit**.
2. Update **Enter a short description of the image for screen readers.**
3. Select **Save alternate text**.

<a id="task-cover-image"></a>

### TASK-COVER-IMAGE — Replace or remove the cover image

**Steps**

**Before you start:** A cover image must already be present.

1. On the NOFO edit page, scroll to **NOFO cover image** and select **Edit**.
2. Select **Replace cover image** and follow the upload form, or select
   **Remove cover image** and confirm in the dialog.

<a id="task-theme"></a>

### TASK-THEME — Change theme, cover style, or icon style

**Steps**

1. On the NOFO edit page, scroll to **NOFO theme options** and select
   **Edit**.
2. Choose the **Theme**, **Cover style**, or **Icon style**.
3. Select **Save theme options**.

For HRSA NOFOs, **Cover style** offers **Text only** and **Standard image**.
An existing **Full coverage with image** cover can also be retained as a legacy
value. New HRSA imports start with **Text only**; choose **Standard image** here
to use an image cover.

**Notes**

- New ACL imports can select **ACL (Default)** from the OpDiv even with a blank
  or placeholder opportunity number. Previously imported records are not
  backfilled: if an ACL NOFO still has **NIH (Light)**, explicitly choose
  **ACL (Default)** here. Reimport preserves the saved theme.

<a id="task-pdf-metadata"></a>

### TASK-PDF-METADATA — Fill in PDF metadata (author, subject, keywords)

Author, subject, and keywords are required by the NOFO metadata guidance.

**Steps**

1. On the NOFO edit page, scroll to **NOFO metadata** and select **Edit**.
   You can also use **Edit NOFO metadata** in the **Check PDF metadata** tab.
2. Fill in **NOFO author**, **NOFO subject**, and **NOFO keywords**.
3. Select **Save metadata**.

<a id="task-basic-info"></a>

### TASK-BASIC-INFO — Change the title, number, deadline, agency, or tagline

New-template Tagline headings are imported into this existing field, not a
Tagline subsection. See [tagline import and re-import behavior](TAGLINE_IMPORT.md).

**Steps**

1. On the NOFO edit page, find the field in the **Basic information** table.
2. Select **Edit** in that row.
3. Make the change and save.

<a id="task-deadline-update"></a>

### TASK-DEADLINE-UPDATE — Update the deadline and matching subsection text

**Steps**

1. In **Basic information**, select **Edit** beside **Application deadline**.
2. Enter the new deadline.
3. Review the matching-subsection table, if one appears. Matching rows are
   selected by default; clear any checkbox for text that should not change.
   Imported introductory subsections are included when their text matches.
4. Select **Save application deadline**; its label also indicates selected
   replacements when present.
5. Check the saved deadline and affected subsections, then **Preview PDF**.
   Update differently formatted dates or relative instructions separately.

Matching uses the current deadline's literal text, ignoring case. It does not
interpret dates. Changing the structured field without selected replacements
does not rewrite authored content. Generated introductory deadlines use the
structured field instead.

---

## Checking your work

<a id="task-history-review"></a>

### TASK-HISTORY-REVIEW — Review a NOFO's updates

1. On the NOFO edit page, select **See all updates** beside **Last updated**.
2. Review the latest events. Select **Load More Events** for the next batch.
3. Follow an available comparison link to inspect a subsection's changes.

An administrator enables the indexed history reader separately after deployment,
backfill and a successful completeness check: in **Django admin → Constance →
Config**, check `DOCUMENT_HISTORY_INDEX_ENABLED` and save. No further deployment
or worker restart is required. Uncheck and save to return to the legacy reader.
Until that cutover, the existing reader can still be slow. With indexed reads,
events use exact timestamp order, then event ID for ties; deleted objects retain
history descriptions but have no live comparison link. Concurrent new edits can
shift offset-based batches. Report a timeout rather than repeatedly reloading.
See [history rollout and limitations](DOCUMENT_HISTORY.md).

<a id="task-preview"></a>

### TASK-PREVIEW — Preview the PDF after making changes

**Steps**

1. On the NOFO edit page, select **Preview PDF**. It opens in a new tab.
2. To download a copy, select **Download PDF**.

When readability metrics are enabled, a successful **Download PDF** also saves
a PDF-download readability checkpoint, separate from an import, reimport or
manual checkpoint for the same unchanged content. Repeating the same action on
an unchanged measurement does not add another checkpoint. **Preview PDF** and
failed downloads do not save a readability checkpoint. Both successful preview
and download actions record a PDF-generation audit event and use the configured
PDF service. See [TASK-READABILITY-SAVE](#task-readability-save).

<a id="task-readability-save"></a>

### TASK-READABILITY-SAVE — Check readability and keep a snapshot

**Before you start:** readability metrics must be enabled in your environment.
If the panel is absent, this task is unavailable there.

**Steps**

1. On the NOFO edit page, expand **Readability metrics**. Opening it checks the
   current NOFO; use **Calculate metrics** to request another calculation.
2. Review the results, scope and any **Calculation notes** before interpreting
   the scores.
3. Select **Save these results** to keep a manual checkpoint. Saving checks the
   current NOFO and recalculates if it has changed.
4. Under **Saved snapshots**, expand a checkpoint to see its results. Select
   **See all snapshots** for the full history when that link appears.

Import, reimport, manual saving and successful PDF download each save their own
checkpoint once per unchanged measurement. Calculation alone does not save a
manual checkpoint. Historical results remain available after measurement-version
changes; compare version/profile information before treating a score difference
as a content change. Automatic saves are best effort: an import or download can
succeed even if metrics could not be saved. See [readability metrics](readability/READABILITY_METRICS.md).

<a id="task-readability-upload"></a>

### TASK-READABILITY-UPLOAD — Check Word or PDF readability without creating a NOFO

**Starting point:** **Readability Checker** at the direct
`/nofos/readability-checker/` URL on your Builder environment.
There is no navigation link. This restricted pilot requires an active account,
pilot permission and an enabled feature; signing in alone does not grant access.
If access is denied or the page is unavailable, contact the pilot operator.

**Steps**

1. Open `/nofos/readability-checker/` and review **Document requirements** and
   **How we handle your document**. Use only documents authorized for this pilot.
2. Choose one supported text-based HHS NOFO PDF or unlocked Word `.docx`, then
   select **Analyze document**. Legacy `.doc` and macro-enabled formats are not
   supported. For PDFs, keep genuine NOFO identifiers in the first five pages;
   recognition needs two distinct signal types, such as an agency name and an
   opportunity number. Blank templates may not be recognized.
3. Wait for analysis. If an error appears, follow its guidance and submit again.
4. Read **Measurement scope**, reliability information and any **Calculation
   notes**. For Word, **Why “Estimated”?** under Measurement scope explains the
   metric labels. Word conversion may omit text boxes, headers, footers and image text;
   template instructions and unused draft options can be counted.
   A Word report without a reliability rating explains the tool's limitation;
   it does not mean a problem was detected in your upload.
5. Select **Copy metrics** or **Print / Save as PDF** before leaving the report.
   Use **Analyze another document** for another upload.

Profiles are selected automatically; there is no profile setting to choose.
Check the report's **Measurement version** when comparing results. Version 0.7.0
changes passive treatment of “as defined by” modifiers; use the same version and
format to compare content revisions.

This upload does not create a NOFO. Ordinary unsaved reports have no retained history; authorized reviewers can explicitly save Word comparisons as described in [TASK-WORD-COMPARISON](#task-word-comparison). When usage recording
is enabled, **How we handle your document** explains that content-free usage/error
records include the attempted file category (PDF, DOCX or unknown) and are kept
without automatic expiration by default; they exclude your
identity, filename, document text and scores. Remove template
instructions and unused options from the copy you upload when they should not
count. Keep instructions applicants need. An in-progress draft can be checked
before publication design, but favorable scores do not establish publication
readiness. Compare drafts with the same content scope.
Word, PDF and saved-Builder scores can differ; use the same format and
analysis method when tracking revisions. The separate public `/readability-checker/`
route remains PDF-only and has its own availability controls.
See [authenticated readability pilot](readability/AUTHENTICATED_PDF_READABILITY_PILOT.md).

---

Preview and download require the configured PDF service. The controls are
disabled when the app is accessed through localhost; the local walkthrough
did not generate or verify PDFs.

## Synthetic local design pilot

These tasks apply only to the isolated synthetic profile, not a deployed Builder
or an ordinary NOFO. They were checked in local Chrome on October 20, 2026.
See [local host setup and limitations](design-pilot/DESIGN_PILOT_LOCAL_HOST.md).

<a id="task-design-pilot-import"></a>

### TASK-DESIGN-PILOT-IMPORT: Import an invented Word document

**Starting point:** `/design-pilot/` on the separately configured localhost
instance. The profile must be started with a private scratch database and no
provider credentials. Sign in with its ordinary synthetic test account.
This route is unavailable under normal settings. Do not upload real documents.

**Steps**

1. Under **Synthetic NOFO Word document**, choose one invented `.docx` file,
   no larger than 1 MB.
2. Select **This file contains invented information only.**
3. Select **Import candidate**.
4. If an error appears, follow its guidance, choose the corrected file and
   submit again. A retry of the same source checks the existing candidate’s
   integrity and reopens it if valid. If invalid, the upload shows recovery
   guidance without replacing the candidate.
5. On **Review synthetic candidate**, check the source name, conversion
   warnings and saved design-change count.

<a id="task-design-pilot-review"></a>

### TASK-DESIGN-PILOT-REVIEW: Change presentation and optionally view HTML

**Starting point:** **Review synthetic candidate** after the local import.

**Steps**

1. To change the theme, select **Theme**, enter **Reason for this change** and
   select **Save theme**. Choices follow your current group permissions and
   the candidate's design restrictions, not the OpDiv named in the upload.
   A permitted current legacy theme can be retained, but cannot be selected
   again after changing away from it.
2. To change table widths, choose **Standard** or **Full width** for the
   relevant section, enter a reason and select that section's **Save table width**.
   This applies to every table in that section, not one table.
3. Confirm the saved setting and **Saved design changes** count. Saving an
   unchanged setting does not add a change.
4. Optionally select **View current HTML (opens a new tab)**. It uses Builder's
   existing templates but does not verify PDF pagination. External links are
   inactive in this preview; stored source content remains unchanged.
5. If **Request not saved** appears, use **Return to current candidate**,
   review its latest state and enter the intended change again. An old HTML
   link must also be reopened from the current candidate.

If the error says the candidate's content changed outside the pilot, ask the
developer running it to follow [targeted recovery](design-pilot/DESIGN_PILOT_LOCAL_HOST.md#recover-a-candidate-after-an-outside-content-edit).
Returning to the candidate or uploading the same file will not repair it. The
developer must remove the affected candidate and its associated NOFO before you
upload the original file again; this removes that candidate's saved changes.

**PDF unavailable** is expected. Cover changes, acceptance, publication,
production transfer and discard are not implemented in this slice. The human
login is not an agent credential. Do not use ordinary editor tasks to bypass the
local profile's restrictions. Stopping the server does not erase the scratch
database or the source documents it contains.

<a id="task-design-pilot-access"></a>

### TASK-DESIGN-PILOT-ACCESS: Manage access to one synthetic candidate

**Starting point:** **Review synthetic candidate** on the isolated local pilot,
signed in as that candidate's owner. Use invented information only. This action
does not configure or start an agent runtime.

**Steps**

1. Under **Candidate-only agent access**, select **Create agent access** (or
   **Create or replace agent access** when a key is already active).
2. On **Candidate access created**, copy the key only into the approved local
   client. Keep it out of screenshots, URLs, chats, issues and logs. Do not share
   your Builder cookie or give the client broad host/database access.
3. Select **Return to current candidate**. The key is not shown there again;
   the page shows **Active**, the latest expiry and request count instead.
4. To stop access early, select **Revoke agent access** on that candidate.
5. For a lost key, select **Create or replace agent access**. After **Expired**
   or **Request limit reached** appears, select **Create new agent access** to
   reconnect the client. Creating access immediately invalidates the previous key.

The status updates when you load or refresh the review page. **No active access**
means no key has been issued, or access was revoked. **Revoke agent access** is
disabled when access is no longer active. The server enforces expiry and request
limits on every client request even while an older review page remains open.

Access ends after 20 minutes or 100 admitted requests. The client can read this
candidate and request theme/table-width changes only. It cannot accept, transfer,
publish or discard a design. See the [interface protocol and limits](design-pilot/DESIGN_CANDIDATE_INTERFACE.md).

<a id="task-design-pilot-findings"></a>

### TASK-DESIGN-PILOT-FINDINGS: Review findings on a synthetic candidate

**Starting point:** **Review synthetic candidate** in the isolated local pilot,
signed in as the candidate owner. Invented information only. Acceptance, rejection
and deletion are not available in this slice.

**Steps**

1. Read the **Ready for review** alert and its counts.
   Import processing is complete, but this is not a production NOFO or acceptance.
2. Read each finding's evidence and next step. **Review affected section**
   opens the relevant read-only imported text. The retained Word conversion
   output is also available below the sections.
3. For a nonblocking **Word conversion** warning only, compare the relevant
   source and enter **Why can this warning be acknowledged?** Then select
   **Acknowledge warning**. Confirm the recorded person, time and reason.
4. For blocking findings, follow their next step. Acknowledgment cannot clear
   them. Correct missing information, wording or structure in the source and
   import a fresh synthetic copy; never guess the intended value.
5. Use the existing theme/table-width controls for presentation corrections.
   Changes invalidate old review evidence. Optionally select **View current HTML
   (opens a new tab)**; **PDF unavailable** is expected and not a blocker.
6. If **Warning not acknowledged** appears, review the refreshed findings.
   An unchanged warning keeps your explanation in its form; submit it again only
   after checking the current candidate. If the warning changed or is no longer
   available, the old explanation appears separately for copying and is not
   automatically reused. If **Request not saved** appears instead, copy your
   explanation from the read-only field, select **Return to current candidate**,
   and review the latest checks before retrying. These unsaved drafts remain
   only in the returned page; copy them before leaving or refreshing if needed.

See [review scope and limits](design-pilot/DESIGN_CANDIDATE_REVIEW.md). A clean diagnostic
report is not complete source/content/asset verification or design acceptance.

## Maintaining this page

Labels on this page come from these files. When you change one, update the
matching task in the same pull request.

| UI area | Source |
| --- | --- |
| Synthetic local candidate upload, changes and HTML review | `nofos/nofos/templates/nofos/design_pilot_*.html`; `nofos/nofos/design_pilot_views.py`; [local profile guide](design-pilot/DESIGN_PILOT_LOCAL_HOST.md) |
| NOFO edit page, section tables, warning tabs | `nofos/nofos/templates/nofos/nofo_edit.html` |
| **NOFO actions** menu | `get_nofo_action_links()` in `nofos/nofos/nofo.py` |
| Subsection edit page, conflict recovery, **Other actions** | `nofos/nofos/templates/nofos/subsection_edit.html`; `NofoSubsectionEditView` in `nofos/nofos/views.py` |
| Word import, name/number confirmation, review warnings | `nofos/nofos/templates/nofos/nofo_import*.html`; `nofos/nofos/templates/nofos/includes/word_import_review.html` |
| Blocking import errors and retry/support labels | `nofos/bloom_nofos/templates/import_error.html`; `nofos/bloom_nofos/import_errors.py` |
| Editable introductory content and restrictions | `nofos/nofos/templates/nofos/nofo_edit.html`; `SubsectionEditForm` in `nofos/nofos/forms.py`; `documentation/EDITABLE_INTRODUCTION.md` |
| Deadline matching/replacement | `nofos/nofos/templates/nofos/nofo_edit_application_deadline.html`; `NofoEditApplicationDeadlineView` in `nofos/nofos/views.py` |
| Readability panel and saved checkpoints | `nofos/nofos/templates/nofos/includes/readability_metrics_panel.html`; `nofos/nofos/templates/nofos/includes/readability_saved_snapshots.html`; `documentation/readability/READABILITY_METRICS.md` |
| Standalone Word/PDF upload and report | `nofos/bloom_nofos/templates/pdf_readability.html`; `documentation/readability/AUTHENTICATED_PDF_READABILITY_PILOT.md` |
| Delete confirmation | `nofos/nofos/templates/nofos/subsection_confirm_delete.html` |
| **Configure section** page | `nofos/nofos/templates/nofos/section_detail.html` |
| **Preview PDF** / **Download PDF** | `nofos/bloom_nofos/templates/includes/print_button.html` |
| Table size rules | `add_class_to_table()` in `nofos/nofos/templatetags/utils/__init__.py` |
| Merged-cell tables kept as HTML | `convert_table()` in `nofos/nofos/nofo_markdown.py` |
| Find & Replace, Remove Page Breaks, Theme options | `nofo_find_replace.html`, `nofo_remove_page_breaks.html`, `nofo_edit_theme_options.html` |


<a id="task-word-comparison"></a>

### TASK-WORD-COMPARISON — Compare passive sentence percentages

**Before you start:** an operator must enable comparisons and grant you
**Can save passive sentence comparisons** in addition to Readability Checker access.

1. Complete [TASK-READABILITY-UPLOAD](#task-readability-upload) with a Word file.
2. On the report, enter **Microsoft Word for Windows passive sentences (%)** for
   that same whole-document copy. Enter zero if its displayed percentage is zero.
3. Select **Save comparison** within 30 minutes. This retains the Readability Checker
   result and entered percentage. The report reloads with a **Comparison saved**
   confirmation; there is no next entry page and nothing is saved while typing.
   If a red field error appears, correct the percentage and select **Save
   comparison** again.
4. Metrics viewers can follow **View passive sentence comparisons**. The table is
   newest first. Expand **View details** in **Calculation version** for profile and
   input-processing identities. Use **View chart data** for exact plotted values.

The trend plots Readability Checker minus Microsoft Word for Windows in percentage
points by save date; positive values mean the Readability Checker percentage is
higher. Different documents and calculation versions can affect the trend.
There is no correction or investigation workflow in this MVP; analyze and save a
new run for a new comparison. See the [operator guide](readability/WORD_COMPARISONS.md)
for permissions, retention, deletion and deferred enhancements.
