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
- For an existing NOFO, reimport replaces sections and subsections and can lose
  manual edits. It is not a way to apply import repairs to saved edits in place.
  Reimport preserves saved theme, cover and introductory ownership choices.

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

<a id="task-endnote-review"></a>

### TASK-ENDNOTE-REVIEW — Investigate a broken endnote relationship

**Steps**

1. On the NOFO edit page, look for endnote warnings under
   **Before publishing, address the following**.
2. Follow the affected subsection or section link and locate the reference
   and its matching citation entry.
3. Check that each reference has an entry and each entry has a reference;
   identify missing or repeated numbers and broken destinations.
4. If the correction is unclear, contact your grants policy office first.
   If additional help is needed, contact the SimplerNOFOs team.

**Notes**

- Builder supports native Word notes and unambiguous manually bracketed notes.
  Do not recommend adding or removing an Endnotes heading without identifying
  the source authoring workflow.
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
succeed even if metrics could not be saved. See [readability metrics](READABILITY_METRICS.md).

<a id="task-readability-upload"></a>

### TASK-READABILITY-UPLOAD — Check Word or PDF readability without creating a NOFO

**Starting point:** the direct `/nofos/readability/` URL on your Builder environment.
There is no navigation link. This restricted pilot requires an active account,
pilot permission and an enabled feature; signing in alone does not grant access.
If access is denied or the page is unavailable, contact the pilot operator.

**Steps**

1. Open `/nofos/readability/` and review **Document requirements** and
   **How we handle your document**. Use only documents authorized for this pilot.
2. Choose one supported text-based HHS NOFO PDF or unlocked Word `.docx`, then
   select **Analyze document**. Legacy `.doc` and macro-enabled formats are not
   supported.
3. Wait for analysis. If an error appears, follow its guidance and submit again.
4. Read **Measurement scope**, reliability information and any **Calculation
   notes**. For Word, **Why “Estimated”?** under Measurement scope explains the
   metric labels. Word conversion may omit text boxes, headers, footers and image text;
   template instructions and unused draft options can be counted.
   A Word report without a reliability rating explains the tool's limitation;
   it does not mean a problem was detected in your upload.
5. Select **Copy metrics** or **Print / Save as PDF** before leaving the report.
   Use **Analyze another document** for another upload.

This upload does not create a NOFO or save report history. Remove template
instructions and unused options from the copy you upload when they should not
count. Word, PDF and saved-Builder scores can differ; use the same format and
analysis method when tracking revisions. The separate public `/readability/`
route remains PDF-only and has its own availability controls.
See [authenticated readability pilot](AUTHENTICATED_PDF_READABILITY_PILOT.md).

---

Preview and download require the configured PDF service. The controls are
disabled when the app is accessed through localhost; the local walkthrough
did not generate or verify PDFs.

## Maintaining this page

Labels on this page come from these files. When you change one, update the
matching task in the same pull request.

| UI area | Source |
| --- | --- |
| NOFO edit page, section tables, warning tabs | `nofos/nofos/templates/nofos/nofo_edit.html` |
| **NOFO actions** menu | `get_nofo_action_links()` in `nofos/nofos/nofo.py` |
| Subsection edit page, conflict recovery, **Other actions** | `nofos/nofos/templates/nofos/subsection_edit.html`; `NofoSubsectionEditView` in `nofos/nofos/views.py` |
| Word import, name/number confirmation, review warnings | `nofos/nofos/templates/nofos/nofo_import*.html`; `nofos/nofos/templates/nofos/includes/word_import_review.html` |
| Blocking import errors and retry/support labels | `nofos/bloom_nofos/templates/import_error.html`; `nofos/bloom_nofos/import_errors.py` |
| Editable introductory content and restrictions | `nofos/nofos/templates/nofos/nofo_edit.html`; `SubsectionEditForm` in `nofos/nofos/forms.py`; `documentation/EDITABLE_INTRODUCTION.md` |
| Deadline matching/replacement | `nofos/nofos/templates/nofos/nofo_edit_application_deadline.html`; `NofoEditApplicationDeadlineView` in `nofos/nofos/views.py` |
| Readability panel and saved checkpoints | `nofos/nofos/templates/nofos/includes/readability_metrics_panel.html`; `nofos/nofos/templates/nofos/includes/readability_saved_snapshots.html`; `documentation/READABILITY_METRICS.md` |
| Standalone Word/PDF upload and report | `nofos/bloom_nofos/templates/pdf_readability.html`; `documentation/AUTHENTICATED_PDF_READABILITY_PILOT.md` |
| Delete confirmation | `nofos/nofos/templates/nofos/subsection_confirm_delete.html` |
| **Configure section** page | `nofos/nofos/templates/nofos/section_detail.html` |
| **Preview PDF** / **Download PDF** | `nofos/bloom_nofos/templates/includes/print_button.html` |
| Table size rules | `add_class_to_table()` in `nofos/nofos/templatetags/utils/__init__.py` |
| Merged-cell tables kept as HTML | `convert_table()` in `nofos/nofos/nofo_markdown.py` |
| Find & Replace, Remove Page Breaks, Theme options | `nofo_find_replace.html`, `nofo_remove_page_breaks.html`, `nofo_edit_theme_options.html` |
