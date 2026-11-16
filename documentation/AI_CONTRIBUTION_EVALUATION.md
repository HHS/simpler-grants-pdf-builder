# AI contribution evaluation pilot

This opt-in procedure supports [#1375](https://github.com/HHS/simpler-grants-pdf-builder/issues/1375). It tests whether an explicit pointer to the import guide improves coding-agent output.

## Start a pilot run

The maintainer starts the evaluation by asking “Run the #1375 pilot for <task>.” The coordinating session reads this guide. An ordinary coding or PR request follows the normal contribution workflow. A file change, issue reference, PR label, or PR creation does not start the pilot. If a pilot patch goes through normal PR review, link its evidence record and #1375 in the PR summary.

## Enroll scored tasks as they come up

Enroll a task when the maintainer opts in and the request changes how Builder imports a document in a way that can be verified with a small example. Decide whether it qualifies before launching either coding session. Enroll one distinct task at a time, up to the planned 12 scored pairs. Keep enrolled outcomes in the evidence record, including failed or empty runs. The two calibration dry runs are separate from the scored round.

## Prepare the pair

1. Turn the request into a standalone coding goal. Before launching either run, record the base commit, what should change, what should stay the same, and the common verification commands and expected results. Verify through the actual import path. For Word import, use a small synthetic Word document with examples that should change and examples that should be preserved. For historical tasks, check that the base predates the fix and contains the existing import rule. Keep links to the merged solution in the coordinator's notes.
2. Create two clean worktrees at that commit. Use two fresh coding sessions with the same agent, model, settings, permissions, and test setup. Keep evidence files and this procedure out of the inputs to those sessions. The usual repository instructions apply in both.
3. Give one session the standalone prompt. Give the other that exact prompt plus “Before editing, consult `documentation/IMPORT_RULES.md`.” Capture both results before comparing them. Use fresh Codex desktop threads if the coordinator cannot launch separate sessions, and give the operator the two exact prompts and the pinned base.
4. Run the same focused verification against both patches. Retain failed and empty runs. Record infrastructure problems separately from patch quality. If a replay session finds the merged solution, flag the pair and select a different dry-run task.

## Score the patches

Give a fresh review session the original task, expected behavior, applicable repository rules, both patches, and common test results. Present them as Patch 1 and Patch 2. Withhold the prompt mapping and coding-session commentary until scores are recorded. A reviewer may still infer the mapping from a patch, so each judgment should cite the diff, a test result, or the applicable rule.

| Check | Pass when |
| --- | --- |
| Task correctness | The patch achieves the specified import behavior, preserves the specified existing behavior, and the available verification supports both. |
| Documentation accuracy | The matching entry in the import guide accurately describes what changed. |

Record pass, fail, or unknown for each check, with evidence. The combined result passes when both checks pass, fails when either check fails, and is unknown otherwise. If review identifies a case the planned checks missed, apply the same follow-up check to both patches and record its results separately from the planned checks. During the two dry runs, the maintainer checks the automated judgments and resolves rubric ambiguities. During scored runs, spot-check decisions and adjudicate uncertainties that could change the recommendation. Preserve corrections and their rationale.

## Record the evidence

Use the [pilot evidence record](review-evidence/1375/README.md). Keep the task, base commit, agent configuration, prompts, patches or run outcomes, common test results, review scores, and maintainer decision. Record whether the guide was opened before the first relevant edit when the event sequence is available. Mark it unknown otherwise. Publish short records using synthetic or public material. Keep raw transcripts and restricted content out of the public evidence.

Keep the proposed stopping point and decision rule in #1375 recorded before the first scored pair. Evaluate the results after 12 distinct scored pairs. Report both-pass, pointer-only, usual-only, and neither-pass pairs where both combined outcomes are known. Report pairs with unknown outcomes separately and report task correctness for each prompt. Use `pointer-only − usual-only` for net additional passes. The proposed threshold is at least three net additional combined passes with task correctness at least as high overall. If unknown outcomes could change the decision, report the result as inconclusive.
