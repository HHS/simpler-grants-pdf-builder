# Checkbox table inline links (#1100)

## Change and reproduction

The existing SVG replacement put the text before an inline link, the anchor,
and the following text into separate flex items. The previous text-only span
also stripped the space immediately before the link. Correct authored content
could therefore appear as columns or as joined words.

The render-time filter now groups each single-checkbox inline label into one
content span beside the decorative SVG. Paragraph and flattened Markdown cells
use the same grouping. Inline emphasis and links remain within that span;
existing block/list containers are not moved into invalid inline structures.
Scoped CSS lets links wrap inline and prevents the icon from shrinking.
No source content, stored records, import rules, or migrations change.

## Browser evidence

The synthetic local NOFO is `4d1f1f2f-d7ce-4556-9350-f34b90d07446`, with
the reported Budget form sentence and a matching Budget form anchor.
The same record also includes plain text, multiple links, emphasis, and a
paragraph/list cell. No private source document was used.

Chrome captures compare server-rendered full Builder HTML using the original
filter/CSS at main `0b45b1a59a01e33b59b9d70a280eba46688394d5` with the changed
filter/CSS. The narrow viewport is 700 × 900. The Budget form link was clicked
and reached its matching in-document destination. Cell borders and the
neighboring Required? column remained intact.

| Layout | Before | After |
| --- | --- | --- |
| Normal | [Before](before-normal.jpg) | [After](after-normal.jpg) |
| Narrow | [Before](before-narrow.jpg) | [After](after-narrow.jpg) |

## PDF verification

Before and after PDFs were generated through Builder's existing PDF service
using the public DocRaptor test key, public dev assets, embedded repository
theme-base CSS, and synthetic content only. Both are four-page, watermarked
Prince 15.1 test PDFs, not a production deployment check. All four rendered
pages were inspected. Page 4 contains the checklist; links and sentences remain
continuous after the fix, with no lost borders or clipped labels. The synthetic
cover uses the existing placeholder image and has no application deadline.
The six checklist links have PDF destinations pointing to the Budget form
heading on page 4, verified from the PDF annotations.

Embedded fonts include Source Sans Pro regular/bold/semibold/italic,
Helvetica LT Condensed Bold, and Open Sans Bold; this was checked with
`pdffonts`, not inferred from CSS. The test PDF page-4 captures are below.

| Before | After |
| --- | --- |
| [Checklist PDF](before-pdf-checklist.png) | [Checklist PDF](after-pdf-checklist.png) |

## Automated verification and export scope

- 288 template-tag and import tests pass, covering the reported Markdown,
  mid/start/end/multiple links, whitespace, emphasis, long text, both checkbox
  glyphs, paragraph/multi-block/nested-list cells, rerendering, and arrows.
- The decorative empty alt text and existing PDF Artifact CSS remain unchanged.
- Word export uses its separate Markdown rendering pipeline, not this SVG
  filter or theme-base flex CSS. This change does not alter its source labels or
  hyperlinks. Actual GrabzIt-generated Word bytes were not tested because
  dedicated non-production credentials are unavailable; production credentials
  were not used.

Full-suite results and independent review are recorded in the PR handoff.
