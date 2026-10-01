# Points column width (#1007)

Local Chromium verification, October 1, 2026, using print media at an 816px
(8.5in) viewport. The page is the real Django `nofo_view` template with the
`portrait-cdc-blue` theme and repository styles, rendering a local test NOFO
whose scoring tables are copied from the issue's example. It is not a
production NOFO or a DocRaptor PDF.

- [Before](before.png): "10 points" wraps onto two lines in the Organizational capacity table.
- [After](after.png): the points column shrinks to fit its widest cell, and "10 points" stays on one line. The "Point value" header still wraps, as intended.

The "before" image is the same page with the `col--points` classes removed.
Chromium lays out tables a little differently from the DocRaptor PDF renderer,
which wrapped every points cell in the issue's screenshots.
