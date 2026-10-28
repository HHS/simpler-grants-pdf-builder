# Documentation

This is the repository's canonical documentation directory. Add new repository documentation
here—not in a top-level `docs/` directory—and use the placement rules below.
Link durable guides or topic indexes from this page; individual evidence records are reached through their issue or topic guide.

- [Admin styling](ADMIN_STYLING.md) — Keep admin assets aligned with Django and add scoped customizations
- [SECURITY.md](SECURITY.md) — Security vulnerability reporting through HHS responsible disclosure, research scope and policy contacts
- [QUALITY_REVIEW_AND_TRIAGE.md](QUALITY_REVIEW_AND_TRIAGE.md) — Design/accessibility and application-experience review, evidence gathering, triage, proposed priorities and assisted-review boundaries
- [SCALABLE_NOFO_DESIGN_SYSTEM.md](SCALABLE_NOFO_DESIGN_SYSTEM.md) — Technology-agnostic architecture considerations for shared NOFO components, branding, compatibility, reproducible output and PDF validation, with pinned Builder evidence
- [readability/](readability/README.md) — Source-native metrics, Word/PDF upload guidance, safeguards, verification and launch readiness
- [design-pilot/](design-pilot/README.md) — Local synthetic design contracts, host, candidate access and review
- [Announcement Services integration](integrations/announcement-services/README.md) — Current manual pilot sources and optional identity/lifecycle foundations
- [BUILDER_METRICS.md](BUILDER_METRICS.md) — The usage & quality metrics dashboard at `/nofos/metrics`: what it reports and who can see it
- [CHANGELOG_BANNER.md](CHANGELOG_BANNER.md) — The site-wide "Latest release" banner driven by `CHANGELOG.md`: when it shows, how long, and the admin off switch
- [CONTRIBUTION_WORKFLOW.md](CONTRIBUTION_WORKFLOW.md) — Diagram of the contribution workflow for people and AI agents (issue → branch → PR → CI → squash merge → changelog), with what to read at each step
- [DESIGN_STANDARDS.md](DESIGN_STANDARDS.md) — Selected NOFO design and accessibility standards (headings, images, visual consistency, line breaks, lists, links, tables) reproduced from the HHS Office of Grants standards, with a checklist to use before publishing
- [DECISIONS.md](DECISIONS.md) — Product, architectural, and implementation decision log
- [Agent design pilot boundary ADR](adr/2026-10-20-agent-design-pilot-boundary.md) - Accepted HTML-only local synthetic-proof direction and human acceptance boundary for #902/#1145
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
- [UI_PATTERNS.md](UI_PATTERNS.md) — Reusable interface patterns, including alert text and spacing, shared file-upload error states, loading progress modals, readability reliability alerts, and subsection save-conflict recovery
- [STYLE_GUIDE.md](STYLE_GUIDE.md) — The SimplerNOFOs Style Guide (edition of August 25, 2026) as Markdown: writing, formatting, and structure conventions for NOFO content, with known conversion gaps listed at the end
- [TABLES.md](TABLES.md) — Automatic table styling: size classes, captions, points columns, import-time width classes, and how users override them
- [UPDATING_PYTHON_DEPENDENCIES.md](UPDATING_PYTHON_DEPENDENCIES.md) — How to update Python dependencies
- [WORD_LIST_IMPORT.md](WORD_LIST_IMPORT.md) — Supported native list markers, mixed HTML trees and editing limitations
- [adr/](adr/README.md) — Architecture Decision Records (ADRs), written from [template.md](template.md)
- [review-evidence/](review-evidence/README.md) — Issue-specific investigations, experiments, screenshots and validation records

**`IMPORT_RULES.md` vs `IMPORT_ERROR_CODES.md`:** the first catalogs `IMPORT-NNN` *rules* — content the importer transforms automatically. The second catalogs the `IMPORT-NAME` *error codes* a user sees when an import is blocked outright. A rule can be the reason a code fires; they are separate registries.

## Where documentation belongs

Before creating a file, look for an existing guide to update. Classify the content
by its purpose, rather than its age or whether an issue is closed.

| Content | Destination |
| --- | --- |
| Current reusable instructions, behavior reference or operating procedure | Existing guide or established topic folder, linked from this index directly or through a topic index |
| Issue/PR-specific investigation, spike findings, experiment, screenshots or completed validation | `review-evidence/<issue-number>/`, with a README and supporting files together; see the [evidence conventions](review-evidence/README.md) |
| Substantial architectural decision, context and alternatives | `adr/`, indexed in its [README](adr/README.md) |
| Brief product or implementation decision | `DECISIONS.md`; link to an ADR for a substantial architectural choice |
| Reusable ADR template | [template.md](template.md), kept at this stable path for people and agents |

A new file directly under `documentation/` should cover a distinct, durable
subject that does not fit an existing guide or topic folder. Use a topic index
when related guides need separate purposes; link to authoritative explanations
instead of copying instructions. Create a new topic folder only when existing
folders do not fit a coherent set of guides. Never create a top-level `docs/`.

Split mixed documents: keep current guidance in its guide and put dated
experiments/results in review evidence, with links in both directions. A pilot
runbook or reusable release checklist is guidance; a completed test worksheet or
deployment observation is evidence. An unaccepted proposal can remain in a topic
folder when it defines an evolving contract; label its status and limitations.

## Keeping documentation current

- Give evolving proposals a status, related issue and source baseline or last
  review date. When implementation lands, reconcile implemented, remaining and
  superseded portions in the same PR. Issue closure alone does not prove every
  proposed capability exists.
- Recheck decision/index statuses against their linked records when they change.
  Preserve accepted decisions and their rationale; mark superseded decisions and
  link the replacement rather than silently deleting them.
- Preserve dated evidence as historical. Add a new dated result for a new run;
  correct misleading status claims without making old screenshots look current.
- Archive a superseded guide only with a named replacement and a clear historical
  label. Retain useful evidence; age or a closed issue is not a deletion rule.
- Before opening a PR, and again after review changes, check placement, reuse,
  indexes and links. For moves, update inbound links, relative links, commands and
  path-dependent scripts in the same PR. Keep commit-pinned historical citations
  pointing to the original source. Review references in archived evidence for
  their original context rather than rewriting historical results.
