# AGENTS.md

Guidance for AI coding agents (Claude Code, Codex, etc.) working in this repository.

## PR titles must follow Conventional Commits

Every PR title must start with a type prefix — `feat:`, `fix:`, `chore:`, `docs:`, `refactor:`,
`test:`, `ci:`, etc. — per [Conventional Commits](https://www.conventionalcommits.org/). This is
enforced by `.github/workflows/pr_title_lint.yml` and, more importantly, is what
[release-please](https://github.com/googleapis/release-please) uses to generate CHANGELOG.md
entries (see `release-please-config.json` for the type-to-section mapping). A PR title without a
recognized prefix means the change is miscategorized or silently dropped from the changelog.

See `DEPLOYMENT.md` for the full contribution workflow, branch protection rules, and the hotfix
title convention.
