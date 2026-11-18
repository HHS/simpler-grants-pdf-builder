<!-- Contribution workflow: documentation/CONTRIBUTION_WORKFLOW.md. Use a Conventional Commit title (fix:, feat:, docs:, ...) and squash and merge. -->

## Summary

<!-- What does this PR do, and why? -->

## Test plan

<!-- How did you verify this works? -->

## UI evidence

<!-- For visible UI changes, embed before-and-after screenshots of the same screen and interaction state using synthetic or approved data. Store any screenshots committed to the repository under documentation/review-evidence/<issue-number>/. If you could not capture screenshots, explain why and describe how you verified the visible change. -->

## Checklist

- [ ] Documentation follows the [placement rules](../documentation/README.md#where-documentation-belongs): existing guides reused where appropriate, issue-specific evidence filed together, and indexes/links updated; rechecked after review changes (or no documentation changes).
- [ ] Tests pass locally (`make test`)
- [ ] [Editor Tasks](../documentation/EDITOR_TASKS.md) reviewed: affected instructions updated in this PR, or the PR explains why no update is needed (see [maintenance rule](../AGENTS.md#keep-editor-tasks-current)). Rechecked after review changes before merging.
- [ ] If this PR adds, removes, or changes an **import rule** (behavior in `nofos/nofos/nofo.py`, `nofos/nofos/utils.py`, `nofos/nofos/import_transforms.py`, `nofos/nofos/nofo_markdown.py`, `nofos/nofos/policy_language.py`, `nofos/nofos/pdf_metadata.py`, or `nofos/composer/models.py::extract_variables`), [`documentation/IMPORT_RULES.md`](../documentation/IMPORT_RULES.md) has been updated to match (see [DEPLOYMENT.md § Updating Import Rules](../DEPLOYMENT.md#updating-import-rules))
- [ ] If this PR changes **Word (DOCX) export** behavior (see the [file list](../documentation/DOCX_EXPORT.md#keeping-this-page-current)), [`documentation/DOCX_EXPORT.md`](../documentation/DOCX_EXPORT.md) has been updated to match, or the PR has the `docs-not-needed` label and explains why no update is needed
- [ ] If this PR introduces an operating division theme, reviewed the [Builder theme checklist](../documentation/SCALABLE_NOFO_DESIGN_SYSTEM.md#builder-implementation-checklist-for-an-opdiv-theme) and recorded the applicable checks in the test plan and UI evidence.
