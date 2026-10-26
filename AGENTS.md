# AGENTS.md

Guidance for AI coding agents (Claude Code, Codex, etc.) working in this repository.

Follow the workflow in [`documentation/CONTRIBUTION_WORKFLOW.md`](documentation/CONTRIBUTION_WORKFLOW.md):
issue, branch, PR with a Conventional Commit title, CI, then squash and merge. It links to what to
read at each step and lists the rules that apply only to agents.

## PR titles must follow Conventional Commits

Every PR title must start with a type prefix — `feat:`, `fix:`, `chore:`, `docs:`, `refactor:`,
`test:`, `ci:`, etc. — per [Conventional Commits](https://www.conventionalcommits.org/). This is
checked by `.github/workflows/pr_title_lint.yml` (advisory only, not a required check).

[release-please](https://github.com/googleapis/release-please) does not read the PR title — it
reads the commit message(s) that actually land on `main`. This repo allows squash and rebase
merges (merge commits are disabled): under squash, GitHub sets the resulting commit's message to
the PR title, so a conventional title is what determines categorization; under rebase, each
individual commit lands as-is and must itself be conventional, or the PR can silently disappear
from CHANGELOG.md despite a valid title. If that happens, add a `BEGIN_COMMIT_OVERRIDE` /
`END_COMMIT_OVERRIDE` block to the merged PR's description to fix it retroactively.

**Always squash and merge.** Don't rebase-merge, even though the repository allows it.

See `DEPLOYMENT.md` for the full contribution workflow, branch protection rules, and the hotfix
title convention.

## Documentation belongs in `documentation/`

Put repository documentation in the top-level `documentation/` directory. Do not create a
top-level `docs/` directory. Add durable guides to `documentation/README.md`; use
`documentation/adr/` for architecture decision records and `documentation/review-evidence/` only
for PR-specific screenshots and validation notes.

## Keep editor tasks current

When a change affects how someone imports, edits, reviews, previews, or exports a NOFO,
review [`documentation/EDITOR_TASKS.md`](documentation/EDITOR_TASKS.md) and update affected
tasks in the same PR. This includes changes to labels, navigation, permissions, prerequisites,
warnings, recovery steps, and automatic behavior that affects the task's outcome. Add a task
when an uncovered workflow needs instructions; preserve existing task IDs and anchors.

Check this before opening the PR and recheck against the final behavior after review changes,
before merging. In the PR checklist, confirm the instructions were updated or explain why no
update is needed. Routine internal changes with no effect on editor instructions need only a
brief explanation; they do not require a documentation edit.

## Runtime feature switches

If a feature should be enabled or disabled by an administrator after deployment,
manage its switch through Django Constance and read it through `constance.config`
when the behavior runs. Do not require an environment change or worker restart
for an operational feature toggle.

- Default new optional features to disabled.
- Explain the effect and any enablement prerequisites in the admin help text.
- If an environment variable supplies the initial default, document that a saved
  Constance value takes precedence.
- Test both states and verify that changing the switch takes effect without
  restarting workers.
- Update rollout, rollback, and affected editor instructions in the same PR.

Keep credentials, infrastructure configuration, and settings that must be fixed
at application startup in environment-based settings. Do not expose them through
Constance. A feature switch does not replace permission checks or required data
preparation.

## UI patterns

Before adding or changing user-facing UI, read
[documentation/UI_PATTERNS.md](documentation/UI_PATTERNS.md) and reuse relevant
shared components and typography utilities. On editor pages that load Bootstrap,
check computed heading/alert styles and actual rendered fonts against an existing
Builder page; stylesheet loading alone does not prove the typography matches.
Extend the catalog when introducing another verified pattern; do not assume
undocumented screens follow it.

## Word export safety

Do not test GrabzIt Word export from a non-production environment using production credentials.
`GRABZIT_WORD_EXPORT_ALLOWED_HOSTS` is enforced server-side; keep it empty outside production until
that environment has dedicated GrabzIt credentials. See `DEPLOYMENT.md` § Word export environment
isolation. Never include credential or authentication-cookie values in source control, logs,
screenshots, issues, or pull requests.

## NOFO import rules

This repo automatically transforms content on NOFO import (`.docx`/HTML upload) — footnote/endnote
handling, list/table repair, link cleanup, metadata suggestion, and more. Every one of these rules
is cataloged with a stable ID in `documentation/IMPORT_RULES.md`.

**Before changing behavior in any of these files, read that document. After changing it, update
the matching entry in the same change:**

- `nofos/nofos/nofo.py`
- `nofos/nofos/utils.py` (the Mammoth style map)
- `nofos/nofos/import_transforms.py`
- `nofos/nofos/nofo_markdown.py`
- `nofos/nofos/policy_language.py`
- `nofos/nofos/pdf_metadata.py`
- `nofos/nofos/endnotes.py`
- `nofos/composer/models.py` (`extract_variables`)

See `DEPLOYMENT.md` § Updating Import Rules for the full contribution policy.
