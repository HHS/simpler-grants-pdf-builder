<!-- Contribution workflow: documentation/CONTRIBUTION_WORKFLOW.md. Use a Conventional Commit title (fix:, feat:, docs:, ...) and squash and merge. -->

## Summary

<!-- What does this PR do, and why? -->

## Test plan

<!-- How did you verify this works? -->

## Checklist

- [ ] Documentation follows the [placement rules](../documentation/README.md#where-documentation-belongs): existing guides reused where appropriate, issue-specific evidence filed together, and indexes/links updated; rechecked after review changes (or no documentation changes).
- [ ] Tests pass locally (`make test`)
- [ ] [Editor Tasks](../documentation/EDITOR_TASKS.md) reviewed: affected instructions updated in this PR, or the PR explains why no update is needed (see [maintenance rule](../AGENTS.md#keep-editor-tasks-current)). Rechecked after review changes before merging.
- [ ] If this PR adds, removes, or changes an **import rule** (behavior in `nofos/nofos/nofo.py`, `nofos/nofos/utils.py`, `nofos/nofos/import_transforms.py`, `nofos/nofos/nofo_markdown.py`, `nofos/nofos/policy_language.py`, `nofos/nofos/pdf_metadata.py`, or `nofos/composer/models.py::extract_variables`), [`documentation/IMPORT_RULES.md`](../documentation/IMPORT_RULES.md) has been updated to match (see [DEPLOYMENT.md § Updating Import Rules](../DEPLOYMENT.md#updating-import-rules))
