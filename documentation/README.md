# Documentation

This is the repository's canonical documentation directory. Add new repository documentation
here—not in a top-level `docs/` directory—and link durable guides from this index. Architecture
decision records belong in `adr/`; PR-specific screenshots and validation notes belong in
`review-evidence/`.

- [QUALITY_REVIEW_AND_TRIAGE.md](QUALITY_REVIEW_AND_TRIAGE.md) — Design/accessibility and application-experience review, evidence gathering, triage, proposed priorities and assisted-review boundaries
- [BUILDER_METRICS.md](BUILDER_METRICS.md) — The usage & quality metrics dashboard at `/nofos/metrics`: what it reports and who can see it
- [AUTHENTICATED_PDF_READABILITY_PILOT.md](AUTHENTICATED_PDF_READABILITY_PILOT.md) - Restricted PDF/Word upload pilot, access provisioning, source-aware reporting and activation checks
- [DRAFT_PDF_READABILITY.md](DRAFT_PDF_READABILITY.md) - Draft content scope, synthetic characterization, and remaining Word-to-PDF validation
- [Word readability uploads](PDF_READABILITY_PILOT.md#word-uploads-1111) - Reused conversion and measurement paths, archive limits and scope caveats
- [Word report scope and reliability](WORD_READABILITY_RELIABILITY.md) - Why Word has no reliability rating, general scope versus detected warnings, and report/copy/print presentation
- [CHANGELOG_BANNER.md](CHANGELOG_BANNER.md) — The site-wide "Latest release" banner driven by `CHANGELOG.md`: when it shows, how long, and the admin off switch
- [CONTRIBUTION_WORKFLOW.md](CONTRIBUTION_WORKFLOW.md) — Diagram of the contribution workflow for people and AI agents (issue → branch → PR → CI → squash merge → changelog), with what to read at each step
- [DESIGN_STANDARDS.md](DESIGN_STANDARDS.md) — Selected NOFO design and accessibility standards (headings, images, visual consistency, line breaks, lists, links, tables) reproduced from the HHS Office of Grants standards, with a checklist to use before publishing
- [DECISIONS.md](DECISIONS.md) — Product, architectural, and implementation decision log
- [Agent design pilot investigation](AGENT_DESIGN_PILOT.md) - Proposed bounded rules, fidelity checks and manual baseline; not an implemented pilot
- [Agent design pilot boundary ADR](adr/2026-10-20-agent-design-pilot-boundary.md) - Accepted HTML-only local synthetic-proof direction and human acceptance boundary for #902/#1145
- [Design candidate operation rules](DESIGN_CANDIDATE_OPERATIONS.md) - In-memory presentation-operation slice; trusted-host integration and runtime isolation still required
- [Connected local design host](DESIGN_PILOT_LOCAL_HOST.md) - Synthetic human upload, candidate persistence and revision-bound HTML review; no agent transport or acceptance
- [EDITOR_TASKS.md](EDITOR_TASKS.md) — Instructions for common NOFO Builder tasks, including prerequisites and support contacts
- [GROUPS.md](GROUPS.md) — How user groups and permissions work
- [DOCUMENT_HISTORY.md](DOCUMENT_HISTORY.md) - Indexed history pagination, deleted-item retention, backfill and rollout verification
- [IMPORT_ERROR_CODES.md](IMPORT_ERROR_CODES.md) — What each blocking import error code (`IMPORT-NO-SECTIONS`, `IMPORT-OPDIV-BLANK`, …) means and what to tell someone who hits one
- [IMPORT_RULES.md](IMPORT_RULES.md) — Every automatic content rule applied when a NOFO is imported (footnote/endnote handling, list/table repair, metadata suggestion, etc.)
- [TAGLINE_IMPORT.md](TAGLINE_IMPORT.md) — Legacy and Basic information tagline sources, blank precedence, editing, and re-import behavior
- [WORD_METADATA_IMPORT.md](WORD_METADATA_IMPORT.md) — Legacy labels and trailing Metadata blocks, precedence, defaults and saved-record behavior
- [INTRODUCTORY_PAGE_IMPORT.md](INTRODUCTORY_PAGE_IMPORT.md) — Supported Word introductory headings, destinations, maintained registration families and legacy preservation
- [EDITABLE_INTRODUCTION.md](EDITABLE_INTRODUCTION.md) — Imported introductory ownership, compatibility, editing, output policy and resolving template guidance before the introduction
- [endnote-import.md](endnote-import.md) — Windows Word author FAQ, native note/cross-reference import fallbacks, and manually bracketed reference conventions
- [DOCUMENT_PROCESSING.md](DOCUMENT_PROCESSING.md) — Shared content-processing boundary, application responsibilities and remaining portability limits
- [NOFO_BUILDER_FAQ.md](NOFO_BUILDER_FAQ.md) — Answers to common questions about designing a NOFO in NOFO Builder: importing, Markdown, tables, page layout, endnotes, appendices, metadata, and status; links to the editor tasks for step-by-step instructions
- [READABILITY_METRICS.md](READABILITY_METRICS.md) — The `hhs-nofo-metrics` integration and source contract; when readability snapshots are saved (by a person, or automatically on import, re-import and Download PDF); saved readability history, deletion, archiving, and duplication behavior
- [UI_PATTERNS.md](UI_PATTERNS.md) — Reusable interface patterns, including alert text and spacing, shared file-upload error states, loading progress modals, readability reliability alerts, and subsection save-conflict recovery
- [STYLE_GUIDE.md](STYLE_GUIDE.md) — The SimplerNOFOs Style Guide (edition of August 25, 2026) as Markdown: writing, formatting, and structure conventions for NOFO content, with known conversion gaps listed at the end
- [TABLES.md](TABLES.md) — Automatic table styling: size classes, captions, points columns, import-time width classes, and how users override them
- [UPDATING_PYTHON_DEPENDENCIES.md](UPDATING_PYTHON_DEPENDENCIES.md) — How to update Python dependencies
- [WORD_IMPORT_DRIFT.md](WORD_IMPORT_DRIFT.md) — Code-review findings on likely differences between Word author intent and imported NOFO structure
- [WORD_LIST_IMPORT.md](WORD_LIST_IMPORT.md) — Supported native list markers, mixed HTML trees and editing limitations
- [adr/](adr/README.md) — Architecture Decision Records (ADRs), written from [template.md](template.md)
- [review-evidence/](review-evidence/) — Before/after screenshots and capture notes supporting individual PRs, filed by issue number

**`IMPORT_RULES.md` vs `IMPORT_ERROR_CODES.md`:** the first catalogs `IMPORT-NNN` *rules* — content the importer transforms automatically. The second catalogs the `IMPORT-NAME` *error codes* a user sees when an import is blocked outright. A rule can be the reason a code fires; they are separate registries.

## Announcement Services integration

- [Current manual S3 pilot workflow and AS responses (#950)](https://github.com/HHS/simpler-grants-pdf-builder/issues/950) — Source of truth for proposed Word delivery, manual designer retrieval/import, confirmed capabilities and unresolved operating decisions. Capability confirmation does not establish implementation or approval.
- [Future automated PDF delivery (#951)](https://github.com/HHS/simpler-grants-pdf-builder/issues/951) — Separate future capability; the delivery approach and contract remain to be decided under [#957](https://github.com/HHS/simpler-grants-pdf-builder/issues/957). PDF retrieval and return remain manual in the current pilot.

The earlier `ANNOUNCEMENT_SERVICES_DATA_FLOW.md` and `ANNOUNCEMENT_SERVICES_WORKFLOW.md` files are absent from `main`. Use #950 for the current pilot rather than those older diagrams.
