# ONC onboarding verification

[Issue #1286](https://github.com/HHS/simpler-grants-pdf-builder/issues/1286)
tracks onboarding. The theme uses the [inverse ONC logo PNG](https://healthit.gov/wp-content/uploads/2026/03/ONC_Primary-Horizontal_inverse@2x.png)
from HealthIT.gov, the issue's navy and gold, and Builder's bundled Public Sans
headings and Source Sans Pro body. It reuses the existing portrait cover layouts
and image-alt-text workflow. See [editor tasks](../../EDITOR_TASKS.md#task-theme)
and [group setup](../../GROUPS.md) for current instructions.

## November 10 local validation

- A synthetic ONC account imported a Word fixture. The preview and print source
  used the same long title, a sample deadline and an invented illustration.
- Chrome at 1,200 and 390 CSS pixels rendered both cover variants. The wordmark
  loaded with its text alternative; the cover and header did not overflow.
  The image cover exposed the illustration and its description; the text-only
  cover hid it. Heading and body styles used the expected bundled families.
- White text on navy, and navy titles on white, measured 14.12:1 for those
  solid colors. Navy and gold measured 9.05:1. The gold rule is decorative.
- Local Prince 17 rendered the HTML generated for Builder's PDF service, using
  its PDF/UA-1 profile without contacting DocRaptor. Both covers fit on one page
  with a legible logo and the complete title. Both PDFs embedded Public Sans
  and Source Sans Pro. The tag tree had the ONC wordmark alternative, deadline,
  title, opportunity number and HHS seal alternative before Contents; the image
  cover also included the illustration alternative. This is a bounded cover
  check, not a full PDF/UA or Section 508 audit. The mark in the upper right is
  from the local Prince renderer, not part of the theme.
- The ONC migration follows the Contents layout migration. A clean local test
  database applied both and Django found no missing migrations. Account
  creation, a conflicting opportunity-number prefix, group isolation, Bloom
  access and invalid theme-option submissions are covered by Django tests.

| Cover | Local prototype | HTML with ONC logo | Tagged PDF cover |
| --- | --- | --- | --- |
| Text only | [Before](text-before.jpg) | [After](text-after.jpg) | [Local PDF render](text-pdf.jpg) |
| Standard image | [Before](image-before.jpg) | [After](image-after.jpg) | [Local PDF render](image-pdf.jpg) |

## Cover and icon contrast matrix

ONC has one theme. The two cover options and two icon styles give four
combinations. Chrome verified the computed header and icon colors in a local
fixture using the Builder stylesheets and shared SVG artwork. The same ONC icon
rules apply to screen and print. The icons supplement visible section labels.

| Cover | Icon style | Cover header text | Icon glyph and fill |
| --- | --- | --- | --- |
| Text only | Outlined | White on navy, 14.12:1 | Navy on white, 14.12:1 |
| Text only | Filled | White on navy, 14.12:1 | White on navy, 14.12:1 |
| Standard image | Outlined | White on navy, 14.12:1 | Navy on white, 14.12:1 |
| Standard image | Filled | White on navy, 14.12:1 | White on navy, 14.12:1 |

These solid-color pairs exceed 4.5:1 for normal text and 3:1 for graphics.
Both cover layouts place the title on white and keep the image separate from
the text. The gold cover rule is decorative. This matrix covers the ONC theme
colors and icon treatment. The PDF cover renders above cover both layouts.
A full export check with the revised icons remains part of rollout validation.

## Rollout checks

Verify a live Builder export in an environment where DocRaptor is authorized.
After the approved deployment, a superuser can create the agreed initial
accounts. Grant OpDiv Admin only to designated staff. Then verify sign-in,
import and group isolation with the approved rollout accounts. No accounts
were provisioned for this local test.

## Current Builder screenshots

Chrome captured the rendered HTML at a 1,200 CSS pixel viewport. The same
synthetic Word NOFO was imported as an ONC user and used throughout. The
import selected ONC and Text only. The sample includes a long title, a
bundled cover image for the Standard image option, and synthetic Key facts
and Key dates callouts. The theme picker exposed one theme, two cover
options and two icon styles.

| View | Text only / Outlined | Standard image / Filled |
| --- | --- | --- |
| Cover | [Text only, the import default](onc-cover-text.jpg) | [Standard image](onc-cover-image.jpg) |
| Contents | [Outlined icons](onc-contents-outlined.jpg) | [Filled icons](onc-contents-filled.jpg) |
| Step 1 opener | [Outlined icon](onc-step-1.jpg) | [Filled icon](onc-step-1-filled.jpg) |

- [Page after the Step 1 opener, with the right column callouts](onc-step-1-callouts.jpg)
- [Theme options as an ONC editor](onc-theme-options.jpg)

These are browser screenshots. The earlier tagged PDF cover renders remain
available above.
