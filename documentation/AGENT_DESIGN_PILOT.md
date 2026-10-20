# Agent design pilot: initial rule and baseline contract

Proposed analysis for #902/#1146, based on main at `5fe16ad6`. This is not an
implemented skill, completed manual baseline or release approval. Environment
choices are in the [proposed ADR](adr/2026-10-20-agent-design-pilot-boundary.md).

## Keep the first slice small

Use the existing import pipeline, design system and PDF service. Automate only
presentation controls initially. Do not reproduce deterministic import repairs
in a prompt, invent missing content or silently repair unsupported structures.
Do not create another comprehensive standards registry: the sources below retain
their current authority and limitations.

| Stable pilot rule | Classification | Allowed action / exit evidence | Existing source |
| --- | --- | --- | --- |
| DESIGN-001: establish imported baseline | Escalate unexplained differences | Account for source-to-import differences with applicable import rules; unexpected loss blocks acceptance | [IMPORT_RULES](IMPORT_RULES.md), [DOCUMENT_PROCESSING](DOCUMENT_PROCESSING.md) |
| DESIGN-002: theme and cover | Presentation when supplied preference is unambiguous; otherwise confirm suggestion | Use declared theme/cover choices; never invent branding or a cover image. Inspect rendered cover before accepting a change | [TASK-THEME](EDITOR_TASKS.md#task-theme) |
| DESIGN-003: pagination | Presentation with rendered evidence | Set subsection breaks only in the first slice. Suggest in-body markers to a human; do not edit body text automatically. Record affected pages and regenerate | [FAQ page breaks](NOFO_BUILDER_FAQ.md#when-should-i-add-a-manual-page-break) |
| DESIGN-004: table width | Presentation | Existing section-level full-width control; review every table affected, not just the target table | [TASK-TABLE-FULL-WIDTH](EDITOR_TASKS.md#task-table-full-width), [TABLES](TABLES.md) |
| DESIGN-005: custom CSS | Confirm suggestion in first slice | No automatic CSS writes. Require demonstrated defect, native-control attempts and complete rerender | [UI patterns](UI_PATTERNS.md), existing theme controls |
| DESIGN-006: semantic structure | Escalate ambiguity | Flag heading jumps, ambiguous table headers, list damage and missing alt text. Do not rewrite headings, invent alt text or delete content autonomously | [DESIGN_STANDARDS](DESIGN_STANDARDS.md), [EDITOR_TASKS](EDITOR_TASKS.md) |
| DESIGN-007: substance and policy | Forbidden autonomous change | Preserve all wording, dates, amounts, eligibility, links and policy even when policy tags are missing/disabled | #902; [IMPORT_RULES](IMPORT_RULES.md) only explains import-stage changes |
| DESIGN-008: final review | Human decision | Exact current PDF inspected; unresolved blocking findings prevent acceptance; acceptance is design completion, not publication/compliance | [Before you publish](DESIGN_STANDARDS.md#before-you-publish) |

There are no allowlisted autonomous content fixes in the first slice. The
classification remains available for later, individually specified fixes with
tests; it is not permission for general copyediting. Human corrections need
attribution and must invalidate affected previews/checks.

## Resolve guidance differences without silent edits

- The UI supports H7, while the supplied standards limit structural headings to
  H1-H6. Flag the affected structure for human resolution; do not invent a heading
  or flatten it automatically.
- Cover guidance and agency-specific form restrictions can differ. Current legal
  choices constrain the adapter, but an available choice does not establish the
  author's intended branding.
- Caption guidance has exemptions. Apply those before raising a missing-caption
  finding. Table size heuristics do not establish semantic table complexity.
- Import-time markers are not render-time detection. Respect intentional marker
  removal and width overrides; a missing marker is not proof of import loss.
- Optional line-break advice is not permission to rewrite prose. Page layout must
  be judged from the actual rendered revision, not the editor screen alone.

## Readiness and fidelity contract

Every finding needs rule ID, target section/field, severity, evidence reference,
proposed next action and whether a human decision is required. Use separate
values for `pass`, `fail`, `not_assessed` and `unsupported`; unavailable checks
must not become passes. Nonblocking findings may be explicitly acknowledged;
blocking findings require resolution and rerun, not a generic acknowledgment.

Map existing diagnostics into these findings rather than build parallel scanners:
`find_broken_links`, `find_same_or_higher_heading_levels_consecutive`,
`find_incorrectly_nested_heading_levels` and `find_endnote_issues` in
`nofos/nofo.py`, plus `PDF_METADATA_FIELDS` and `is_missing_pdf_metadata_value`
in `nofos/pdf_metadata.py`. These checks are already used by the edit view.
Retain their scope limits; they do not establish complete accessibility or source
fidelity. External-link status checking performs network requests and is not
part of the default isolated proof.

Ready for review means the candidate and exact revision-bound previews are
available with an honest report of missing evidence and open questions. A missing
PDF yields a partial HTML review only, not ready for final design acceptance.
Acceptance additionally requires current authorization, resolved blockers,
recorded final PDF inspection and no changes since that inspection. Freeze the
Builder revision, relevant feature flags, render options, templates/styles and
asset bytes as well as candidate fields; changes invalidate affected evidence.
Apply the ADR's destination-mapping and rendered-output verification after
transfer rather than assuming local and production output will match.

Two comparisons are required:

1. Source-to-import: preserve original bytes and conversion output. Identify
   transformations allowed by the import rules, including source guidance removal,
   metadata extraction and note/list changes. Do not apply a broad text-normalization
   waiver that could hide a missing number, condition or paragraph.
2. Imported baseline-to-designed candidate: compare ordered section/body content,
   policy text, table cell values, list order/start semantics, links, notes and
   assets. Include separately stored title, opportunity number, deadline,
   agency/subagency fields, tagline, PDF metadata and introductory-page
   ownership/family/variant. Import can consume their source text, so matching
   body text alone cannot detect their loss. Freeze the complete render-affecting
   record baseline; permit only declared presentation changes or attributable
   human corrections. Store an
   explicit expected-before target and validate revision before each edit.

Digests bind exact artifacts; they do not explain differences or prove content
fidelity. PDF text extraction is supplementary and may be unreliable for tables
and columns. Deterministic comparisons plus full rendered-page inspection remain
necessary. The comparison/report contract is specified here, not implemented.

## Synthetic fixture and baseline plan

| Fixture | Expected result |
| --- | --- |
| Clear theme preference, image-less image cover, simple scoring table | Propose legal cover/layout settings; preserve every word/value and intentional width marker; inspect PDF |
| Header hierarchy before first main heading | Existing import failure, actionable recovery; no guessed restructuring |
| Conflicting dates or unknown agency preference | Blocking human question; no invented date/theme |
| Canonical policy paragraph with missing tags | Preserve exact wording; changing a protected sentence fails fidelity |
| Altered amount, missing table cell or changed ordered-list start | Deterministic failure, even if the model describes the output as good |
| Lost deadline/tagline metadata or changed introductory-page mode | Fidelity failure even when section/body text is unchanged |
| Damaged archive, oversized expanded ZIP or unsupported structure | Bounded rejection or escalation, not silent source repair |
| Embedded instruction to fetch a URL, read another candidate or accept output | No corresponding authority; host rejects tool/path escape |
| Edit after PDF inspection | Earlier readiness and acceptance evidence becomes stale |
| Changed theme stylesheet, feature flag or remapped destination asset after review | Revalidate the destination; material output differences require new PDF inspection |

Run the same fixtures manually and with the agent against the same pinned source
and Builder revision. Record human active time, elapsed time, every intervention,
operation/field, import defect versus design task versus permanent judgment,
render calls, model use/cost when available and final quality/rework. Existing
single-document trials are historical evidence, not a representative new baseline.

First baseline scope: a routine presentation case, a table-heavy case and a case
requiring human judgment. Invented Word fixtures can support regression tests;
they do not establish production accuracy. Source preparation, complete Word/PDF
rendering and visual inspection are still work to do. No timing, cost savings or
design quality measurement has been claimed from this documentation investigation.

## Next implementation contracts

#1147 implements candidate staging and declared tools; #1148 implements findings,
targeted corrections and refreshed previews; #1149 and #1150 own trusted acceptance
and discard; #1151 measures the complete loop. Reuse prior immutable-snapshot,
expected-before and human-decision patterns after checking them against current
Builder. Do not bring editorial-coaching prompts or an entire stale fork into
the design pilot.
