# Email link warning review

Captured November 9, 2026 for [PR #1320](https://github.com/HHS/simpler-grants-pdf-builder/pull/1320),
with upstream commit `8e660d25` as the baseline. This follows the email-link import
repair in [#1291](https://github.com/HHS/simpler-grants-pdf-builder/issues/1291).

A synthetic NOFO subsection contains two plain-text email addresses,
`grants@example.gov` and `team@example.gov`, and an internal link to a missing heading. Both screenshots show the same NOFO edit page
with the first warning tab active and its single disclosure expanded. The
updated panel lists the broken internal link first, followed by both email
link issues and a single repair paragraph.

- [Before at 1280 px](before-1280.png)
- [After at 1280 px](after-1280.png)

The local Chrome check compared both alert headings' computed fonts and
confirmed that the Markdown fits at 1280 and 390 px, the disclosure opens by
keyboard, and the subsection link targets the editor. **Copy links** copies
all three issues in the mixed panel and keeps a closed disclosure closed. To
reproduce, save the synthetic example, open the NOFO edit page at each width,
and expand the link issues. The Django link classification tests also follow
the subsection save flow and verify that the warning clears when the corrected
Markdown is saved.

See [Add a link to an email address](../../EDITOR_TASKS.md#task-link-fix-email)
for current editor instructions.
