# HRSA Before you begin: before and after

These screenshots show page 3 of a representative portrait HRSA PDF, rendered
locally with Prince 16.2 (PDF/UA-1, print media) and rasterized with Poppler at
1500 pixels high on September 16, 2026. They use the actual Django PDF template,
repository styles/assets, and the public fonts referenced by the application.
The fixture is synthetic; no existing NOFO records were changed.

- `before.png`: the existing `full` BYB variant, with the HRSA stylesheet from
  base commit `8fd4d7a9`. This remains the layout of existing HRSA records.
- `after.png`: the new `hrsa` BYB variant, with the required heading and exact
  paragraph after the internal-links callout. Only this variant loses the
  portrait page's extra 150px top padding.

Both renders use `portrait-hrsa-white`, the default filled icon style
(`nofo--icons--border`), a text-only cover, a single application deadline
(`05/06/2027`), and a real Step 2 link. A stored cover-image path is also supplied
to verify that the text-only cover does not display it.

## Verification

- The full document remains five pages; all BYB content fits on page 3.
- The new heading is a semantic `h3` under the page's `h2`; the PDF is tagged.
- Body text stays at 11pt; the subordinate heading is 13pt.
- The last line ends at 734.55pt, above the footer text starting at 770.90pt.
- Visually inspected both screenshots: no clipping, overlap, orphaned heading,
  or footer collision.
- PDF text extraction retains the complete paragraph in reading order.
- The text-only cover contains no raster images, despite its stored cover image.

The PDFs were rendered offline with [Prince](https://www.princexml.com/), the
rendering engine used by DocRaptor. These are local render checks, not a
production DocRaptor service request. The full PDFs are temporary QA artifacts;
the review screenshots are committed here.
