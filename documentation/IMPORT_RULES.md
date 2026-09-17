# NOFO Import Rules Reference

This document catalogs every automatic content rule the NOFO Builder applies when a `.docx` or HTML file is imported (new import, reimport/overwrite, and Composer import all share this pipeline). Each rule is an implicit "if this pattern is found, then the content is changed like this" — heading/list/table repair, footnote-to-endnote conversion, link cleanup, metadata guessing, and so on.

**⚠️ Maintenance requirement:** If your PR adds, removes, or changes behavior in any of the source files below, update the matching rule entry in this document in the same PR (add a new `IMPORT-NNN` entry, edit an existing one, or mark one `status: removed` — never delete an entry outright, so the numbering and history stay stable). See [DEPLOYMENT.md § Updating Import Rules](../DEPLOYMENT.md#updating-import-rules) for the enforced contribution policy.

**Not to be confused with import error *codes*.** The `IMPORT-NNN` IDs here are numbered rule identifiers for content transformations. The `IMPORT-NAME` strings a user sees when an import is blocked (`IMPORT-NO-SECTIONS`, `IMPORT-OPDIV-BLANK`, and so on) are a separate namespace, catalogued in [`IMPORT_ERROR_CODES.md`](IMPORT_ERROR_CODES.md). A rule here can be the *reason* an error code fires; they are not the same registry.

**Source files covered by this document:**
- `nofos/nofos/nofo.py` — `process_nofo_html()` and the ~20 cleanup passes it runs, plus sectioning/subsectioning and metadata-suggestion logic
- `nofos/nofos/utils.py` — `style_map_manager`, the Mammoth DOCX→HTML style-name map
- `nofos/nofos/import_transforms.py` — pre-Mammoth DOCX document transform (`transform_word_document`)
- `nofos/nofos/nofo_markdown.py` — `NofoMarkdownConverter`, the HTML→Markdown conversion rules
- `nofos/nofos/policy_language.py` — policy-language status detection (feature-flagged)
- `nofos/nofos/pdf_metadata.py` — PDF metadata placeholder normalization
- `nofos/nofos/endnotes.py` — bracketed manual endnote detection and linking
- `nofos/composer/models.py` — `extract_variables` (Composer-only)

**Format note for automated/AI readers:** Each rule has a stable ID (`IMPORT-NNN`) that never changes or gets reused, even if a rule is later removed (mark it `status: removed` instead). Every rule uses the same five fields in the same order — **Type**, **Trigger**, **Action**, **Source**, **Status** — so a rule's meaning can be extracted reliably without parsing prose. The index table below is a complete, compact summary of every rule; the sections after it give full detail. If you are an AI agent editing import-pipeline code, treat this file as the authoritative rule registry: check it before changing behavior, and update it as part of the same change.

---

## Rule Types

Every rule is tagged with a **Type**, classifying *why* it exists rather than *what it touches* (the section headings below group by subject matter instead — tables, links, footnotes, etc.). This is a judgment call in a few spots — flagged inline where it applies — so treat it as a useful filter, not a strict taxonomy:

- **repair** — fixing malformed or incorrectly-encoded source markup so it matches what it should have been (Word/Google-export artifacts, broken links, empty tags, split paragraphs).
- **conversion** — deliberately choosing or changing a representation for the app's own needs, where the source wasn't "wrong," just different (Word style names → semantic HTML, footnote/endnote formatting decisions, callout-box detection).
- **removal** — content is deleted outright, not reattached or reused elsewhere.
- **extraction** — a value or block of content is pulled out of the document (or derived from surrounding context) and used to populate a separate field, or reattached to a different part of the document structure.
- **validation** — the rule doesn't transform content; it blocks import with an error, or picks a structural default when the source is ambiguous.
- **tagging** — non-visual classification metadata is attached to already-imported content; the content itself is untouched.

A few rules sit right on the boundary between two types — most notably **IMPORT-022** (table-header promotion), which could be read as repair *or* conversion depending on whether you consider Word's flat first row "wrong" in the first place. Those are called out with a parenthetical in their own entry rather than forced into one bucket without comment.

---

## Index

| ID | Type | Category | Summary | Source |
|----|------|----------|---------|--------|
| IMPORT-001 | conversion | DOCX Conversion | Checkbox-row indent detection → "Application Checklist Child" style | `import_transforms.py` |
| IMPORT-002 | conversion | DOCX Conversion | Word heading *character* styles → real `h2`-`h6` | `utils.py` |
| IMPORT-003 | conversion | DOCX Conversion | Word `heading 7`/`heading 8` paragraph styles → synthetic H7/H8 divs | `utils.py` |
| IMPORT-004 | repair | DOCX Conversion | Mis-styled Word bullet/numbered paragraph styles → real nested `ul`/`ol` | `utils.py` |
| IMPORT-005 | conversion | DOCX Conversion | Word emphasis-signaling styles → `<strong>` variants | `utils.py` |
| IMPORT-006 | conversion | DOCX Conversion | `Placeholder Text` style → visible flagged span | `utils.py` |
| IMPORT-007 | repair | DOCX Conversion | ~30 cosmetic/noise Word styles → suppressed or flattened to plain tags | `utils.py` |
| IMPORT-008 | repair | Text Normalization | Non-breaking space / checkbox glyph variants → unified characters | `nofo.py` |
| IMPORT-009 | repair | Text Normalization | Hardcoded broken grants.gov/cdc.gov URLs → working URLs | `nofo.py` |
| IMPORT-010 | repair | Text Normalization | Metadata field values → NFKC-normalized, control chars stripped, whitespace collapsed | `nofo.py` |
| IMPORT-011 | validation | Heading Structure | `h2` before first `h1` → import blocked with actionable error | `nofo.py` |
| IMPORT-012 | validation | Heading Structure | No `h1` present → section level defaults to `h2` | `nofo.py` |
| IMPORT-013 | repair | Heading Structure | Heading cleanup: unwrap spans, collapse whitespace, drop empty headings | `nofo.py` |
| IMPORT-014 | conversion | Heading Structure | Auto-generate heading IDs; rewrite internal links to match | `nofo.py` |
| IMPORT-015 | conversion | Footnotes/Endnotes | Missing "Endnotes" heading + trailing footnote list detected → heading synthesized | `nofo.py` |
| IMPORT-016 | conversion | Footnotes/Endnotes | Footnote/endnote `<ol>` → preserved as raw HTML through Markdown conversion | `nofo_markdown.py` |
| IMPORT-017 | conversion | Footnotes/Endnotes | Footnote/endnote `<a>` → wrapped in `<sup>`, preserved as raw HTML | `nofo_markdown.py` |
| IMPORT-049 | conversion | Footnotes/Endnotes | "Footnotes"/"Footnote:"/etc. heading text → canonical "Endnotes" | `nofo.py`, `endnotes.py` |
| IMPORT-050 | conversion | Footnotes/Endnotes | Unambiguous `[N]` reference/citation pairs → forward/return links | `nofo.py`, `endnotes.py` |
| IMPORT-051 | conversion | Footnotes/Endnotes | Manually-linked endnote lists/links → preserved as raw HTML | `nofo_markdown.py` |
| IMPORT-018 | repair | Lists | Adjacent same-class lists merged; differing-class lists nested | `nofo.py` |
| IMPORT-019 | repair | Lists | Redundant `<li>`/`<ul>` wrapper levels unwrapped | `nofo.py` |
| IMPORT-020 | conversion | Lists | `<ol start="N≠1">` or list-in-table-cell → kept as raw HTML in Markdown | `nofo_markdown.py` |
| IMPORT-021 | conversion | Lists | Custom fixed-indent bullet/number rendering in Markdown | `nofo_markdown.py` |
| IMPORT-052 | repair | Lists | Canonical ACF required-alignment bullet groups → continuing numbered lists | `nofo.py` |
| IMPORT-022 | repair *(see note)* | Tables | First table row's `<td>`s → `<th>`s (assumed header row) | `nofo.py` |
| IMPORT-023 | repair | Tables | Multi-row `<thead>` with no `<tbody>` → rows after the first moved to a new `<tbody>` | `nofo.py` |
| IMPORT-024 | conversion | Tables | Single-cell, single-row table → extracted as a callout-box subsection | `nofo.py` |
| IMPORT-025 | conversion | Tables | Callout box titled "Key facts"/"Key dates" → forced to `h4`, canonical casing | `nofo.py` |
| IMPORT-026 | repair | Tables | `<span>` inside table cells → unwrapped | `nofo.py` |
| IMPORT-027 | conversion | Tables | Any cell with `colspan`/`rowspan` ≠ 1 → whole table kept as raw HTML; header width classes auto-assigned | `nofo_markdown.py` |
| IMPORT-028 | repair | Links | Google Docs tracking-redirect URLs → unwrapped to real destination | `nofo.py` |
| IMPORT-029 | repair | Links | Consecutive same-href links merged; whitespace before punctuation trimmed | `nofo.py` |
| IMPORT-030 | repair | Links | Bookmark/heading/table-heading anchor IDs transferred to surviving parent elements | `nofo.py` |
| IMPORT-031 | repair | Cleanup | Empty inline wrapper tags (`em`/`span`/`strong`/`sup`) unwrapped | `nofo.py` |
| IMPORT-032 | removal | Cleanup | Empty block/list-item tags decomposed (removed) | `nofo.py` |
| IMPORT-033 | repair | Images | Missing `alt` attribute → backfilled `alt=""` + marker, preserved as raw HTML | `nofo.py`, `nofo_markdown.py` |
| IMPORT-034 | repair | Images | Image `alt` text double-newlines → single newline | `nofo.py` |
| IMPORT-035 | conversion | Images | Inline image `src` → rewritten to static NOFO-numbered path | `nofo.py` *(not currently wired into the pipeline)* |
| IMPORT-036 | conversion | Emphasis | CSS classes with `font-weight: 700` (&lt;18pt) → wrapped in `<strong>` | `nofo.py` |
| IMPORT-037 | conversion | Emphasis | Literal text "de minimis" → wrapped in `<em>` | `nofo.py` |
| IMPORT-038 | removal | Content Removal | "Before you begin" heading + section → removed (duplicates a Builder-generated page) | `nofo.py` |
| IMPORT-039 | extraction | Content Removal | "Instructions for NOFO writers" tables → extracted, reattached to matching subsection | `nofo.py` |
| IMPORT-040 | repair | Field Merging | Split label/value paragraphs under "Funding details" → merged into one paragraph | `nofo.py` |
| IMPORT-041 | extraction | Metadata Suggestion | `Label:` text patterns → auto-suggested NOFO metadata fields; an underscore-only `Tagline:` value → empty | `nofo.py` |
| IMPORT-042 | extraction | Metadata Suggestion | OpDiv / opportunity-number prefix → suggested cover theme | `nofo.py` |
| IMPORT-043 | extraction | Metadata Suggestion | Theme prefix → suggested cover style (text-only vs. medium) | `nofo.py` |
| IMPORT-044 | extraction | Metadata Suggestion | New import's HRSA theme / user's group → suggested "before you begin" page variant; duplicates copy the saved variant | `nofo.py` |
| IMPORT-045 | extraction | Metadata Suggestion | Opportunity number / title substring → suggested cover image | `nofo.py` |
| IMPORT-046 | tagging | Non-Visual Tagging | Subsection body vs. canonical policy-language templates → compliance status tag | `policy_language.py` |
| IMPORT-047 | extraction | Non-Visual Tagging | `{Prompt}` / `{List: label}` syntax → Composer content-guide variables | `composer/models.py` |
| IMPORT-048 | repair | Non-Visual Tagging | PDF metadata field is a whole-field `{placeholder}` → normalized to empty | `pdf_metadata.py` |

---

## DOCX Conversion & Word Style Mapping

Mammoth converts the uploaded `.docx` to HTML using a style-name map (`style_map_manager` in `utils.py`) plus a pre-conversion document transform (`import_transforms.py`) that runs before Mammoth ever sees the document.

### IMPORT-001 — Checkbox-row indent detection
- **Type:** conversion *(arguably repair — see note below)*
- **Trigger:** Within a Word table, a row's first cell's paragraph starts with a checkbox glyph (`¨`, DEL, `☐`, `◻`) and its indent is deeper than a previously-seen checkbox row's indent (visually nested, but not structurally, since Word doesn't encode this as real nesting).
- **Action:** Relabel that paragraph with the `Application Checklist Child` style, which the style map (below) then maps to `<p class="application-list--left-indent">`.
- **Source:** `import_transforms.py::transform_word_document/_transform_table` (`_first_column_checkbox_paragraph`)
- **Status:** active
- **Note:** classified as conversion because it synthesizes new semantic structure (a style Word never had) from a visual cue, rather than fixing markup that was supposed to already encode that structure — but it's a defensible repair reading too, since the intent was clearly a nested list.

