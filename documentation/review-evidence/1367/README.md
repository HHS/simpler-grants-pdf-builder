# #1367 evidence: single Readability Checker URL

Local check of [#1367](https://github.com/HHS/simpler-grants-pdf-builder/issues/1367)
on November 15, 2026. Inspected branch `claude/eloquent-mayer-s220qg`, based on
upstream `main` at `4b3b920`. Local `runserver` with SQLite, synthetic accounts
and no documents, driven by Playwright Chromium at 1280px and 390px widths.
Public switch off, signed-in switch on. Current guidance is in
[signed-in Readability Checker access](../../readability/AUTHENTICATED_PDF_READABILITY_PILOT.md).

| Check | Result |
|---|---|
| Signed out, `/readability-checker/` | Unavailable page with **Login** in the header ([screenshot](signed-out-unavailable.png)) |
| Signed out, `/nofos/readability-checker/` | One redirect to `/readability-checker/` |
| **Login** link | Opens `/users/login/?next=/readability-checker/`; password sign-in returns to the checker |
| Signed in, `/readability-checker/` | Upload form, with the user's email in the header ([screenshot](signed-in-checker.png)) |
| Print media | Header nav hidden, so the email isn't printed |
| 390px width | Header nav hidden, as on the Builder header, which also has no menu button at this width |

The phone-width behavior matches the existing Builder header. Making the account
item reachable on small screens would be a change to the shared header pattern,
not part of #1367.

Not covered here: deployed environments, WAF behavior, and production recording
settings. Those belong to the companion `HHS/simpler-grants-gov` changes.
