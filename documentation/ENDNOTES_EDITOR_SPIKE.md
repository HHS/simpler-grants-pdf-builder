# Endnote editor spike (#1186)

Status: local synthetic investigation, not a supported Builder workflow.
Baseline: `c3fad94c1e559f016b8934b280bed8432b60feb2`, October 27, 2026.
[Issue #1186](https://github.com/HHS/simpler-grants-pdf-builder/issues/1186).

## Recommendation

**Build a smaller version, subject to a short user test.** Start from the
subsection being edited, with a guided citation form and a paragraph-preview
placement option. Keep the existing editor. Do not introduce a replacement
rich-text editor, a citation service or a database migration for this first step.

The prototype demonstrates interaction and identity handling, not editing of
existing imported HTML. The next production slice must first prove a conservative
adapter for supported existing note shapes, with exact before/after previews and
atomic conflict-protected saves. Unknown or ambiguous markup must remain
unchanged, with the existing warning and source-repair guidance available.

This recommendation does not establish how often users edit endnotes or whether
paragraph-end placement meets their needs. Those remain user questions. Do not
build a full management screen just because the prototype can simulate one.

## What already exists

- [`SubsectionEditForm`](../nofos/nofos/forms.py) uses Martor. Its
  [edit template](../nofos/nofos/templates/nofos/subsection_edit.html) loads Ace
  with Markdown mode; this is not a WYSIWYG document editor.
- [`NofoAddEndNotesSectionView`](../nofos/nofos/views.py) already creates the fixed
  Endnotes section and initial editable content. It applies permissions, status
  restrictions, duplicate checks and a parent-row lock. Reuse it, not a second
  section-creation flow.
- [`nofo_markdown.py`](../nofos/nofos/nofo_markdown.py) preserves raw note links
  and note containers so IDs survive conversion. Imported notes may have
  paragraphs, lists, tables and links; they are not all simple strings.
- [`endnotes.py`](../nofos/nofos/endnotes.py) and
  [`word_endnotes.py`](../nofos/nofos/word_endnotes.py) handle import recognition
  and repair. Saved-document checks feed **Check endnotes** without automatically
  modifying stored content. Do not turn those import transformations into a
  save-time rewrite of the entire document.
- The [Word author FAQ](endnote-import.md) documents native, repeated native,
  manual and legacy note conventions. Repeated references need distinct anchor
  IDs and return links. Visible numbers are not necessarily internal IDs.
- [Subsection conflict protection](../nofos/nofos/subsection_conflicts.py) and
  ordinary save/audit services already exist. A citation edit spanning several
  subsections needs a broader transaction boundary, not several independent
  subsection submissions.

## Two placement approaches

Both are clickable in the [synthetic prototype](spikes/endnotes-1186/index.html).
It uses Builder's local USWDS stylesheet and heading utilities. It has no server
save, import endpoint, browser storage, external assets or real document data.

### A. Pick a paragraph in a read-only preview

```text
Subsection -> Add citation -> Choose paragraph -> Preview reference at end
           -> Confirm citation and placement -> Review whole-document links
```

The user chooses a paragraph by its text, rather than selecting raw HTML. Native
select controls and buttons avoid relying on mouse selection. The trade-off is
precision: a paragraph with several claims may need a reference after a specific
sentence. In real content, mapping rendered paragraphs back to source ranges
needs a parser-backed adapter; splitting Markdown on blank lines is insufficient
for lists, tables, raw HTML and nested content.

### B. Insert at the editor cursor

```text
Edit subsection -> Position cursor -> Insert citation -> Enter/reuse citation
                -> Preview resulting reference -> Save and check links
```

This is precise and stays close to writing. However, Ace's cursor is in Markdown
or raw HTML: inserting inside a tag, link, table or existing note could corrupt
content. A production helper must validate the insertion range and refuse unsafe
positions. The prototype uses a plain-text textarea as a stand-in, not
Martor/Ace, and therefore does not prove that integration.

**Preferred first test:** paragraph preview for users avoiding markup, with
cursor insertion kept as a possible later enhancement if sentence placement is
essential. A central citation list can support edits, but should not force the
user to leave the passage to create a reference.

## What the proof of concept exercises

Run from the repository root, using only loopback:

```sh
python3 -m http.server 8976 --bind 127.0.0.1
# Open http://127.0.0.1:8976/documentation/spikes/endnotes-1186/
node --test documentation/spikes/endnotes-1186/core.test.mjs
```

Use only the built-in synthetic text. No upload or save is implemented.

1. Add a citation and place it using either approach.
2. Add another reference to the same citation, in another subsection.
3. Edit or reorder citations. Stable IDs and locations stay unchanged while
   displayed numbers update. This tests list-order numbering, not automatic
   first-appearance numbering; the production numbering policy remains to agree.
4. Delete a citation only after confirming removal of all its references.
5. Change a referenced paragraph. The reference remains recorded but is flagged;
   generated HTML is blocked until its location is explicitly reconfirmed.
6. Inspect the generated HTML shape and forward/return links. The output is
   constructed from plain text, not a round trip of an existing Builder document.

The in-memory core is independent of Django, USWDS and any editor. It separates
citation identity, reference identity, display order and text position. It does
not search for a matching phrase or silently rebase offsets after an edit. Even
an unrelated edit in the same paragraph requires placement review; that is a
deliberately conservative spike behavior, not the final authoring experience.

Citation input is plain text. Formatted/multi-paragraph citations, URLs as rich
content, selections across elements, repeated text matching, overlapping note
shapes and arbitrary existing HTML are not supported by this prototype.

## Storage and integration options

| Option | Value | Cost and risk |
| --- | --- | --- |
| HTML remains authoritative; adapter produces a revision-bound change plan | Preserves current import/render/history paths; no initial database migration | Must reliably recognize supported shapes, retain rich citation content, inventory IDs and update all affected bodies atomically |
| Separate persisted citation/reference models become authoritative | Better long-term structured API and rich editor integration | Requires migration, dual-source prevention, import/reimport policy, rendering changes, audit/compare integration and broader regression coverage |

Prefer the first option for a bounded helper. The browser's in-memory records
are an experiment, not a second persisted source of truth. A future adapter
should return proposed changed bodies plus preconditions, without importing
Django models. The application owns authorization, locks, audit and persistence.

Before committing any edit, inspect the whole document for IDs and references,
not just the open subsection. Preserve original identifiers where possible;
allocate new IDs only after a document-wide collision check. Never deduplicate
citations solely because their text matches. Repeated references are distinct
occurrences, not duplicate IDs. Leave unsupported legacy structures untouched.

## Effects that need proof before production

| Surface | Required proof |
| --- | --- |
| Import/reimport | Existing native/manual/legacy content is preserved; reimport replacement semantics remain explicit. No promise of stable child IDs across reimport. No importer changes in this spike. |
| HTML/PDF | Unique anchors, matching forward and return links, repeated references, citation ordering and multi-page notes survive existing rendering. A browser preview is not a generated-PDF test. |
| Word export | Test the actual supported export path separately. Raw HTML links do not establish native Word endnotes or editable Word note relationships. |
| History/compare | All related body changes appear through ordinary audited saves, under one intentional operation; no partial citation/reference update on conflict or failure. |
| Find & Replace | Source edits must not leave an out-of-date position map or stale manager state. Do not change find/replace behavior incidentally. |
| Warnings | Reuse existing saved-content analysis for missing notes, duplicate IDs and unrecognized content; do not mask warnings from unsupported notes. |
| Concurrent edits | Recheck every affected body under a consistent lock order. A stale endnotes body or a separately edited reference must fail the entire plan and preserve the user's draft. |
| Cleared/published records | Respect existing editing/status controls. A helper cannot bypass restrictions because it updates more than one body. |

## What can be reused outside Builder

The likely reusable foundation is a **small data contract and change-planning
core**, not Django views, models or Martor UI. The prototype demonstrates stable
identities, explicit placement validation, reordering and paired removal in
plain JavaScript. It is not yet a supported library or an SGM integration.

- Shared: citation/reference identities, numbering policy, link inventory,
  validation results, immutable input revisions and a proposed change plan.
- Host-specific: parsing the current content format, mapping selections to
  ranges, rendering reference widgets, enforcing permissions and saving changes.
- Editor-specific: Ace uses source positions; a structured rich-text editor
  should use its own document positions/transactions; form-based authoring needs
  field/block addresses. Do not make one editor's coordinates the shared contract.

No SGM source, content model or editor capability was inspected for this spike.
Its exact needs and technology choices are not assumed. The interface pattern
can transfer even when the implementation language or editor differs. A Python
host can consume a change-plan contract without depending on Django; do not
create a cross-language service solely to share this small logic.

## Size and next decision

[Local test and screen evidence](review-evidence/endnotes-editor-1186/README.md)
records what was actually checked and which integration checks remain.

Rough engineering ranges, excluding deployment and policy turnaround:

- **Small helper:** about 4-7 engineering days for a conservative existing-HTML
  adapter, paragraph placement, paired transactional saves, regression coverage
  and UI checks, if one confirmed subset of note shapes is sufficient.
- **Full management experience:** about 2-4 weeks or more for arbitrary rich
  citations, repeated references, numbering policies, source edits, concurrency
  and wider export compatibility. This is not justified by current usage evidence.
- **Persisted-model migration:** a separate estimate after inventorying real
  note shapes and host requirements; not included in either range.

Use the [short user walkthrough](spikes/endnotes-1186/USER_WALKTHROUGH.md) to test
the two flows: add a new citation, cite the
same source again, place within a dense paragraph, and repair a reference after
editing text. Ask whether paragraph-end placement suffices and how often they
make these edits after import. Keep changes in the source Word/AM document when
that remains the maintained source; don't create competing authoring workflows.

If the small helper is accepted, create a narrowly scoped implementation issue
for the supported-shape adapter and transactional helper, carrying the proof
requirements above. Do not create a full editor epic or change production data
as an automatic consequence of this spike.
