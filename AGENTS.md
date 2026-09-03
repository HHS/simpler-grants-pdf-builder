# AGENTS.md

Guidance for AI coding agents (Claude Code, Codex, etc.) working in this repository.

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

See `DEPLOYMENT.md` for the full contribution workflow, branch protection rules, and the hotfix
title convention.
