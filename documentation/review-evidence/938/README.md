# Issue 938: heading-repair guidance

Captured locally on September 21, 2026 using Builder's Django error renderer,
templates, and static styles. These are local rendered-page previews, not a
deployed-environment smoke test or screenshots of a Word upload.

Both previews use the same example: first Heading 2 is "Step 1: Review the
opportunity", final Heading 1 is "Endnotes", with seven preceding Heading 2s.

- `before.png`: existing error details and recovery steps, without the new
  outlier metadata. This reproduces the previous visible message.
- `after.png`: the same page with the new count metadata and "Likely Word fix"
  detail. The source heading is named, the suggested Word style is explicit,
  and the advice remains conditional on these being peer main sections.

The existing HTTP 422 block, retry action, and neutral recovery steps remain.
Automated resolver and import-page tests verify detection, ambiguous fallbacks,
escaping, unchanged source content, and no saved NOFO on a blocked import.
