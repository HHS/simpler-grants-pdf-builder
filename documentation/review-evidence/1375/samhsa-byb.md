# SAMHSA Word import BYB setting

[Tracking issue](https://github.com/HHS/simpler-grants-pdf-builder/issues/1375) · [Evidence index](README.md)

## Task and setup

On November 17, 2026, the maintainer enrolled a task to set **BYB page with eRA**
on Word imports and re-imports when the NOFO's group or the uploaded OpDiv
identifies SAMHSA. The previous single-implementation PR (#1395) was closed and
its branch reset before the paired runs.

Both coding sessions started in separate clean worktrees at
[`aa0fdc362b86cd921c1a8188019e412cb7fc30d3`](https://github.com/HHS/simpler-grants-pdf-builder/commit/aa0fdc362b86cd921c1a8188019e412cb7fc30d3).
This locally available upstream ancestor had IMPORT-044 and predated the fix.
It was nine commits behind the original PR's base. Both fresh Codex sessions
inherited the same model, reasoning, settings, and permissions. The exact model
identifier was unavailable in their results. They shared the Python 3.14.3,
Django 6.0.8, and Mammoth 1.12.2 test environment. Two earlier CLI launches
stopped before starting a coding session because the app server could not
initialize under the sandbox. Both were replaced by fresh sessions with no
conversation history passed in.

## Prompts

The usual prompt was:

> Update NOFO Builder so that importing or re-importing a Word document sets the NOFO’s Before you begin page setting to the existing BYB page with eRA option when the NOFO belongs to the SAMHSA OpDiv group or the document identifies SAMHSA in the OpDiv metadata. Apply the setting on re-import even if a different option was saved. Keep other import behavior the same. Leave the patch in this checkout for review.

The second prompt appended:

> Before editing, consult `documentation/IMPORT_RULES.md`.

Both sessions reported opening the import guide before making their first
relevant edit and encountering no previous implementation. These are session
self-reports.

## Common verification

Both patches passed the same 51-test command. The synthetic Word upload contract
exercised group membership with a generic OpDiv, abbreviated and full SAMHSA
OpDiv names, a generic new import, direct and confirmed re-imports, and the
archived setting. The base failed all five SAMHSA assertions and passed both
generic controls. The base also passed all 46 tests in the existing HRSA BYB
and metadata-block suites.

Apply each raw patch on its own fresh worktree at the base. Make
[the contract module](samhsa-byb/test_samhsa_byb_contract.py) available on
`PYTHONPATH`, then run this command from the worktree's `nofos/` directory:

```sh
python manage.py test test_samhsa_byb_contract nofos.tests_nofos.test_metadata_block_import nofos.tests_nofos.test_hrsa_byb --noinput
```

## Blind review

The separate review session received the two numbered patches and the common
verification results. The prompt mapping was withheld until after scoring.

| Patch | Prompt | Task correctness | Documentation accuracy | Combined |
| --- | --- | --- | --- | --- |
| [1](samhsa-byb/patch-1.diff) | Import-guide pointer | Pass | Fail | Fail |
| [2](samhsa-byb/patch-2.diff) | Usual | Pass | Pass | Pass |

Both patches use the Word import MIME type, carry the Word flag through the
confirmation path, and set the variant after the re-import archive is created.
Both update IMPORT-044. Patch 1 leaves contradictory statements about preserving
the saved variant across re-import in IMPORT-062 and the introductory page
guide. Patch 2 updates both places to reflect the exception. The reviewer ranked
Patch 2 first on documentation grounds.

The result for this pair is **usual-only**. Both patches passed task
correctness. A confirmation opened before deployment and submitted after
deployment lacks the new Word flag in its saved session. The reviewer identified
that rollout case as untested for both patches.

Maintainer decision pending.
