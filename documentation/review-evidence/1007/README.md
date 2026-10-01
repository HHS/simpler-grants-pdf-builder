# Points column width (#1007)

Local Chromium verification, October 1, 2026, using print media at an 816px
(8.5in) viewport. Both pages are the real Django `nofo_view` template with the
`portrait-cdc-blue` theme and repository styles, rendering local test NOFOs
whose scoring table is copied from the issue's example. They are not
production NOFOs or DocRaptor PDFs.

- [Before](before.png): a NOFO imported before this change (no `{: .col--points }`
  marker in its Markdown). "10 points" wraps onto two lines. This is also how
  existing NOFOs keep rendering after this change.
- [After](after.png): the same table run through the import converter (`md()`),
  which writes `| **Point value** {: .col--points } |`. The points column shrinks
  to fit its widest cell, and "10 points" stays on one line. The "Point value"
  header still wraps, as intended.

Chromium lays out tables a little differently from the DocRaptor PDF renderer,
which wrapped every points cell in the issue's screenshots.
