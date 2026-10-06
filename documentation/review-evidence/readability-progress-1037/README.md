# PDF analysis progress screenshots

Rendered locally from the actual Django template and repository assets using
synthetic context. Submission was intercepted to hold loading; the report uses
synthetic fixture data. No PDF was analyzed or sent to production.

- `modal-loading.png`: Working, without a dismissal button. The animation is
  advanced eight seconds for a readable still frame.
- `modal-ready.png`: Report response with OK; closes automatically after three
  seconds or immediately on OK, matching Word export.

Browser checks verified hidden OK while loading, ready-state display, automatic
closing and manual OK closing. Errors use the existing error page.
