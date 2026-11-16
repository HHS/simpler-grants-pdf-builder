# FDA onboarding draft evidence

Tracked in [#1341](https://github.com/HHS/simpler-grants-pdf-builder/issues/1341).
The draft cover is a synthetic example. It contains a neutral box marked
“Logo placeholder,” not an FDA mark or approved artwork. The colors and font
choices are provisional pending FDA review.

- [Text-only cover, 1,200px](cover-1200.png)
- [Text-only cover, 390px](cover-390.png)

Chrome rendered the long fixture title without horizontal overflow at both
widths. Its computed white-on-navy header contrast was 12.93:1. This is a
check of that draft color pair, not a theme-wide contrast audit.

The focused tests cover import, re-import, group isolation, theme-option
validation, and the PDF HTML template for both cover modes. They do not prove
PDF tagging or reading order. Before merge, replace the placeholder with the
approved asset, capture same-state before/after evidence and theme options,
and validate the final cover and callouts in both cover and icon modes. Check a
tagged PDF for logo alternative text, reading order, and contrast. Deployed
account provisioning and live DocRaptor verification are separate rollout steps.
