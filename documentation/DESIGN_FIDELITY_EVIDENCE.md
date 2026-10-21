# Bounded local fidelity evidence

This is a partial [#1146](https://github.com/HHS/simpler-grants-pdf-builder/issues/1146)
implementation, used by the [candidate review report](DESIGN_CANDIDATE_REVIEW.md).
It adds deterministic, read-only evidence rather than another importer or model
assurance check. Normal Builder import/render behavior is unchanged.

## Boundaries being compared

The host already compares original source bytes with their stored SHA-256 and
the full imported-record snapshot with the current record, excluding only
declared presentation fields. That catches out-of-workflow record changes,
including metadata and introductory-page settings. It does not establish that
the import preserved everything in Word.

The new inspection compares the **retained conversion HTML** with the **current
filtered native HTML**. This is neither a direct Word-to-HTML comparison nor an
independent replay of the importer. It does not validate converter extraction,
account for every import transformation or establish complete source fidelity.

| Evidence | Exact observed comparison |
| --- | --- |
| Converted tables | Ordered row/cell text, cell tag (`th`/`td`), row/column spans, scope, headers and cell IDs; this is not full header-association validation |
| Converted ordered lists | Ordered item text/value, list start/type and reversed attribute |
| Converted links | Exact authored `href` values, occurrence count and sequence |
| Converted images | Exact `src` values, occurrence count and sequence |
| Direct local HTML resources | Resolve direct `/static/` stylesheet/image references with existing static finders; hash bounded file bytes without fetching URLs |

Generated tables/navigation may add output elements. The comparison looks for
the entire converted sequence in order, allowing extras between matches, and
checks duplicate occurrence counts. A pass means that exact converted sequence
was observed in the output, not that its semantic origin was independently
mapped. Repeated matching content elsewhere could satisfy this observation.
This is why these passes cannot clear the overall fidelity blockers.
Text/attribute values are not whitespace-normalized, lowercased or fuzzily matched.
Table captions, complete heading/prose coverage, unordered lists, paragraph
boundaries, link text, image alt text, CSS list markers and visual layout are not
verified by these inventories.

## How to interpret the report

- Exact observed matches are scoped passes, not document approval.
- Missing/reordered exact matches are blocking reconciliation findings. An
  internal link may have a documented ID remapping, a metadata table may have
  been consumed or a safety filter may remove a URL. A mismatch is **not by
  itself proof of a defect**. Do not edit the source or waive a difference just
  to make a counter pass.
- No converted elements means **not assessed**, not proof that Word had none.
  That absence is informational; the overall source verification blocker remains.
- Nested tables, inline CSS-driven list markers or inspection budgets are explicit blocking/not
  assessed results, not empty successful comparisons.
- Direct static-resource checks cover only directly referenced file bytes.
  CSS imports/URLs, fonts, external assets, intended image meaning, complete link
  mapping and final PDF rendering are not established. No network access is added.

Input conversion/render bytes and the local resource manifest bind finding
evidence. Two different inputs with the same summary counts do not share an
evidence identity. The existing human warning form must still match both current
candidate revision and evidence revision; an acknowledgment cannot clear these
blocking results or finalize a design.

## Bounds and remaining work

Inspection is limited to 4 MiB per HTML input, 1,000 combined inventory items per
input, 5 MiB per direct local file and 16 MiB total direct local file bytes.
Nested tables, linked file/parent paths,
traversal paths and missing/unreadable local resources are not silently accepted.
These are conservative inspection bounds, not a complete runtime resource policy
or an OS sandbox. Other application work, including native rendering, has its own
existing limits.

Overall source-to-import reconciliation and complete asset/link verification
remain blocking and not assessed. Next work needs a maintained transformation
ledger with explicit field/ID/URL mappings and coverage for source Word content
that is consumed, relocated, removed or unsupported. Re-running the same importer
is not independent evidence; a broad normalization waiver could hide a missing
condition or amount. Human source comparison remains necessary until those checks
are implemented and validated. Real-data operation, acceptance/transfer/discard,
model runtime and local PDF generation are not introduced by this slice.
