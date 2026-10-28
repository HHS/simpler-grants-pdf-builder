# Review evidence

Use this directory for issue/PR-specific investigations, spike reports, experiments,
screenshots and completed validation records. Reusable instructions, operating
procedures and current feature contracts belong in a guide or topic folder; see
[documentation placement](../README.md#where-documentation-belongs).

## File a record

- Prefer `<issue-number>/README.md`. If there is no issue, use a short descriptive
  folder name and link the PR. Existing descriptive folders remain valid; reuse
  the matching folder rather than duplicating it for a follow-up.
- Keep screenshots, sanitized samples, one-off experiment scripts and capture
  notes together. Shared regression fixtures and reusable developer tools retain
  their normal application/test/tool locations; link them from the evidence.
- The README identifies the issue/PR, capture or investigation date, inspected
  commit/branch and environment, method, findings and limitations. If an original
  date or baseline was not recorded, say so instead of inventing it. Distinguish
  source inspection, local tests and deployed behavior.
- Give each supporting file a purpose through links or descriptions. Record how
  to reproduce an experiment and any dependencies. A screenshot alone does not
  establish accessibility, production behavior or release approval.
- Link reusable conclusions to the current guide, and link evidence from the
  relevant issue/PR or topic guide. The main documentation index links this
  directory; it need not list every evidence record.
- Follow existing handling requirements. Keep private source documents, identifying
  content, credentials and sensitive logs out of public evidence.

## Preserve history

Keep dates and source revisions attached to observations. A closed issue or old
screenshot is not a reason to delete evidence. New verification gets a dated
section or separate record; do not present an old capture as a new run. Correct
stale status claims and link accepted limitations or replacements explicitly.

When a report mixes reusable guidance with historical results, split it and link
both ways. If a guide is retired, identify its replacement before archiving it;
retain useful rationale and evidence. No automatic age-based deletion applies.

## Investigation records

- [Word import drift — #974](974/README.md)
- [Shared design impact and render-input traceability — #1197](1197/README.md)
- [Draft readability — #1059](draft-readability-1059/README.md), with [characterization details](draft-readability-1059/characterization.md)
- [Readability launch observations — #1239](readability-readiness-1239/README.md)
- [Synthetic design-pilot fixtures — #1146](design-pilot-1146/README.md)

Other folders retain their issue or descriptive names and capture records.
