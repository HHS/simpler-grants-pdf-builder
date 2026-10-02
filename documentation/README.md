# Documentation

This is the repository's canonical documentation directory. Add new repository documentation
here—not in a top-level `docs/` directory—and link durable guides from this index. Architecture
decision records belong in `adr/`; PR-specific screenshots and validation notes belong in
`review-evidence/`.

- [BUILDER_METRICS.md](BUILDER_METRICS.md) — The usage & quality metrics dashboard at `/nofos/metrics`: what it reports and who can see it
- [DECISIONS.md](DECISIONS.md) — Product, architectural, and implementation decision log
- [GROUPS.md](GROUPS.md) — How user groups and permissions work
- [IMPORT_ERROR_CODES.md](IMPORT_ERROR_CODES.md) — What each blocking import error code (`IMPORT-NO-SECTIONS`, `IMPORT-OPDIV-BLANK`, …) means and what to tell someone who hits one
- [IMPORT_RULES.md](IMPORT_RULES.md) — Every automatic content rule applied when a NOFO is imported (footnote/endnote handling, list/table repair, metadata suggestion, etc.)
- [endnote-import.md](endnote-import.md) — How Word imports preserve native notes and link manually authored bracketed references
- [READABILITY_METRICS.md](READABILITY_METRICS.md) — The `hhs-nofo-metrics` integration and source contract; saved readability history, deletion, archiving, and duplication behavior
- [TABLES.md](TABLES.md) — Automatic table styling: size classes, captions, points columns, import-time width classes, and how users override them
- [UPDATING_PYTHON_DEPENDENCIES.md](UPDATING_PYTHON_DEPENDENCIES.md) — How to update Python dependencies
- [WORD_IMPORT_DRIFT.md](WORD_IMPORT_DRIFT.md) — Code-review findings on likely differences between Word author intent and imported NOFO structure
- [adr/](adr/README.md) — Architecture Decision Records (ADRs), written from [template.md](template.md)
- [review-evidence/](review-evidence/) — Before/after screenshots and capture notes supporting individual PRs, filed by issue number

**`IMPORT_RULES.md` vs `IMPORT_ERROR_CODES.md`:** the first catalogs `IMPORT-NNN` *rules* — content the importer transforms automatically. The second catalogs the `IMPORT-NAME` *error codes* a user sees when an import is blocked outright. A rule can be the reason a code fires; they are separate registries.
