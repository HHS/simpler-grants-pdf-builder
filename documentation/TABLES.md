# Automatic Table Styling

NOFO Builder adds CSS classes to tables automatically so they look right in the PDF without manual formatting. Some classes are added once, when a NOFO is imported. Others are added every time a page or PDF is rendered, so they also apply to NOFOs that were imported before the rule existed, and to tables users edit by hand.

Import-time rules are cataloged in [IMPORT_RULES.md](IMPORT_RULES.md). This page covers the render-time rules, plus the import-time width classes they interact with.

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

`add_class_to_points_columns()` finds scoring columns like "Point value" and adds `col--points` to every cell in that column, header included. The CSS shrinks the column to fit its content and keeps body cells on one line, so "10 points" doesn't wrap onto two lines. The header can still wrap.

A column is a points column when all of these are true:

1. Its header cell (first row), lowercased with `*`, `:` and extra whitespace removed, matches
   `^(max(imum)?\s+)?points?(\s+(value|values|possible|available))?$`.
   For example: "Point value", "Points", "Points value", "Point values", "Maximum points", "Points possible".
2. Every non-empty body cell in the column is short and point-like, matching
   `^(up to\s+)?\d+(\s*[-–—]\s*\d+)?(\s*(points?|pts\.?))?$`.
   For example: "10 points", "5", "0–10 points", "Up to 5 points", "3 pts".
3. The header cell doesn't already have a width class (`w-*`).

The rule is skipped for the whole table when any cell has a `colspan` or `rowspan`, or when rows have different numbers of cells, since columns can't be lined up reliably.

It works for any column count and any column position. One exception: imported tables with 3–5 columns already get a `w-*` class on every header (see below), so rule 3 skips them. Those widths are wide enough that points cells don't wrap.

---

## Import-time width classes

When a NOFO is imported, `get_width_class()` in `nofos/nofos/nofo_markdown.py` adds a width class to each header cell, based on column count:

- 3 columns: `w-33`, with header text overrides for application checklists: "Component" → `w-45`, "How to upload…"/"How to submit…" → `w-40`, "Page limit" → `w-15`
- 4 columns: `w-25`
- 5 columns: `w-20`

These are written into the Markdown (for example `| Component {: .w-45 } |`), so users can see and change them. See IMPORT-027 in [IMPORT_RULES.md](IMPORT_RULES.md).

---

## How users can override these

- **Set a column width:** add a width class to a header cell in the Markdown editor, for example `| Point value {: .w-25 } |`. Any class from `w-5` to `w-100` (in steps of 5, plus `w-33` and `w-66`) works. A width class on a points column header turns off the points-column rule for that column.
- **Make every table in a section full width:** on the section page, check **Use full-width tables for this section**. This adds `section--tables-full-width` to the section, which makes `table--small`, `table--large` and `table--criterion` tables 100% wide. Points columns still shrink to fit inside a full-width table.
