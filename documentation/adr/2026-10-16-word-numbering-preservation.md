# Preserve source numbering before Word conversion

- **Status:** Proposed in #1121 implementation
- **Last Modified:** 2026-10-16
- **Deciders:** Pending pull-request review

## Context

Mammoth 1.12's document transform sees an ordered/unordered flag and a level.
Its numbering reader does not retain letter/Roman formats, numbering-instance
identity, starts or overrides. Its style reader also discards information needed
to resolve some inherited numbering. Restoring those details after conversion
by inspecting text or HTML depth would require guessing.

Builder already uses conversion-only Word preprocessing and Mammoth for inline
content. It also preserves raw semantic HTML where Markdown cannot represent a
table or list. Its sanitizer accepts list `type` and `start`; existing CSS uses
depth-based fallback only when no explicit type is supplied.

## Decision

Use a small, per-upload numbering adapter around the existing Mammoth call.
Read supported OOXML numbering and style definitions from the in-memory
conversion copy. Map known list paragraphs to unique temporary paragraph styles
and retain their resolved semantics outside the content. Reconstruct semantic
lists after Mammoth has converted runs, emphasis, links and bookmarks.

Do not fork or patch Mammoth, replace the document converter, persist the
sidecar, add a service or infer source markers from text. Temporary styles avoid
aligning an index of Word paragraphs with HTML paragraphs that Mammoth may drop
or reorganize. Preserve unsupported cases through the existing converter with
a review advisory instead of inventing custom marker rendering.

## Consequences

Complete list trees remain HTML when Markdown would lose source markers or
starts; simple standalone lists retain their readable Markdown form and fixed
four-space nesting. Source-reconstructed trees bypass legacy class/wrapper
repair. The existing exact ACF repair runs afterward and deliberately overrides
its matched groups to continuing decimal numbering.

This is an internal framework-independent adapter, not a new public package or
general Word layout engine. Native formats, inheritance, restart rules, table
and note boundaries, and shared consumers require regression coverage. Manual
marker recovery remains separate. Reimport explicitly reapplies conversion;
opening an existing NOFO does not rewrite stored content.

Rule details and compatibility limits are recorded under IMPORT-066 in
[IMPORT_RULES.md](../IMPORT_RULES.md).
