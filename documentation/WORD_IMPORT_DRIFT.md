# Word import drift: initial findings and measurement plan

**Issue:** [#974](https://github.com/HHS/simpler-grants-pdf-builder/issues/974)

**Status:** Initial code review complete; production aggregate run pending

**Last updated:** September 24, 2026

## Executive summary

NOFO Builder does not import the visual appearance of a Word document. It imports the document's structure as Mammoth interprets it: paragraph and character styles, list definitions, tables, links, images, and Word-native footnotes/endnotes. Builder then applies the transformations catalogued in [`IMPORT_RULES.md`](IMPORT_RULES.md), splits the result into sections and subsections, converts subsection HTML to Markdown, and generates HTML and PDF from the saved models.

The code review found eight high-value drift hypotheses. Their order below is a **code-evidence priority**, not a claim about production frequency. The audit data needed to establish frequency has not yet been run in an authenticated environment.

| Priority | Drift hypothesis | Why it ranks here | Can current data establish frequency? | Best upstream response |
|---:|---|---|---|---|
| 1 | Heading styles and hierarchy | Headings control all sectioning; Builder has dedicated repairs, three heading-related blocking errors, fixtures, and recent fixes for mixed or mistagged headings. A failure can hide or misplace whole blocks of content. | Partly. Heading text and level edits are measurable; visual-only headings that remain body text are not. | Make semantic Word heading styles unavoidable in templates; add a pre-import heading-outline check. |
| 2 | Manual or malformed footnotes/endnotes | Builder has six import rules plus saved-content warnings and a concentrated history of fixes for unconverted notes. | No. All note repairs occur inside the broad subsection `body` field. Reimports are only a proxy. | Require Word-native notes or the supported bracketed format; add a pre-import note diagnostic. |
| 3 | Metadata labels and page-one layout | Builder extracts many fields from label text and has specific errors for missing/ambiguous values; values split across cells, lines, or paragraphs need special handling. | Partly. Post-import metadata edits and blocking error codes are measurable, but the source layout that caused them is not. | Lock labels and values into a tested template pattern; validate required metadata before upload. |
| 4 | Lists and indentation | Six import rules repair Word list styles, nesting, checklist indentation, and one agency-specific continuing-number pattern. | No. List changes are stored as broad body edits. Mammoth warning counts do not identify list warnings. | Use native Word lists and template list styles; lint typed bullets/numbers and broken continuation. |
| 5 | Tables and callout boxes | Six rules infer headers, repair table structure, preserve merged cells as HTML, and reinterpret one-cell tables as callouts. | Partly. Callout classification edits are measurable; ordinary table fixes are indistinguishable from other body edits. | Provide approved table/callout components; check header rows, merged cells, and layout-only tables before import. |
| 6 | Links and bookmarks | Three import rules repair redirects, adjacent links, and bookmark targets; separate saved-content checkers find broken internal and empty-destination links. | No. Link fixes are broad body edits unless they trigger a reimport. | Validate destinations and bookmarks in Word; discourage pasted tracking URLs and empty hyperlinks. |
| 7 | Images and alternative text | Builder backfills missing `alt` attributes with an empty value and marker so the image survives, but it cannot invent an accessible description. | No. Image and alt-text changes live inside subsection body content. | Require alt text in the authoring workflow and flag missing descriptions before upload. |
| 8 | Manual page breaks and spacing | Page-break preservation/removal exists after import, while much visual spacing has no semantic representation to preserve. | No. Audit data cannot distinguish layout edits inside body content. | Define supported page-break markers and remove manual blank-line layout from templates. |

Until aggregate data is run, the honest frequency statement for each hypothesis is “current data has not established it.” The initial ranking reflects severity, the number and specificity of existing repairs, error paths, fixtures, and recent corrective commits.

## How a Word document becomes a NOFO

| Stage | What Builder uses | Important consequences |
|---|---|---|
| 1. DOCX to HTML | Mammoth, a Builder style map, and a pre-conversion document transform | Word style names and native structures matter. Direct formatting is not promoted to a heading merely because it looks like one. Unrecognized styles can produce warnings; strict mode blocks on those warnings. |
| 2. HTML cleanup | The ordered passes in `process_nofo_html()` | Builder repairs known list, table, link, note, heading, image, and metadata patterns. These transformations are evidence of recurring source variation, but not evidence of its production frequency. |
| 3. Sectioning | The resolved top heading level, then heading levels beneath it | The first consistent Heading 1/Heading 2 structure determines main sections. An ambiguous Heading 2-before-Heading 1 structure blocks import rather than silently dropping content. |
| 4. Storage | `Nofo`, `Section`, and `Subsection` records; subsection content becomes Markdown | Many distinct source defects collapse into one `Subsection.body` field, which limits later audit classification. |
| 5. Rendering | Saved models render to HTML and then the designed PDF | Some display/export transformations happen after import and are intentionally outside the import-rule catalog. |

The authoritative transformation list is [`IMPORT_RULES.md`](IMPORT_RULES.md). The authoritative blocking-error list is [`IMPORT_ERROR_CODES.md`](IMPORT_ERROR_CODES.md).

### What counts

- Real Word heading paragraph/character styles, including Builder's named style mappings.
- Native list structure and recognized list-like paragraph styles.
- Table rows, cells, headers, and merge spans.
- Hyperlinks, bookmarks, images, and Word-native note markup as Mammoth exposes them.
- Recognizable metadata labels such as opportunity number, title, OpDiv, deadline, and agency fields.

### What does not reliably count

- A paragraph made to look like a heading only through font size, bold, or spacing.
- Typed bullets or numbers that do not carry list semantics.
- Visual whitespace as an author-intended layout instruction.
- A one-cell table's visual intent: Builder must infer that it is a callout.
- The difference between a table, list, link, note, image, or ordinary prose correction after all of them have been stored in `Subsection.body`.
- The original cause of a reimport. The event records that a reimport happened, not what changed in Word.

## Evidence behind the initial ranking

### 1. Heading styles and hierarchy

Heading semantics have the widest blast radius because `resolve_section_heading_level()`, `get_sections_from_soup()`, and `get_subsections_from_sections()` use them to create the entire document tree. Current defenses include character-style conversion, Heading 7/8 support, heading cleanup, a mixed-hierarchy block, a no-sections error, and an overlong-heading error that catches paragraph text accidentally styled as a heading.

Likely author-visible drift includes missing sections, body text promoted to navigation, skipped levels, a different nesting hierarchy, and content attached to the wrong section. A template-level heading outline check is the highest-value upstream candidate.

### 2. Manual or malformed notes

Builder supports Word-native note markup and unambiguous bracketed manual notes, preserves linked note HTML through Markdown conversion, canonicalizes the heading to “Endnotes,” and reruns diagnostics on saved content. This unusually large repair and warning surface indicates both complexity and repeated failures, but the audit schema cannot count them separately.

### 3. Metadata and page-one layout

Metadata extraction is based on recognizable labels and nearby values. Builder already normalizes text, merges one known split-label/value pattern, and reports blank or ambiguous OpDiv input. Table cells, text boxes, line breaks, placeholders, and renamed labels can therefore create visible differences between Word and the populated NOFO fields.

### 4–8. Body-level structure

Lists, tables, links, images, notes, and layout cues all become Markdown or preserved HTML inside `Subsection.body`. The importer contains targeted repairs for each, but post-import audit events expose only that `body` changed. Any more specific frequency claim would require either privacy-reviewed content classification or new structured import diagnostics recorded at import time.

## What the existing data can measure

The new `import_drift_metrics` management command emits aggregate counts only. It does not output document text, changed values, filenames, email addresses, or other user identifiers.

```sh
poetry run python nofos/manage.py import_drift_metrics \
  --since 2026-09-01 \
  --until 2026-10-01
```

Use `--group cdc` (or another configured external OpDiv group) to narrow the run. `--until` is exclusive. The default start is September 1, 2026, when the current durable metrics work began.

The command reports:

- import attempts, reimport attempts, failures by error code, attempts with Mammoth warnings, and total warnings;
- custom import, reimport, and test/live print audit actions;
- heading-text, heading-level, ordering, callout, metadata, and broad subsection-body edit signals;
- distinct affected objects for audit signals;
- internal events excluded from the analysis and events with no surviving user attribution;
- malformed audit payloads that could not be classified.

Import-attempt eligibility and OpDiv are snapshots taken at import time. Audit events do not have an equivalent historical eligibility snapshot, so their group filtering uses the user's current group; events whose user was deleted cannot be attributed and are reported separately. Section/subsection create-event counts include the initial import and must not be treated as post-import fixes.

### Interpretation limits

| Signal | What it supports | What it does not support |
|---|---|---|
| `imports.reimport_attempts` | How often authors tried another source document | Why they reimported, whether content changed, or whether the cause was drift |
| `imports.error.*` | Frequency of specific blocking import outcomes | Non-blocking drift that authors fixed in-app |
| `imports.warning_count` | Volume of non-ignored Mammoth warnings | Warning type; one document may contribute many warnings |
| `edit.heading_text` / `edit.heading_level` | In-app correction of a heading's name or semantic level | Whether Word caused the correction |
| `edit.structure_order` | In-app section/subsection reordering | Whether source order was wrong or the author changed intent |
| `edit.subsection_body` | A body changed | Whether the change involved a list, table, link, note, image, layout, policy text, or ordinary wording |
| Time to first live PDF | Overall effort/latency proxy from existing durable metrics | Which drift pattern consumed the time |

## Audit logging gaps

The main gap is that the importer records totals, not structured observations. A privacy-preserving `ImportDiagnostic` (or equivalent aggregate event) could record stable codes and counts such as:

- `visual-heading-suspected`, `heading-level-skip`, `mixed-section-levels`;
- `manual-note-converted`, `manual-note-unresolved`;
- `typed-list-suspected`, `list-repaired`;
- `table-header-inferred`, `merged-cell-table-preserved`, `layout-table-suspected`;
- `link-destination-missing`, `tracking-link-unwrapped`;
- `image-alt-missing`;
- `metadata-value-missing` or `metadata-layout-unsupported`.

Each diagnostic should store only the code, count, import-attempt reference, whether the import succeeded, the import/reimport flag, timestamp, and the same durable eligibility/group snapshot already used by `ImportAttempt`. It should not store document excerpts, headings, URLs, filenames, or user identity. This would make pattern frequency measurable without reading document content from audit payloads.

Post-import intent also needs a stronger boundary. Structured UI actions such as “change heading level,” “move subsection,” “edit table,” or “repair endnotes” would be more useful than inferring intent from model field changes, provided they use stable action codes and aggregate-safe dimensions.

## Production analysis checklist

1. Confirm how far back `ImportAttempt` and usable `CRUDEvent` data exist in each environment.
2. Run `import_drift_metrics` for a bounded period and each OpDiv, saving only its aggregate output.
3. Record the unknown-user and internal-exclusion counts as coverage notes.
4. Compare reimport, heading, metadata, order, callout, and broad-body rates against eligible import attempts; do not convert broad-body counts into pattern-specific claims.
5. Compare the results with support tickets, designer feedback, and qualitative reports without copying user content into this document.
6. Replace the hypothesis ordering in the executive summary with observed counts and an explicit denominator.

## Recommended follow-up issues

1. Add privacy-preserving structured import diagnostics for the top patterns.
2. Add a Word-template/preflight heading-outline check.
3. Add preflight diagnostics for manual notes, typed lists, table headers/merged cells, empty links, and missing image alt text.
4. Add warning-type aggregation rather than storing only Mammoth's total warning count.
5. Add structured editor action events for heading level, ordering, tables, links, and endnote repair.

These follow-ups are intentionally separate from this spike; no import behavior changes are proposed here.
