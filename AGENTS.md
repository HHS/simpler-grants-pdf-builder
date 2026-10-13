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