### IMPORT-002 — Heading character styles → real headings
- **Type:** conversion
- **Trigger:** A Word *run* (character) style named `Heading 2 Char` through `Heading 6 Char` is applied to text (Word sometimes marks a heading via character style rather than paragraph style).
- **Action:** Emit a real `<h2>`-`<h6>` tag instead of a plain `<span>`.
- **Source:** `utils.py::style_map_manager` (`r[style-name='Heading N Char']` rules)
- **Status:** active

### IMPORT-003 — Synthetic H7/H8 headings
- **Type:** conversion
- **Trigger:** Paragraph style `heading 7` or `heading 8` (the app has no native support past `h6`).
- **Action:** `heading 7` → `<div role="heading" aria-level="7">` (recognized elsewhere as `is_h7()`); `heading 8` → `<div class="heading-8">`.
- **Source:** `utils.py::style_map_manager`; consumed by `nofo.py::is_h7`
- **Status:** active

### IMPORT-004 — Mis-styled bullet/numbered paragraphs → real lists
- **Type:** repair
- **Trigger:** Paragraph styles `Bullet`, `Bullet Level 1`, `List Bullet1`, `Bullet 2`, `Bullet 2 Calibri`, `Bullet 3`, or Mammoth's built-in `p:unordered-list(1-6)` / `p:ordered-list(1-6)` detectors — all cases where Word's list is a flat paragraph style, not real nesting.
- **Action:** Emit properly nested `<ul>`/`<ol>` &gt; `<li>` structures at the correct depth.
- **Source:** `utils.py::style_map_manager`
- **Status:** active

