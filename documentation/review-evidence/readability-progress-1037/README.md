# PDF analysis progress screenshots

Rendered locally from the actual Django template and repository assets with
synthetic context and a synthetic filename. Submission was intercepted to hold
the pending state; no PDF was analyzed or sent to production. The animation is
advanced eight seconds for a readable still frame.

- `modal-loading.png`: desktop analysis progress.
- `modal-loading-mobile.png`: mobile analysis progress.
- `modal-dismissed.png`: progress hidden; submission remains disabled and the
  inline status remains visible while the request is pending.

The workflow replaces the page with a report or error; it does not have separate
success/error modal states.
