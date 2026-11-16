# FDA onboarding review evidence

Tracked in [#1341](https://github.com/HHS/simpler-grants-pdf-builder/issues/1341).

The original synthetic previews used a placeholder. The current cover uses the
[white FDA monogram from FDA.gov](https://www.fda.gov/themes/custom/preview/assets/images/FDA_Logo_Icon_White.svg)
with accessible text in the shared HTML template. Text only is the default.
Standard image uses the editor’s upload for that NOFO.

- [Draft text-only cover, 1,200px](cover-1200.png)
- [Draft text-only cover, 390px](cover-390.png)

Chrome rendered the draft long title without horizontal overflow at both widths.
The theme uses FDA Dark Blue (`#222C67`) with white text in the header
(12.93:1), and dark blue for headings and links, including in pale blue
(`#E0F2FF`) callouts (11.28:1). FDA Blue (`#007CBA`) is used for the
decorative cover rule. Public Sans headings and Source Sans Pro body text
are shared by the HTML and PDF templates.

References: [FDA Visual Identity Guidelines (2016)](https://fda.report/media/105076/FDA-Visual-Identity-Guidelines-Low-Res.pdf)
and the [FDA USWDS Theme](https://github.com/FDA/FDA-USWDS-Theme).

Use Builder’s existing PDF export to spot-check the final text-only cover,
logo alternative text and reading order. The template tests exercise PDF
source HTML. Initial account provisioning and live export are rollout steps.
