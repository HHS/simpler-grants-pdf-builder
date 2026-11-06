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

## Rollout checks

Verify a live Builder export in an environment where DocRaptor is authorized.
After the approved deployment, a superuser can create the agreed initial
accounts. Grant OpDiv Admin only to designated staff. Then verify sign-in,
import and group isolation with the approved rollout accounts. No accounts
were provisioned for this local test.
