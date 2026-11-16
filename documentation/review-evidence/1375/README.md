# NOFO Builder pilot evidence for #1375

[Tracking issue](https://github.com/HHS/simpler-grants-pdf-builder/issues/1375) · [Pilot procedure and rubric](../../AI_CONTRIBUTION_EVALUATION.md)

## First dry-run candidate

Replay [#1349](https://github.com/HHS/simpler-grants-pdf-builder/pull/1349) from its merge commit's parent, `56699bed09d816a5f26ff8897bef57059ea17dc6`. The parent contains the existing import-rule instructions. This candidate was checked by inspecting Git history. The replay and test execution are pending.

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
