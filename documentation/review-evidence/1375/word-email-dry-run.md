# Dry run 2 — Word email links

[Tracking issue #1375](https://github.com/HHS/simpler-grants-pdf-builder/issues/1375) · [Pilot evidence index](README.md)

Replayed [#1290](https://github.com/HHS/simpler-grants-pdf-builder/pull/1290) on November 16, 2026, from its pre-fix parent `0a90923bd0c613bfdaa9beabae0eec9ec8b879dc`. This calibration run is excluded from the 12 scored task pairs.

## Setup and prompts

Two fresh `gpt-6.1-sol` coding sessions used separate shallow checkouts, no network, the same repository instructions, and the same Python 3.14.3 environment. Neither received the historical patch, PR number, or scoring rubric. The coordinator did not ask about documentation reads until after editing, to avoid making the usual prompt more prescriptive.

Both sessions received this task:

> Fix Word import so an email address that Word saved as a file URL becomes a working mailto link when its decoded final path component exactly matches the displayed email address. Preserve the displayed text and leave existing email links, unrelated links, mismatched labels, and ambiguous file targets with queries or fragments unchanged. Verify with synthetic examples.

One session also received “Before editing, consult `documentation/IMPORT_RULES.md`.” The separate reviewer received the task, both de-identified patches, and the shared results. The coordinator revealed the prompt mapping after scoring.

## Verification and scores

The first [HTML-only check](verify_word_email_shared_html.py) was pinned before the runs. It failed on the pre-fix commit, passed on the historical fix, and bypassed both candidates' Word-specific repair. To check the requested workflow, the coordinator ran the same input cases through the real Word parser using [synthetic DOCX files](verify_word_email_links.py), then verified the links in Builder's parsed content. The DOCX check reproduced both missing repairs on the baseline and passed on the historical fix and both candidates.

| Evidence | [Patch 1](word-email-patch-1.patch) | [Patch 2](word-email-patch-2.patch) |
| --- | --- | --- |
| Shared synthetic DOCX checks | 3 groups passed, 9 cases | 3 groups passed, 9 cases |
| Same focused Django command | 78 passed | 78 passed |
| Task correctness | **Pass.** Handles the common cases and also repairs a Word target with Windows backslashes. | **Fail.** Handles the common cases but leaves that Windows target unrepaired because it splits the path only on forward slashes. |
| Import-rule accuracy | **Pass** for the core rule. The guide could identify the line break and image exclusions. | **Pass** for the core rule. The guide could identify the line break exclusion. |
| Combined outcome | **Pass** | **Fail** |
| Opened guide before first relevant edit | Yes, self-reported. Independent timing unknown. | Yes, self-reported. Independent timing unknown. |
| Prompt mapping, revealed after scoring | Direct pointer | Usual prompt |

The coordinator reproduced the review finding with a synthetic DOCX hyperlink whose target was `file:///C:\Users\writer\person@example.test` and label was `person@example.test`. Patch 1 and the historical merge returned `mailto:person@example.test`; Patch 2 and the pre-fix baseline kept the file URL. This was a follow-up probe after blind review.

From a checkout at the pinned base with either patch applied and project dependencies installed, reproduce the common checks:

```sh
DJANGO_SETTINGS_MODULE=bloom_nofos.settings PYTHONPATH="$PWD/nofos" python /path/to/verify_word_email_links.py
cd nofos
python manage.py test nofos.tests_nofos.test_content_processing nofos.tests_nofos.test_document_processing nofos.tests_nofos.test_import nofos.tests_nofos.test_reimport --noinput
```

For the follow-up probe, load the shared DOCX script with `runpy.run_path` using the same environment and call `WordEmailLinkChecks().check_target` with the Windows target, label, and expected mailto URL above.

## Calibration

Both session pairs and blind reviews ran, and the evidence records were reproducible. Before the scored tasks, pin a shared check at the actual entry point and include representative inputs that should change and inputs that must be preserved. Record follow-up probes separately. Keep independent guide-read timing unknown unless the tooling can verify it. This second dry run produced one pointer-only pass, which is calibration evidence. Maintainer calibration and adoption decisions remain pending. The candidate patches are included as evidence artifacts.
