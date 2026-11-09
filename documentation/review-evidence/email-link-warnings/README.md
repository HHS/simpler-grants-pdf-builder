# Email link warning review

Captured November 9, 2026 on the local `codex/email-link-warnings` branch, with
upstream commit `8e660d25` as the baseline. This follows the email-link import
repair in [#1291](https://github.com/HHS/simpler-grants-pdf-builder/issues/1291).

A synthetic NOFO subsection contains `grants@example.gov` in plain text and an
internal link to a missing heading. Both screenshots show the same NOFO edit page
with the first warning tab active and the broken internal links list expanded.
The second screenshot also expands the new email link issues list.

- [Before at 1280 px](before-1280.png)
- [After at 1280 px](after-1280.png)

The local Chrome check compared both alert headings' computed fonts and
confirmed that the Markdown fits at 1280 and 390 px and the subsection link
targets the editor. To reproduce, save the synthetic example, open the NOFO edit
page at each width, and expand both warnings. The Django link classification
tests also follow the subsection save flow and verify that the warning clears
when the corrected Markdown is saved.

See [Add a link to an email address](../../EDITOR_TASKS.md#task-link-fix-email)
for current editor instructions.