### IMPORT-005 — Emphasis-signaling styles → `<strong>`
- **Type:** conversion
- **Trigger:** Styles `Style Bold`, `Subtle Emphasis`, `Emphasis A`, `Subhead2`, `Intense Reference`.
- **Action:** Wrapped in `<strong>` with a style-specific class (e.g. `strong.style-bold`, `strong.subhead`) rather than left as plain text/span.
- **Source:** `utils.py::style_map_manager`
- **Status:** active

### IMPORT-006 — Placeholder text flagged visibly
- **Type:** conversion
- **Trigger:** Style `Placeholder Text` (Word content-control placeholder).
- **Action:** Emit `<span class="placeholder-text">` — kept visible intentionally, as a signal that placeholder text was left in a real document rather than replaced.
- **Source:** `utils.py::style_map_manager`
- **Status:** active

### IMPORT-007 — Cosmetic/noise style suppression
- **Type:** repair
- **Trigger:** ~30 Word run/paragraph styles that are purely cosmetic Word artifacts (e.g. `normaltextrun`, `eop`, `findhit`, `cf01`/`cf11`/`cf21`, `Default`, `contentcontrolboundarysink`, `Body Text Char`, `Table`, `Table Paragraph`, `Normal (Web)`, `No Spacing`, and several `Bulletlevel2`/`customXmlDelRange`/`FootnoteReference`/`ListParagraph`/`v:`/`w:`/`office-word:` prefixes ignored from strict-mode warnings entirely).
- **Action:** Flattened to plain `<span>`/`<p>` (no semantic change) or fully suppressed from the `WORD_IMPORT_STRICT_MODE` warning list — each has a code comment recording why it's safe to ignore.
- **Source:** `utils.py::style_map_manager` (styles_to_ignore list + the bulk of `add_style` calls)
- **Status:** active

---

## Text & Character Normalization

### IMPORT-008 — Non-breaking space / checkbox glyph unification
- **Type:** repair
- **Trigger:** Raw file content contains `\xa0` or `&nbsp;` (both non-breaking spaces), or the checkbox glyph variants U+2610 (☐), U+00A8 (¨), or U+007F (DEL).
- **Action:** Non-breaking spaces → regular space. Checkbox variants → unified to U+25FB (◻).
- **Source:** `nofo.py::replace_chars`
- **Status:** active

### IMPORT-009 — Hardcoded broken-link fix
- **Type:** repair
- **Trigger:** Raw content contains one of 3 hardcoded known-broken URLs (`grants.gov/web/grants/search-grants.html`, `grants.gov/web/grants/forms/sf-424-family.html`, `cdc.gov/grants/dictionary/index.html`) — noted as broken because they don't redirect but return HTTP 200.
- **Action:** String-replaced with the correct current URL.
- **Source:** `nofo.py::replace_links`
- **Status:** active

### IMPORT-010 — Metadata value sanitization
- **Type:** repair
- **Trigger:** Any metadata field value extracted during import (opportunity number, deadline, title, etc.).
- **Action:** Unicode NFKC-normalize, strip all Unicode "control/format/invisible" category characters (including zero-width spaces), collapse whitespace, and trim.
- **Source:** `nofo.py::sanitize_imported_text`
- **Status:** active

---

## Heading Structure

