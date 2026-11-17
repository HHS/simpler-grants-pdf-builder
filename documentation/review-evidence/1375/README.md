# NOFO Builder pilot evidence for #1375

[Tracking issue](https://github.com/HHS/simpler-grants-pdf-builder/issues/1375) · [Pilot procedure and rubric](../../AI_CONTRIBUTION_EVALUATION.md)

## First dry-run candidate

Replay [#1349](https://github.com/HHS/simpler-grants-pdf-builder/pull/1349) from its merge commit's parent, `56699bed09d816a5f26ff8897bef57059ea17dc6`. The parent contains the existing import-rule instructions. The replay was completed as the first dry run below.

Standalone task for both coding sessions:

> On NOFO import and reimport, normalize applicant note labels at the start of paragraphs, including in table cells. Handle labels such as “PLEASE NOTE:”, “Note –”, and “N.B.” and render the label as bold “Note:”. Preserve the text and formatting after the label. Leave ordinary sentences and labels embedded in a paragraph alone. Include focused verification using synthetic inputs.

Before running, pin common verification for paragraph starts, table cells, preserved inline formatting, and nonmatching text. Also check that the normalized label appears in the imported content. Use the same fixtures and commands for both patches. Keep this page and the merged PR reference with the coordinator.

## Evidence template

- Task and date
- Starting commit, agent, model, permissions, and test setup
- Common verification commands and expected results
- Patch 1 and Patch 2 references or run outcomes
- Test results for each patch
- Task correctness and documentation accuracy scores with evidence
- Prompt-to-patch mapping, revealed after scoring
- Guide opened before first relevant edit for each run, or unknown
- Maintainer corrections, decision, and links to any resulting PR

## Dry run 1 — November 16, 2026

**Scope.** Replay the standalone task above from the pinned pre-fix commit. This is a calibration run and is excluded from the 12 scored pairs. Neither patch is proposed for integration.

**Setup.** A local Codex CLI launch failed during session initialization with an environment permission error. The coordinator used two fresh, context-isolated Codex coding sessions with the same model (`gpt-6.1-sol`), workspace permissions, and Python 3.14.3 environment. Each had its own shallow checkout from the same commit, with no Git remote configured. Both were instructed to work only in their assigned checkout, avoid network access, and report their tests and the order of documentation reads and edits. That last instruction may itself cue the usual-prompt session to consult documentation. The coding sessions did not receive the merged patch, its PR number, or the scoring rubric. Neither reported accessing the merged solution.

**Prompts.** Both sessions received this standalone task:

> On NOFO import and reimport, normalize applicant note labels at the start of paragraphs, including in table cells. Handle labels such as “PLEASE NOTE:”, “Note –”, and “N.B.” and render the label as bold “Note:”. Preserve the text and formatting after the label. Leave ordinary sentences and labels embedded in a paragraph alone. Include focused verification using synthetic inputs.

The pointer variant also received “Before editing, consult `documentation/IMPORT_RULES.md`.” The reviewer received the task, the existing import-rule requirement, both patches, and common test outcomes. Prompt labels and session commentary were withheld until scores were recorded.

### Verification

Apply either patch to a fresh checkout of `56699bed09d816a5f26ff8897bef57059ea17dc6`. Save the [common test script](verify_applicant_notes.py) outside that checkout. With the project's Python dependencies installed, run the following from the checkout root:

```sh
PYTHONPATH="$PWD/nofos" python /path/to/verify_applicant_notes.py
cd nofos
python manage.py test nofos.tests_nofos.test_content_processing nofos.tests_nofos.test_document_processing nofos.tests_nofos.test_import nofos.tests_nofos.test_reimport --noinput
```

The common script covers the named prefixes, inline formatting and links, table cells, ordinary and embedded prose, and the normalized label reaching a parsed subsection. It failed on the pre-fix commit and passed on the historical merged implementation. The Django command targets the same modules for both patches. Its counts differ because the patches add different tests.

| Evidence | [Patch 1](patch-1.patch) | [Patch 2](patch-2.patch) |
| --- | --- | --- |
| Common applicant-note checks | 4 passed | 4 passed |
| Common Django module command | 81 passed | 82 passed |
| Task correctness, blind reviewer | **Fail.** `N.B.-based organizations` is rewritten as a note. | **Fail.** Both `N.B.-based organizations` and `N.B.’s office` are rewritten as notes. |
| Import-rule accuracy, blind reviewer | **Fail.** IMPORT-079 omits the ASCII hyphen placement condition for `Note` and does not identify where matching stops at inline markup. | **Fail.** IMPORT-079 says an ASCII hyphen requires whitespace or the end of a run. The implementation accepts `N.B.-based` and matches over concatenated text nodes. |
| Combined outcome after coordinator verification | **Fail** | **Fail** |
| Opened the guide before the first relevant edit | Self-reported yes. Independent sequence verification unknown. | Self-reported yes. Independent sequence verification unknown. |
| Prompt mapping, revealed after scoring | Direct pointer | Usual prompt |

### Coordinator spot-check

The original checks passed on both patches. Follow-up probes after blind scoring confirmed that both changed the ordinary paragraph `N.B.-based organizations may apply.` to a bold note and that Patch 2 also rewrote `N.B.’s office is open.` The merged reference preserved both paragraphs. The reviewer also flagged that Patch 1 emits `**Note:**Apply by Friday.` for an adjacent label and hypothesized that bold might be lost. Builder’s Markdown rendering preserved the bold label in the coordinator probe. This correction does not change the correctness score.

The dry run exercised separate coding and review sessions, a reusable test command, and a checkable evidence record. Guide-read timing was self-reported. Before scored runs, add ordinary-prose boundary cases to the common checks, remove the coding-session instruction to report documentation reads if independent event capture is available, and calibrate the rubric on the second dry run. No adoption decision is due from this dry run. Maintainer calibration is pending.

## Second dry run

See [Word email link evaluation](word-email-dry-run.md) for the prompts, scores, and reproducible evidence.

## Inline “Need help?” callout rendering — November 17, 2026

The maintainer requested an evidence record for a rendering change that adds the Contacts and Support icon to qualifying inline help callouts. The PR starts from `17dbf3c71d3605da49916e48c413238e727f79f0`. This entry records one implementation and its verification. The scored pilot measures paired runs on changes to import behavior.

The new match is case-insensitive and checks the opening paragraph of the rendered callout body. It recognizes an opening “Need help?” or “Need any help?” followed by a direction such as “See,” “Visit,” “Go to,” or “Refer to” Contacts and Support. Bold text and link markup are supported. The rule uses the visible destination wording, so it also works when the section name is plain text.

| Example | Observed rendering |
| --- | --- |
| `Need help? See Contacts and Support.` | Contact icon before the body |
| `**Need help?** Visit [Contacts and Support](#contacts-and-support).` | Contact icon before the body, with the link preserved |
| `Need any help? Please refer to the Contact and Support section.` | Contact icon before the body |
| `Need help? Visit Grants.gov.` | No icon |
| `Need help? Email the Contacts and Support team.` | No icon |
| Heading `Need help?` with body `See Contacts and Support.` | No icon |
| `See [our guide](#contacts-and-support) if you need help.` | No icon |

From `nofos/`, run `python manage.py test nofos.tests_nofos.test_callout_box nofos.tests_nofos.test_templatetags --noinput`. All 250 tests passed in the local verification checkout, which used the pinned versions of the changed production files over the available upstream checkout. The focused tests render the shared Django template and also cover the thin icon, existing “Have questions?” and Adobe Reader icons, and the inline scope of the new rule.

## SAMHSA Word import BYB setting — November 17, 2026

[Scored pair, verification, and both patches](samhsa-byb.md).
