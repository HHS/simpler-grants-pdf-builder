# Automatic Table Styling

NOFO Builder adds CSS classes to tables automatically so they look right in the PDF without manual formatting. Some classes are added once, when a NOFO is imported or re-imported, and written into the Markdown so users can change them. Others are added every time a page or PDF is rendered.

Import-time rules are cataloged in [IMPORT_RULES.md](IMPORT_RULES.md). This page gathers every table styling rule in one place, from both stages.

---

## Render-time rules

These run in the `add_classes_to_tables` and `add_captions_to_tables` template filters (`nofos/nofos/templatetags/`). The logic lives in `nofos/nofos/templatetags/utils/__init__.py`.

### Table size class

`add_class_to_table()` adds one class to every `<table>`. The first matching rule wins:

| Rule | Class |
| --- | --- |
| A header cell reads exactly "Recommended For" | `table--large` |
| A header cell reads exactly "Criterion" | `table--criterion` |
| No words in any `<td>` and fewer than 4 columns | `table--small` |
| More than 120 words across all `<td>`s | `table--large` |
| 3 or more columns | `table--large` |
| 2 columns or fewer | `table--small` |

`table--large` tables are full width. `table--small` tables size to their content in portrait NOFOs and are full width in landscape NOFOs.

### Empty rows

`add_class_to_table_rows()` adds `table-row--empty` to any `<tr>` with no words in it.

### Captions

`add_caption_to_table()` looks at the paragraph right before a table. If it starts with "Table: ", it's moved inside the table as a `<caption>`, and the table gets `table--with-caption`.

### Points columns

The column is marked once, on import (see [Points columns on import](#points-columns-on-import) below). At render time, `add_class_to_points_columns()` styles marked columns only. It copies `col--points` from the header to the column's non-empty body cells. The CSS then shrinks the column to fit its content (`width: 1%`) and keeps body cells on one line (`white-space: nowrap`), so "10 points" doesn't wrap onto two lines. The header can still wrap.

The class is dropped from the column, so it wraps normally again, when:
- the header also has a width class (`w-*`), so the user's width wins
- a body cell no longer looks like a point value, for example after an edit to "Up to 5 points, see the budget section", so long text can't push the table past the page edge
- the table has `colspan`/`rowspan` cells

Tables without the marker are never changed. That includes every NOFO imported before this rule existed.

---

## Import-time width classes

When a NOFO is imported or re-imported, `get_width_class()` in `nofos/nofos/nofo_markdown.py` adds a class to each header cell. These are written into the Markdown (for example `| Component {: .w-45 } |`), so users can see and change them in the editor. See IMPORT-027 and IMPORT-054 in [IMPORT_RULES.md](IMPORT_RULES.md).

### Points columns on import

`get_points_column_indexes()` (`nofos/nofos/templatetags/utils/__init__.py`) finds scoring columns. A column is a points column when both of these are true:

1. Its header cell (first row), lowercased with `*`, `:` and extra whitespace removed, matches
   `^(max(imum)?\s+)?points?(\s+(value|values|possible|available))?$`.
   For example: "Point value", "Points", "Points value", "Point values", "Maximum points", "Points possible".
2. Every non-empty body cell in the column is short and point-like, matching
   `^(up to\s+)?\d+(\s*[-–—]\s*\d+)?(\s*(points?|pts\.?))?$`.
   For example: "10 points", "5", "0–10 points", "Up to 5 points", "3 pts".

Tables with `colspan`/`rowspan` cells, or rows with different numbers of cells, are skipped. The header of a points column gets `col--points`, for example `| **Point value** {: .col--points } |`. This works for any column count and any column position.

### Other header cells

- 3 columns: `w-33`, with header text overrides for application checklists: "Component" → `w-45`, "How to upload…"/"How to submit…" → `w-40`, "Page limit" → `w-15`
- 4 columns: `w-25`
- 5 columns: `w-20`

A points column gets `col--points` instead of these.

---

## How users can override these

- **Set a column width:** add a width class to a header cell in the Markdown editor, for example `| Point value {: .w-25 } |`. Any class from `w-5` to `w-100` (in steps of 5, plus `w-33` and `w-66`) works.
- **Points columns:** remove `{: .col--points }` to turn it off, or replace it with a width class such as `{: .w-25 }` to set a fixed width. If both are there, the width class wins. To turn it on for a NOFO imported before this rule, add `{: .col--points }` to the points column's header.
- **Make every table in a section full width:** on the section page, check **Use full-width tables for this section**. This adds `section--tables-full-width` to the section, which makes `table--small`, `table--large` and `table--criterion` tables 100% wide. Points columns still shrink to fit inside a full-width table.