### IMPORT-011 — Ambiguous heading hierarchy blocks import
- **Type:** validation
- **Trigger:** Document contains an `h2` before its first `h1`.
- **Action:** Import is blocked with a `ValidationError` naming the offending headings, rather than silently picking a heading level and discarding earlier content. The user sees error code `IMPORT-AMBIGUOUS-HEADINGS`.
- **Source:** `nofo.py::resolve_section_heading_level`
- **Status:** active

### IMPORT-012 — Default section level
- **Type:** validation
- **Trigger:** Document has no `h1` at all.
- **Action:** Section-level heading defaults to `h2`.
- **Source:** `nofo.py::resolve_section_heading_level`
- **Status:** active

### IMPORT-013 — Heading tag cleanup
- **Type:** repair *(the empty-heading case is a removal)*
- **Trigger:** Any heading (`h1`-`h6`) containing `<span>` wrappers, extra internal whitespace, or leading/trailing whitespace; or a heading that becomes empty after this cleanup.
- **Action:** Unwrap spans, collapse whitespace to single spaces, trim; decompose (remove) the heading entirely if empty.
- **Source:** `nofo.py::clean_heading_tags`
- **Status:** active

### IMPORT-014 — Heading ID generation & link rewriting
- **Type:** conversion
- **Trigger:** Every section/subsection heading, on document build.
- **Action:** Auto-generate a slug `id` for each heading; rewrite any internal `href="#old-id"` links in the document to point at the new ids.
- **Source:** `nofo.py::add_headings_to_document`
- **Status:** active

---

## Footnotes & Endnotes

The example that prompted this document: detecting a footnote/endnote list and formatting it consistently. Covers both native Word/Google Docs notes (IMPORT-015 through IMPORT-017) and manually authored bracketed references like `[1]` (IMPORT-049 through IMPORT-051), a separate mechanism documented for authors in [`docs/endnote-import.md`](../docs/endnote-import.md).

### IMPORT-015 — Synthesize missing "Endnotes" heading
- **Type:** conversion
- **Trigger:** No heading already reads exactly "Endnotes", **and** either (a) the document ends in an `<hr>` with no `style` attribute (Google Docs export pattern), or (b) a final `<ol>` whose first `<li>` has an `id` starting with `footnote` or `endnote` (docx export pattern).
- **Action:** (a) Repurpose that `<hr>` as an `h1`/`h2` with text "Endnotes"; (b) insert a new `h1`/`h2` "Endnotes" heading immediately before that `<ol>`.
- **Source:** `nofo.py::add_endnotes_header_if_exists`
- **Status:** active
- **Note:** covers a *missing* heading. See IMPORT-049 for the case where a note-section heading exists but reads "Footnotes"/"Footnote:"/etc. instead of "Endnotes".

### IMPORT-016 — Footnote/endnote list preserved as raw HTML
- **Type:** conversion
- **Trigger:** During HTML→Markdown conversion, an `<ol>` whose first `<li>` has an `id` starting with `footnote`/`endnote`.
- **Action:** Keep the entire list as raw (prettified) HTML rather than converting to Markdown list syntax, and add `tabindex="-1"` to every `<li>`, so ids and structure survive.
- **Source:** `nofo_markdown.py::NofoMarkdownConverter.convert_ol`
- **Status:** active
- **Note:** covers native Word/Google notes specifically. See IMPORT-051 for the equivalent rule covering manually bracket-linked notes.

### IMPORT-017 — Footnote/endnote reference preserved as raw HTML
- **Type:** conversion
- **Trigger:** During HTML→Markdown conversion, an `<a>` whose `id` starts with `footnote`/`endnote`.
- **Action:** Wrap it in `<sup>` and keep it as raw HTML instead of Markdown link syntax, so the reference displays as a superscript and its id survives.
- **Source:** `nofo_markdown.py::NofoMarkdownConverter.convert_a`
- **Status:** active
- **Note:** covers native Word/Google notes specifically. See IMPORT-051 for the equivalent rule covering manually bracket-linked notes.

### IMPORT-049 — Footnote/Endnote heading text normalization
- **Type:** conversion
- **Trigger:** A heading (`h1`-`h7`, including the synthetic H7 `div`) whose text, ignoring case and an optional trailing colon, reads "endnote", "endnotes", "footnote", or "footnotes".
- **Action:** Rewrite the heading's text to the canonical "Endnotes", so downstream detection (IMPORT-050, IMPORT-051) and the reader both see one consistent heading regardless of which variant the author used. If more than one such heading exists in the document, none are renamed and no bracketed-endnote linking (IMPORT-050) happens at all — the ambiguity is left for the author to resolve rather than guessed at.
- **Source:** `nofo.py::rename_footnotes_heading_to_endnotes` (via `endnotes.py::is_endnotes_heading`)
- **Status:** active

### IMPORT-050 — Bracketed manual endnote reference/citation linking
- **Type:** conversion
- **Trigger:** The document has exactly one recognized Endnotes heading (after IMPORT-049), and contains a `[N]` marker in body text (a "reference") that unambiguously pairs with a `[N]` marker starting a paragraph under that heading (a "citation"): each number used exactly once as a reference and once as a citation, neither already linked, and not colliding with a native Word/Google note number already in the document.
- **Action:** Wrap the in-body `[N]` marker in a forward link to its citation (rendered as a superscript), give the citation paragraph a matching target id, and append a `↑` return link back to the reference. Numbering gaps or out-of-sequence citations are only advisory and don't block linking an otherwise-valid pair. Anything ambiguous — a missing, duplicate, empty, or conflicting marker, or more than one candidate Endnotes heading — is left completely unlinked; NOFO Builder never silently renumbers or guesses at a bracketed reference. Conversion runs on both fresh import and reimport; it never modifies the original source Word file.
- **Source:** `nofo.py::process_nofo_html` (via `endnotes.py::convert_bracketed_endnotes`, `_inspect`, `_scan`)
- **Status:** active
- **Note:** If note evidence exists only as non-structural text such as a bold "Endnotes" paragraph, the heading warning is associated with that text so the editor can direct the user to the content that needs a structural heading.

