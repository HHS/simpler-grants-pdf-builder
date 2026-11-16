# FDA onboarding review evidence

Tracked in [#1341](https://github.com/HHS/simpler-grants-pdf-builder/issues/1341).

The original synthetic previews used a placeholder. The current cover uses the
[white FDA monogram from FDA.gov](https://www.fda.gov/themes/custom/preview/assets/images/FDA_Logo_Icon_White.svg)
with accessible text in the shared HTML template. Text only is the default.
Standard image uses the editor’s upload for that NOFO.

- [Draft text-only cover, 1,200px](cover-1200.png)
- [Draft text-only cover, 390px](cover-390.png)

Chrome rendered the draft long title without horizontal overflow at both widths.
The draft white-on-navy header contrast was 12.93:1 and navy on the pale blue
callout background is 11.28:1.

Use Builder’s existing PDF export to spot-check the final text-only cover,
logo alternative text and reading order. The template tests exercise PDF
source HTML. Initial account provisioning and live export are rollout steps.
