# Two-column Contents: second prototype

November 2, 2026. Follow-up to [the comparison](README.md) and
[the review on #1264](https://github.com/HHS/simpler-grants-pdf-builder/pull/1264#issuecomment-6585960991).
Related to [#1263](https://github.com/HHS/simpler-grants-pdf-builder/issues/1263).
**Design evidence only. No application behavior changes or implementation approval.**

## What changed

The introduction now spans the full width above the columns. The first step in
each column starts at the same height, including when the introduction wraps.
The prototype retains the existing step/subsection text sizes, complete fixture
labels, icons and individual link targets. The renderer chooses breaks from
content; there is no Step 4 split, height cap or removed entry. A small step stays
together when it fits; an oversized step is allowed to overflow.

These are the same invented fixture labels used in the first comparison, not a
new transcription of the authoritative HHS master. No title was shortened or
renamed to improve fit. The longer introduction is explicitly invented stress
text. Exact approved-master and real-document fidelity remain to be checked.

HTML stays single-column. The experiment also adds screen-only wrapping for the
Contents heading: at 320px with doubled text, the unbroken word otherwise exceeds
the available width. Synthetic destination headings receive the same treatment.
At narrow widths, screen-only Contents padding is 1rem rather than the existing
20mm preview padding, leaving more width for enlarged labels. These are prototype
rules to consider in implementation, not deployed fixes.

## Results

| Synthetic PDF | Contents pages | Result |
| --- | --- | --- |
| [29-entry FY27 shape](followup-fy27-ihs-columns.pdf) | 1 | Full-width introduction; aligned first steps; all links and counters retained. |
| [Wrapped introduction](followup-wrapped_intro-ihs-columns.pdf) | 1 | Introduction wraps above the columns without a second-column spacer. |
| [Oversized step, normal columns](followup-overflow-ihs-columns.pdf) | 3 | All entries retained, but continuation lacks a repeated step label and leaves excess space before the oversized step. Not ready. |
| [Oversized step, repeated-caption experiment](followup-overflow-ihs-captions.pdf) | 3 | Exact step name with “(continued)” appears at the two continuation fragments. Tagging and visual tradeoffs prevent adoption as-is. |

Each file also has artificial destination pages. They are not complete NOFOs.
Destination pages deliberately increment their printed counter by 17, exercising
two- and three-digit labels without making a hundred-page document. These are
printed labels, not physical PDF page indices. They are not a fit-rate sample.
The public test service's watermarks cross some text; those marks are not
authored layout content. All pages were rendered and inspected, with larger
Contents views used for layout checks.

![Revised Contents with spanning introduction](followup-contents.png)

![Continuation-caption experiment, not the proposed product design](followup-caption.png)

## Oversized-step feasibility finding

Prince 15.1 does repeat a table caption at a column break in this fixture. The
experiment uses `prince-caption-page: first` and `following`, with one original
linked step name and an unlinked continuation label. It does not require
JavaScript, a second layout pass, fixed subsection counts or shortened names.
See [Prince's caption guidance](https://www.princexml.com/doc/14/cookbook/) and
[its explanation of different repeated captions](https://www.princexml.com/forum/topic/2649/repeated-table-headers-with-different-content).

**Do not adopt this experiment as the production fallback.** Changing step
groups to CSS tables removes the numbered-step icons and changes the generated
structure: the normal oversized Contents has 62 `TOCI` entries and seven `TOC`
groups; the caption version has only nine `TOCI` entries and one `TOC` group.
Both retain 62 ordered link references, but that alone does not preserve the
step/subsection hierarchy. The continuation text has not been deliberately
marked as an artifact; its spoken treatment is unverified. Fixing those issues
could require renderer-specific tag customization and further testing.

This answers the narrow feasibility question, not the design acceptance
question. Keep the ordered-list version as the starting point and the caption
version as a rejected-as-is experiment. Do not hide repeated content from
assistive technology simply to make an automated count pass. Before a production
change, demonstrate a continuation treatment that retains hierarchy and verify
its actual screen-reader behavior.

## Checks and limits

- **30 offline checks:** five fixture shapes, three themes and two experiment
  modes preserve the baseline's ordered labels and unique destinations. The
  original 48 comparison checks also pass.
- **182 links across four PDFs:** every expected label is present, lands on a
  page containing that label, and has the correct printed number at the right
  edge of one of its annotation rectangles. The tag tree's ordered internal-link
  object references match source order, including the spanning introduction.
  This is more specific than content-stream extraction order, but is not a
  full tagged-content-order or screen-reader test.
- **60 isolated Chrome checks:** five fixture shapes, three themes, 320px/800px
  viewports and normal/doubled text. Computed text sizes are doubled, not merely
  the viewport or screenshot. All Contents links remain within the viewport;
  there is no horizontal document overflow. Every link is reached in source
  order using Tab with a visible outline; Enter reaches a distinct subsection.
  These fixtures do not load a logged-in profile or visit Builder.
- **HTML screen handling is probe-only:** heading wrapping and the first probe's
  focus/overflow rules are not application changes. These results do not certify
  the existing production HTML experience. They describe the candidate wrapper.
- **Still open:** approved IHS/master wording and representative prior-year/FY27
  corpus checks, actual PDF assistive-technology reading/navigation, magnification
  usability, full WCAG 2.0 AA evaluation, actual application-template integration,
  and a hierarchy-preserving oversized-step fallback. Landscape application
  behavior has not changed or been regression-tested by this slice.

No production record, import, provider credential, application PDF switch,
dependency or deployment configuration was changed. Only invented inputs and
repository assets went through the documented public DocRaptor test account,
with JavaScript off. Editor Tasks was reviewed; no instructions change because
the application workflow is unchanged.

## Reproduce

Use the locked Builder Python environment with the first probe's dependencies.
Only the explicit `pdf` subcommand sends the fixed synthetic fixture to the
public test service. There is no arbitrary-document input option.

```sh
python documentation/review-evidence/1263/columns_followup.py
python documentation/review-evidence/1263/columns_followup.py pdf
python documentation/review-evidence/1263/columns_followup.py pdf --sample wrapped_intro
python documentation/review-evidence/1263/columns_followup.py pdf --sample overflow
python documentation/review-evidence/1263/columns_followup.py pdf --sample overflow --mode captions
python documentation/review-evidence/1263/pdf_followup.py
PYTHON=/path/to/builder/python node documentation/review-evidence/1263/browser_followup.cjs
```

PDF checks require Poppler's `pdftotext`; browser checks require Playwright and
Chrome. Local generated HTML/PDFs, the machine-readable PDF check receipt and a
320px/doubled-text screenshot go under ignored `generated/followup/`.
The four linked PDFs and two Contents screenshots above are retained for review.

## Recommended next boundary

Review this prototype and the rejected caption tradeoff before a shared
application change. The next implementation should reuse the current Contents
template and theme cascade, preserve the list hierarchy and standardized source
wording, and include a demonstrated, readable overflow path. Keep #1263 open.
