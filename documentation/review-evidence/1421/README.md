# OASH theme review

These screenshots show Builder’s HTML preview for a synthetic NOFO in Chromium at 1,200 CSS pixels. The mobile cover uses a 390 px viewport. The Standard image preview uses a bundled sample photo in place of a per-notice upload.

## Screenshots

| Element | Preview |
| --- | --- |
| Text only cover and update banner | [Desktop](cover-text.jpg) · [Mobile](cover-mobile.jpg) |
| Standard image cover | [Desktop](cover-image.jpg) |
| Table of contents | [Outlined icons](contents-outlined.jpg) · [Filled icons](contents-filled.jpg) |
| Basic information | [Have questions?, Key facts, and Key dates](basic-information.jpg) |
| Help with systems | [Registration callout](help-with-systems.jpg) |
| Contact and support | [Support callout](contact-and-support.jpg) |
| Interstitial step pages | [Review the Opportunity](step-review.jpg) · [Contacts and Support](step-contact.jpg) |
| Application checklist | [Table header and blank row grid](checklist.jpg) |

## Color contrast

Ratios use WCAG 2.2 relative luminance. Compare normal text to the [4.5:1 minimum](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum) and meaningful graphics and component boundaries to the [3:1 minimum](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast).

| Foreground | Background | Ratio | Use |
| --- | --- | ---: | --- |
| White `#FFFFFF` | Navy `#162E51` | 13.60:1 | Filled icon glyphs and group label |
| Navy `#162E51` | White `#FFFFFF` | 13.60:1 | Cover header text, headings, Contents, active step and Outlined icons |
| Navy `#162E51` | Light lavender `#F2F2FA` | 12.22:1 | Callout headings, text and links, and checklist header text |
| Navy `#162E51` | Gold `#FACE00` | 9.00:1 | Cover update notice, Have questions? callout, and their links |
| Primary blue `#005EA2` | White `#FFFFFF` | 6.72:1 | Body links |
| Gray `#5C5C5C` | White `#FFFFFF` | 6.69:1 | Inactive step labels and checklist grid |
| Gray `#5C5C5C` | Light lavender `#F2F2FA` | 6.00:1 | Checklist header grid |

The callout and checklist tint matches the computed `#F2F2FA` **Stay Connected** background on [Health.gov](https://health.gov/). Its **News** panel uses a warm cream, `#FFFBF1`. The navy and gold accents use the [HHS.gov web palette](https://www.hhs.gov/branding/index.html).

## Logo source

The cover uses the [official Health.gov header SVG](https://health.gov/themes/custom/oash_uswds/images/logo_oash.svg) directly on the white cover header. The SVG is bundled with Builder and has the full office name as alternative text. Chromium verified that the logo loads and fits both desktop cover variants and the mobile Text only cover.

The review covers rendered HTML. Tagged PDF verification still needs a DocRaptor export, including cover reading order, running headers, printed page numbers, and link destinations.
