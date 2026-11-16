# FDA onboarding review evidence

Tracked in [#1341](https://github.com/HHS/simpler-grants-pdf-builder/issues/1341).

## Updated FDA theme: local Chrome

Rendered four copies of a fictional notice with Builder's actual document
view on PR #1383. The Standard image sample uses locally supplied abstract
art, not an FDA photograph. There is one FDA theme, `portrait-fda-blue`.
The cover uses the [FDA.gov monogram asset](https://www.fda.gov/themes/custom/preview/assets/images/FDA_Logo_Icon_White.svg);
the bundled SVG matches the source after normalizing XML syntax. The image
loads with the alt text “U.S. Food and Drug Administration logo.” This verifies
the artwork source and HTML, not separate FDA brand sign-off or PDF tagging.

| Cover | Icons | 1,200 px | 390 px |
| --- | --- | --- | --- |
| Text only | Filled | [Cover](text-filled-1200-cover.png) | [Cover](text-filled-390-cover.png) |
| Text only | Outlined | [Cover](text-outlined-1200-cover.png) | [Cover](text-outlined-390-cover.png) |
| Standard image | Filled | [Cover](image-filled-1200-cover.png) | [Cover](image-filled-390-cover.png) |
| Standard image | Outlined | [Cover](image-outlined-1200-cover.png) | [Cover](image-outlined-390-cover.png) |

- First content page: [desktop](text-filled-1200-content.png) and
  [mobile](text-filled-390-content.png). Includes Key Facts, Key Dates and
  Have questions? on the right at desktop widths, plus a mid-section note
  and keyboard tip. The right-hand callouts stack on mobile.
- Step page: [Filled](text-filled-1200-step.png) and
  [Outlined](text-outlined-1200-step.png).

The synthetic title, header and first content page showed no horizontal
overflow in the checked Chrome layouts. The FDA mobile stylesheet keeps the
update callout inside the header and separates the Standard image from the HHS
seal. If no cover art is selected, the shared template omits the image instead
of emitting an empty source.

### Measured contrast

Ratios use computed Chrome foreground and background colors and match across
both widths and all four cover/icon combinations on the sampled pages.

| Element | Ratio |
| --- | ---: |
| White cover header text on FDA Dark Blue; dark-blue cover title on white | 12.93:1 |
| Cover update, Key Facts, Key Dates, Have questions?, mid-section note, and keyboard tip: sampled heading/body text and links on pale blue | 11.28:1 |
| Contact and keyboard callout glyphs on pale blue | 11.28:1 |
| Filled step icon: white glyph on dark-blue disc and disc against white | 12.93:1 |
| Outlined step icon: dark-blue glyph and outline against white | 12.93:1 |

The sampled combinations meet 4.5:1 for normal text and 3:1 for graphics.
The cover rule is decorative. These spot checks do not establish full
accessibility conformance or the tagged PDF's contrast or reading order.

## Earlier placeholder previews

- [Draft text-only cover, 1,200px](cover-1200.png)
- [Draft text-only cover, 390px](cover-390.png)

These original previews predate the FDA.gov artwork. Use the updated captures
above for design review.

References: [FDA Visual Identity Guidelines](https://www.fda.gov/media/102663/download)
and the [FDA USWDS Theme](https://github.com/FDA/FDA-USWDS-Theme).

Use Builder’s existing PDF export to spot-check the final text-only cover,
logo alternative text and reading order. The template tests exercise PDF
source HTML. Initial account provisioning and live export are rollout steps.