### IMPORT-051 — Manual endnote lists/links preserved as raw HTML in Markdown
- **Type:** conversion
- **Trigger:** During HTML→Markdown conversion: (a) an `<ol>`/`<ul>` contains any element with an `id` starting with `endnote-manual-` (a citation linked by IMPORT-050); (b) an `<a>` whose `id` starts with `footnote`/`endnote` is already wrapped in a `<sup>` (one of IMPORT-050's own generated links).
- **Action:** (a) the whole list is kept as raw HTML instead of Markdown list syntax; (b) the existing `<sup>` wrapper is reused instead of wrapping it again.
- **Source:** `nofo_markdown.py::NofoMarkdownConverter.convert_ol/convert_ul/convert_a`
- **Status:** active
- **Note:** extends IMPORT-016/IMPORT-017 (native notes) to also cover manually bracket-linked ones.

---

## List Structure Repair

### IMPORT-018 — Adjacent list merging/nesting
- **Type:** repair
- **Trigger:** Two adjacent `<ul>`/`<ol>` siblings. If they share the same Mammoth-generated list class, they're siblings that should be one list; if classes differ, the second is meant to be nested under the first.
- **Action:** Same class → merge into a single list. Different class → nest the second list inside the last `<li>` of the first (recursing into any already-nested list there).
- **Source:** `nofo.py::join_nested_lists`
- **Status:** active

### IMPORT-019 — Redundant list-wrapper unwrapping
- **Type:** repair
- **Trigger:** An `<li>` whose only content is a nested `<ul>` (no direct text); or a `<ul>` directly nested inside another `<ul>` with no intervening `<li>`.
- **Action:** Unwrap the redundant wrapper level.
- **Source:** `nofo.py::unwrap_nested_lists`
- **Status:** active

### IMPORT-020 — Numbered-list-start / table-cell lists kept as raw HTML
- **Type:** conversion
- **Trigger:** During Markdown conversion, an `<ol start="N">` where N ≠ 1, or any list nested inside a `<td>`/`<th>`.
- **Action:** Rendered as raw HTML instead of Markdown, since Markdown can't express a custom start number and table-cell lists are ambiguous in Markdown.
- **Source:** `nofo_markdown.py::NofoMarkdownConverter.convert_ol/convert_ul`
- **Status:** active

### IMPORT-021 — Custom list rendering in Markdown
- **Type:** conversion
- **Trigger:** Every list item, during Markdown conversion.
- **Action:** Bullet/number and indentation computed with custom fixed-4-space-indent logic rather than markdownify's default (needed for CommonMark-compliant nesting).
- **Source:** `nofo_markdown.py::NofoMarkdownConverter.convert_li`
- **Status:** active

### IMPORT-052 — ACF required-alignment bullet groups → continuing numbered lists
- **Type:** repair
- **Trigger:** Imported metadata identifies an ACF NOFO by opportunity number or OpDiv; an "Agency priorities" subsection is inside Step 1; its opening bold paragraph is "Required alignment with ACF Vision, Mission, Values, Priorities, and Guiding Principles"; its first prose paragraph begins with the canonical required-alignment language; and three unordered lists contain the six expected bold principle labels in order (groups of 1, 2, and 3 items).
- **Action:** Retag only those three `<ul>` containers as ordered lists starting at 1, 2, and 4. The first list becomes normal Markdown numbering; the latter two retain `<ol start="2">` / `<ol start="4">` through IMPORT-020. All source wording, links, emphasis, and intervening paragraphs remain unchanged. If any agency, hierarchy, title, opening-text, list-count, or label check fails, leave the subsection untouched.
- **Source:** `nofo.py::repair_acf_required_alignment_lists` (using `is_acf_nofo_metadata`)
- **Status:** active

---

## Table Handling

### IMPORT-022 — First-row header promotion
- **Type:** repair *(the ambiguous case flagged in the Rule Types section above — could also be read as conversion)*
- **Trigger:** A table's first `<tr>` uses `<td>` cells (no header row marked).
- **Action:** Convert that row's cells to `<th>`, treating it as the header row.
- **Source:** `nofo.py::convert_table_first_row_to_header_row`
- **Status:** active

### IMPORT-023 — Multi-row `<thead>` repair
- **Type:** repair
- **Trigger:** A table has a `<thead>` containing more than one row, no `<tbody>`, and no cell has `rowspan`/`colspan` ≠ 1.
- **Action:** Create a `<tbody>`; move every row after the first into it, converting their `<th>` cells back to `<td>`.
- **Source:** `nofo.py::convert_table_with_all_ths_to_a_regular_table`
- **Status:** active

### IMPORT-024 — Callout box detection
- **Type:** conversion
- **Trigger:** A table has exactly 1 row and 1 column, and that single cell is either all `<th>` or all `<td>` (not mixed).
- **Action:** Recognized as a "callout box" — the cell becomes a `<div>`-based subsection instead of a normal table.
- **Source:** `nofo.py::is_callout_box_table`, consumed in `get_subsections_from_sections`
- **Status:** active

### IMPORT-025 — Key callout title normalization
- **Type:** conversion
- **Trigger:** A callout box's (IMPORT-024) heading text, cleaned and cased, reads exactly "key facts" or "key dates".
- **Action:** Retitled to canonical capitalization ("Key facts"/"Key dates") and forced to `h4`.
- **Source:** `nofo.py::get_subsections_from_sections` (`key_callout_titles`)
- **Status:** active

### IMPORT-026 — Table cell span unwrapping
- **Type:** repair
- **Trigger:** A `<span>` inside any `<td>`/`<th>`.
- **Action:** Unwrapped, keeping the text content.
- **Source:** `nofo.py::clean_table_cells`
- **Status:** active

### IMPORT-027 — Spanned-cell tables kept as raw HTML + auto width classes
- **Type:** conversion
- **Trigger:** During Markdown conversion, any cell in a table has `colspan`/`rowspan` ≠ "1" (Markdown tables can't express spans).
- **Action:** Whole table kept as raw prettified HTML; header cells get an auto-assigned width CSS class based on column count (3→`w-33`, 4→`w-25`, 5→`w-20`) and specific header text overrides ("Component"→`w-45`, "How to upload/submit..."→`w-40`, "page limit"→`w-15`).
- **Source:** `nofo_markdown.py::NofoMarkdownConverter.convert_table/convert_th`, `get_width_class`
- **Status:** active

---

## Link Handling

### IMPORT-028 — Google tracking-link unwrapping
- **Type:** repair
- **Trigger:** An `<a href>` starts with `https://www.google.com/url?` (Google Docs export's link-tracking redirect wrapper).
- **Action:** Rewritten to the real destination URL, extracted from the `q=` query parameter.
- **Source:** `nofo.py::remove_google_tracking_info_from_links`
- **Status:** active

### IMPORT-029 — Consecutive link merging
- **Type:** repair
- **Trigger:** Consecutive `<a>` tags share the same `href` (Word often splits one logical link across multiple runs); separately, whitespace appears between a link and trailing punctuation (`. , ; ! ?`).
- **Action:** Merge the links into one (preserving a single space if whitespace separated them originally); trim the whitespace before trailing punctuation.
- **Source:** `nofo.py::combine_consecutive_links`
- **Status:** active

### IMPORT-030 — Bookmark/heading/table-heading anchor preservation
- **Type:** repair
- **Trigger:** An empty `<a id="...">` (no text) that is a Word bookmark target, immediately precedes a heading, or immediately precedes a table (as a "table heading" anchor) — these get removed later by empty-tag cleanup (IMPORT-032) unless rescued first.
- **Action:** Transfer the `id` to the adjacent surviving element (next paragraph, parent heading, or paragraph before the table) before the empty anchor is decomposed, and rewrite any existing links pointing at the old id. Broken/unreferenced bookmarks are prefixed (`#__id`, `nb_bookmark_id`) so they're identifiable rather than silently dead.
- **Source:** `nofo.py::preserve_bookmark_links`, `preserve_bookmark_targets`, `preserve_heading_links`, `preserve_table_heading_links`
- **Status:** active

---

## Whitespace & Empty-Element Cleanup

### IMPORT-031 — Empty inline-wrapper unwrapping
- **Type:** repair
- **Trigger:** An `<em>`, `<span>`, `<strong>`, or `<sup>` with no text content and no image inside.
- **Action:** Unwrapped (tag removed, no content to lose).
- **Source:** `nofo.py::unwrap_empty_elements`
- **Status:** active

### IMPORT-032 — Empty block/list-item removal
- **Type:** removal
- **Trigger:** A direct child of `<body>`, or any `<li>`/`<p>`, with no text and no `<img>` descendant (and not `<br>`/`<hr>`) — commonly junk left over from PDF-sourced or heavily-edited Word documents.
- **Action:** Decomposed (removed entirely).
- **Source:** `nofo.py::decompose_empty_tags`
- **Status:** active

---

## Images

### IMPORT-033 — Missing alt-text backfill
- **Type:** repair
- **Trigger:** An `<img>` has no `alt` attribute at all (as opposed to an intentionally empty `alt=""`).
- **Action:** Backfill `alt=""` plus an internal marker attribute (`data-nofo-missing-alt-text`), so missing alt text is visible/greppable rather than silently absent; the Markdown converter then keeps that image as raw HTML instead of `![]()` syntax, since Markdown can't distinguish "backfilled empty" from "originally empty".
- **Source:** `nofo.py::add_missing_alt_text_to_imgs`; consumed in `nofo_markdown.py::NofoMarkdownConverter.convert_img`
- **Status:** active

### IMPORT-034 — Alt-text whitespace normalization
- **Type:** repair
- **Trigger:** An image's `alt` attribute contains a double newline (`\n\n`).
- **Action:** Collapsed to a single newline.
- **Source:** `nofo.py::normalize_whitespace_img_alt_text`
- **Status:** active

### IMPORT-035 — Inline image path rewriting
- **Type:** conversion
- **Trigger:** The document has a real (non-default) NOFO opportunity number, and an inline `<img>`'s `src` isn't a base64 data URI.
- **Action:** Rewrite `src` to `/static/img/inline/<nofo-number>/<filename>`.
- **Source:** `nofo.py::replace_src_for_inline_images`
- **Status:** **implemented but not called anywhere in the live import pipeline.** It's fully implemented and unit-tested (`test_nofo.py`), but nothing in `views.py`'s import flow calls it. Confirm with the team whether this is an intentionally paused feature or a regression before relying on it — treat as inactive until confirmed.

---

## Emphasis Detection

### IMPORT-036 — CSS-based bold detection
- **Type:** conversion
- **Trigger:** The document's embedded `<style>` block defines a CSS class with `font-weight: 700` and a font-size under 18pt (18pt+ is assumed to be a heading rather than bold body text) — this is how Google Docs exports encode bold, since it doesn't use semantic tags.
- **Action:** Every element using that class is wrapped in `<strong>`, except elements inside a table's first row (already header cells).
- **Source:** `nofo.py::add_strongs_to_soup`, `_get_classnames_for_font_weight_bold`
- **Status:** active

### IMPORT-037 — "De minimis" auto-italicization
- **Type:** conversion
- **Trigger:** The literal text "de minimis" (case-insensitive) appears anywhere and isn't already wrapped in `<em>`.
- **Action:** Wrapped in `<em>` — a hardcoded, domain-specific house-style rule.
- **Source:** `nofo.py::add_em_to_de_minimis`
- **Status:** active

---

## Content Extraction & Removal

### IMPORT-038 — "Before you begin" duplicate-section removal
- **Type:** removal
- **Trigger:** A heading (`h1`-`h6`) whose normalized text reads exactly "before you begin" (GrantSolutions Announcement Module exports include this).
- **Action:** Remove that heading and everything after it, up to whichever comes first: the next heading of the same or higher level, or a line that looks like a metadata label (e.g. `Opportunity Number:`) — this content is always redundant with the "Before you begin" page NOFO Builder generates itself from its own `before_you_begin` field.
- **Source:** `nofo.py::decompose_before_you_begin_section`
- **Status:** active

### IMPORT-039 — Writer-instructions table extraction
- **Type:** extraction
- **Trigger:** A single-cell table whose text starts with "Instructions for NOFO writers", "Instructions for new NOFO team", or matches the pattern `*-specific instructions`.
- **Action:** Extracted (removed) from the document body, then matched by title to the corresponding subsection and reattached there as that subsection's "instructions" field (Composer import only).
- **Source:** `nofo.py::decompose_instructions_tables`, `add_instructions_to_subsections`
- **Status:** active

---

## Field Merging

### IMPORT-040 — Funding-details label/value merging
- **Type:** repair
- **Trigger:** Under an `h3`/`h4` heading whose text is exactly "Funding details", a `<p>` ending in `:` is immediately followed by another `<p>` whose text doesn't itself end in `:`.
- **Action:** Merge the two paragraphs into one (rejoins a label like "Award ceiling:" that Word had split from its value onto a separate paragraph).
- **Source:** `nofo.py::merge_funding_details_label_value_paragraphs`
- **Status:** active

---

## Metadata Field Auto-Suggestion

These are heuristic *suggestions* pre-filled into NOFO metadata fields (opportunity number, agency, cover theme, etc.) for a human to confirm/edit — not silent content rewrites, but they follow the same "if pattern found, then value set" structure. All classified `extraction`: a value is derived from the document (or, for IMPORT-044, from the importing user's context) and used to prefill a field.

### IMPORT-041 — Label:value field scanning
- **Type:** extraction
- **Trigger:** A paragraph starts with a literal label string (`"Opportunity Number:"`, `"Application Deadline:"`, `"Opportunity Name:"`, `"Opdiv:"`, `"Agency:"`, `"Subagency:"`, `"Subagency2:"`, `"Tagline:"`, `"Metadata Author:"`, `"Metadata Subject:"`, `"Metadata Keywords:"`). For `Opdiv:` specifically, if the value isn't on the same line, the next paragraph is checked too — but only accepted if it doesn't itself look like another metadata label.
- **Action:** The suggested field is pre-filled with the text following the label (sanitized per IMPORT-010).

  **Tagline exception — underscore-only placeholders.** `Tagline:` alone gets one extra check: if the extracted value is made up entirely of underscores and whitespace (`"Tagline: _________"`, the ruled blank an HHS Word template leaves for a writer to fill in), the tagline is suggested as empty instead. In isolation this step is a **repair**, the same shape as IMPORT-048 for `{placeholder}` PDF metadata values; it's documented here rather than as its own rule because it only ever runs as part of this rule's tagline extraction. IMPORT-010's sanitization keeps underscores — they are ordinary printable characters — so without this the row of underscores would be saved as the tagline and rendered on the NOFO cover. A value that merely *contains* underscores is untouched (`"Apply by ____ to be considered"` imports as written), and no other metadata field treats underscores as blank, so an underscore-only `Agency:` still imports literally. The check lives next to `suggest_nofo_tagline()` rather than in the shared scanner precisely to keep it that narrow.
- **Source:** `nofo.py::_suggest_by_startswith_string` and the `suggest_nofo_*` family; the tagline exception in `nofo.py::suggest_nofo_tagline`, `_is_underscore_placeholder`
- **Status:** active

### IMPORT-042 — Cover theme suggestion
- **Type:** extraction
- **Trigger:** OpDiv text or the opportunity-number prefix matches a known agency (`nih`, `hrsa`, `cdc-`, `acf-`, `acl-`, `cms-`, `ihs-`, `rfa-`). ACF is recognized from an `ACF` opportunity-number segment, the full "Administration for Children and Families" OpDiv name, or a standalone `ACF` OpDiv acronym.
- **Action:** Suggest the matching portrait theme.
- **Source:** `nofo.py::suggest_nofo_theme`, `is_acf_nofo_metadata`
- **Status:** active

### IMPORT-043 — Cover style suggestion
- **Type:** extraction
- **Trigger:** Theme prefix is `acf-`/`acl-`/`hrsa-`/`nih-`.
- **Action:** On a new import, suggest a text-only cover for those themes, or the "medium" cover for other themes. Re-imports preserve the stored cover style, including when the existing opportunity number is blank or a placeholder. HRSA theme forms offer only text-only plus the record's current legacy cover, if any; loading the form does not update the record.
- **Source:** `nofo.py::suggest_nofo_cover`
- **Status:** active

### IMPORT-044 — "Before you begin" page variant suggestion
- **Type:** extraction
- **Trigger:** Brand-new import whose suggested theme is HRSA (derived from opportunity number / OpDiv), or importing user's group is `"nih"`.
- **Action:** Select the persisted `"hrsa"` variant for an HRSA theme, otherwise `"era"` for an NIH user, otherwise `"full"`. The HRSA variant includes the registration/deadline content and an “Application and funding requirements” heading and paragraph before the final internal-links callout. Its four subsection headings are matching semantic `h3` elements below the page's `h2`. Re-imports retain their saved variant, even with a blank/placeholder opportunity number. Adding the choice does not backfill any existing records.

  **Duplication does not re-suggest anything.** `duplicate_nofo()` clones the record, so a copy carries the saved variant forward whatever it is — a copy of a record imported before the HRSA variant existed still says `"full"`, and gets no HRSA paragraph. That applies equally to the archive snapshot a re-import takes (`is_successor=True`), which must keep the variant the record actually had. Someone can change a copy's variant by hand at `/nofos/<id>/edit/before-you-begin`.

  *Open question:* whether duplicating an HRSA NOFO should move the copy from `"full"` to `"hrsa"`, on the grounds that a duplicate is usually where the next NOFO starts. Deliberately not decided here; the behaviour above is what ships, and `tests_nofos/test_hrsa_byb.py::BeforeYouBeginOnDuplicateTests` pins it.
- **Source:** `nofo.py::suggest_nofo_before_you_begin`, `suggest_all_nofo_fields`; explicit new/re-import context from `views.py`; duplication in `views.py::duplicate_nofo`
- **Status:** active

### IMPORT-045 — Cover image suggestion
- **Type:** extraction
- **Trigger:** A static cover image file exists matching the opportunity number, or the title contains "pepfar".
- **Action:** Suggest that image, or the hardcoded CDC PEPFAR cover for the "pepfar" case. HRSA re-imports preserve the stored cover image, including an empty value.
- **Source:** `nofo.py::suggest_nofo_cover_image`
- **Status:** active

---

## Non-Visual Classification & Tagging

These rules don't change the visible content, but they run automatically at import time and tag the imported data — worth documenting for the same reason as the content rules above.

### IMPORT-046 — Policy-language compliance tagging
- **Type:** tagging
- **Trigger:** A subsection's markdown body (normalized for smart quotes/dashes/whitespace) is compared against a canonical library of Department Governance policy-language templates (which may contain `{placeholder}` spans).
- **Action:** Tag the subsection `policy_language_status` as `intact`, `may_be_altered`, `matches_prior_version`, or `none`, and record which canonical `policy_language_slot` it matched. Used later for export-time compliance flagging; never mutates the imported content itself.
- **Source:** `policy_language.py::detect_policy_language_status`, consumed in `nofo.py::_build_document`
- **Status:** active, gated behind `config.HHS_NOFO_POLICY_EXPORT_ENABLED`

### IMPORT-047 — Composer variable extraction
- **Type:** extraction
- **Trigger:** A subsection body (Composer import only) contains `{Prompt text}` or `{List: label}` placeholder syntax.
- **Action:** Parsed into named "variables" (slugified into keys) that content-guide writers fill in later; the subsection's `edit_mode` is set to `"variables"`, `"full"`, or `"locked"` depending on whether variables or the word "insert" are present.
- **Source:** `composer/models.py::extract_variables`, consumed in `nofo.py::_build_document`
- **Status:** active (Composer-only)

### IMPORT-048 — PDF metadata placeholder normalization
- **Type:** repair
- **Trigger:** A suggested PDF metadata value (author/subject/keywords) is a whole-field curly-brace placeholder, e.g. `"{insert author}"`.
- **Action:** Normalized to an empty string rather than importing the literal placeholder text.

  Scope note: this covers the curly-brace placeholder form on the three PDF metadata fields only. The other placeholder form the templates produce — a ruled blank that converts to a run of underscores — is handled separately, and only for the tagline, under IMPORT-041. No single rule normalizes placeholders across every metadata field; each one is opt-in by design, so an unexpected value is left visible for a human to correct rather than silently dropped.
- **Source:** `pdf_metadata.py::normalize_pdf_metadata_value`, consumed by `nofo.py::suggest_nofo_author/subject/keywords`
- **Status:** active

---

## Related, But Out of Scope

The rules above cover **import time** only. A separate, parallel layer of "if pattern, then transform" rules runs at **render/view/export time** instead — every time a NOFO is displayed, edited, or exported to PDF/DOCX, via `nofos/nofos/templatetags/*.py` (e.g. `add_classes_to_tables.py`, `convert_paragraphs_to_hrs.py` turning literal `page-break`/`column-break` paragraph text into styled `<hr>` markers, `replace_unicode_with_icon.py`, `truncate_anchor_links_for_docx.py` truncating bookmark ids to Word's 40-character limit on export, and `add_footnote_ids.py` reformatting footnote reference links for display). If this document's scope is ever widened to "everything automatic," those belong in a sibling document (e.g. `RENDER_EXPORT_RULES.md`), kept clearly separate from import-time behavior since they run on every page view rather than once at upload.

The two view-time link-checking functions are worth calling out here because they are frequently mistaken for import rules, and because what counts as "broken" changed in [#908](https://github.com/HHS/simpler-grants-pdf-builder/issues/908):

- **`nofo.py::find_broken_links`** reports links that were *supposed* to resolve inside the NOFO but don't — `#`-fragments with no matching id, root-relative `/…` paths, `bookmark://…`, and `file://…`. These power the "some internal links are broken" warning panel on the edit page.
- **`nofo.py::find_external_links`** reports every link pointing *outside* the NOFO, and powers the "Check external links" page. **Google Docs URLs (`https://docs.google.com/…`) belong here, not in the broken-internal-link panel** — they are ordinary external destinations and are status-checked like any other. Listing them in both places double-counted them and implied a NOFO-internal problem that didn't exist.
  - The `about:blank` placeholder (what Word and Google Docs write when a hyperlink in the source document has no destination) is reported here too, flagged `invalid_destination` so it renders as "no destination / not checked" and is **never requested over HTTP**. It is a defect in the source `.docx`, not a broken anchor into the NOFO. Anchors with `about:blank` and no visible link text are skipped entirely, since there is nothing for a designer to find and fix.

Both of those are *classification* changes only: nothing in the `.docx` import pipeline rewrites or removes these links, so neither gets an `IMPORT-NNN` entry. If you are looking for why a Google Docs link stopped appearing in the broken-links count, this is it — it moved categories, it was not silently dropped.

One more view-time rule is worth calling out because it shares detection logic with IMPORT-050/IMPORT-051: **`nofo.py::find_endnote_issues`** reruns the same bracketed-endnote analysis (`endnotes.py::analyze_endnotes`) fresh against a NOFO's *saved* content every time its detail page is viewed, surfacing warnings (missing/duplicate/empty/malformed/conflicting markers, non-sequential numbering, missing return links) without changing stored content or ids. It's what powers the `unconverted_footnotes` warnings shown in the editor — not an import transformation itself, but the reason a NOFO's endnote warnings can change after import without anyone re-importing it. Warning links use the affected rendered subsection when it has an editor anchor; otherwise they fall back to the containing section so every fragment has a target on the edit page.
