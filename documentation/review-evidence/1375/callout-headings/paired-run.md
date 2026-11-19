# Basic information callout headings — paired replay

On November 19, 2026, the maintainer opted in to replay the [callout-heading task in PR #1406](https://github.com/HHS/simpler-grants-pdf-builder/pull/1406). The original implementation and its before-and-after images are in the [single-run record](README.md).

## Starting point and prompts

Both coding sessions used the same inherited Codex model and permissions, Python 3.14.3, and separate clean local checkouts at `b421b43ae1769dc83875b120975cb68bc449c0b5`. Each received only its task and checkout instructions. Neither reported finding the existing PR implementation. The coordinator retained both diffs before scoring. Both sessions were asked to report when they read the guide, which may have cued the usual-prompt session to consult it.

> On new import and re-import, under Step 1: Review the Opportunity > Basic information, promote an exact first standalone paragraph of a one-cell callout table matching Key dates, Key facts, or Application due date to an editable semantic H4 callout title. Normalize casing/whitespace, preserve the rest of the content and links, leave ordinary prose, multi-cell tables, unrelated labels and matching paragraphs outside this scope alone, and preserve existing styled-heading behavior. Confirm HTML and the HTML supplied to the PDF renderer. Leave changes in the checkout.

Both sessions were told to read the checkout’s AGENTS.md, use local files only, avoid pushing or opening a PR, and report test commands, results, and when they read the import guide. The pointer prompt added “Before editing, consult `documentation/IMPORT_RULES.md`.”

## Common verification

Apply one patch to the pinned commit. Copy [the common fixture](verify_callout_headings.py) to `nofos/nofos/tests_nofos/test_pilot_callout_common.py`. From `nofos/`, run:

```sh
python manage.py test nofos.tests_nofos.test_pilot_callout_common --verbosity 0
```

The original seven tests exercise actual Word import and overwrite, saved headings, HTML and PDF-template markup, preserved links and styled headings, and scope boundaries for H1 and H2 source documents. On the baseline, new import and overwrite failed for missing headings, and the boundary check failed for both source heading levels. Both patches passed those seven tests. The reviewer identified a manual Word line break inside one paragraph as a missed whitespace case. The coordinator added the same check for both final patches. PDF checks cover renderer input HTML. The generated PDF tag tree remains unverified.

## Blind review and outcome

A fresh reviewer received anonymous patches, the task, the import-rule requirement, and the common results. The reviewer initially suspected dropped paragraph anchors, then retracted that finding after confirming that the existing subsection factory retains an ID on the promoted paragraph in both patches.

| Evidence | [Patch 1](patch-1.patch) | [Patch 2](patch-2.patch) |
| --- | --- | --- |
| Original common tests | 7 passed | 7 passed |
| Follow-up with manual line break | 8 passed | 7 passed, 1 failed |
| Task correctness | **Pass.** Treats a manual break in the title as whitespace. | **Fail.** Leaves an otherwise matching title in the callout body when words are separated by a manual break. |
| Documentation accuracy | **Pass.** IMPORT-025 describes the scope, title normalization, and body preservation. | **Fail.** IMPORT-025 promises whitespace normalization without noting the manual-break exclusion. |
| Combined | **Pass** | **Fail** |
| Prompt, revealed after scoring | Direct pointer | Usual prompt |
| Import guide read before the first relevant edit | Yes, reported by the session | Yes, reported by the session |

The coordinator reproduced the manual-break failure on the implementation already in PR #1406. The PR implementation remains the original single-run version. The maintainer's patch selection and decision on enrollment in the 12 scored pairs are pending.
