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
| White `#FFFFFF` | Navy `#162E51` | 13.60:1 | Cover header, Filled icon glyphs and group label |
| Navy `#162E51` | White `#FFFFFF` | 13.60:1 | Headings, Contents, active step and Outlined icons |
| Navy `#162E51` | Pale blue `#E5FAFF` | 12.60:1 | Callout headings, text and links, and checklist header text |
| Navy `#162E51` | Gold `#FACE00` | 9.00:1 | Cover update notice, Have questions? callout, and their links |
| Primary blue `#005EA2` | White `#FFFFFF` | 6.72:1 | Body links |
| Gray `#5C5C5C` | White `#FFFFFF` | 6.69:1 | Inactive step labels and checklist grid |
| Gray `#5C5C5C` | Pale blue `#E5FAFF` | 6.19:1 | Checklist header grid |

The [HHS.gov web palette](https://www.hhs.gov/branding/index.html) is the design source. White on the alternate dark blue `#1A4480` is 9.62:1. Navy on teal `#1DC2AE` is 6.08:1. Keep gold and teal out of white-text treatments, where they give 1.51:1 and 2.24:1 respectively. This implementation uses one navy theme.

## Logo references

- [OASH and ORI webinar slides](https://ori.hhs.gov/sites/default/files/2022-01/2022-Final_IR-ORI-21-002%20%28ORI%20Conferences%29%20TA%20Webinar.pdf) show the full-color OASH wordmark next to the HHS mark on the opening slide.
- The [OASH recruitment postcard](https://health.gov/sites/oash/files/transcripts/2024-04/Benefits%20Postcard.pdf) shows the white OASH wordmark at the upper left.
- [OASH’s official site](https://health.gov/about-oash) gives the office name used in the preview. The cover shows that name as text and uses Builder’s existing HHS mark. The standalone OASH artwork and final palette need confirmation from OASH before rollout.

The review covers rendered HTML. Tagged PDF verification still needs a DocRaptor export, including cover reading order, running headers, printed page numbers, and link destinations.
