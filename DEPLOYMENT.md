# Deployment & Contribution Workflow

This document is intended for engineers onboarding to the [NOFO Builder](https://github.com/HHS/simpler-grants-pdf-builder) repository. It covers how to contribute code, what happens when you open a pull request, and how changes get deployed to production.

---

## Overview

The NOFO Builder follows a trunk-based development model. All work targets the `main` branch via pull requests. Direct pushes to `main` are not permitted.

Production deployments are triggered manually via GitHub Actions in a separate, related repository: [HHS/simpler-grants-gov](https://github.com/HHS/simpler-grants-gov).

---

## Branch Protection Rules

The `main` branch has the following rules enforced:

- **No direct pushes** — all changes must go through a pull request
- **No force pushes** — rewriting history on `main` is not permitted
- **No branch deletion**
- **CI must pass** — the `ci` status check must succeed before a PR can be merged
- **No required reviewers** — you can merge your own PR once CI is green

---

## Contribution Workflow

### 1. Create a feature branch

Branch off of `main` and name your branch descriptively. There is no enforced naming convention in this repo, but aim for something like:

```
[your-handle]/[short-description]
```

### 2. Open a pull request

Open a PR targeting `main`. CI will run automatically on every PR.

**PR titles must follow [Conventional Commits](https://www.conventionalcommits.org/)** — start the title with a type prefix, e.g. `feat: ...`, `fix: ...`, `chore: ...`, `docs: ...`, `refactor: ...`, `test: ...`, `ci: ...`. This is enforced by `.github/workflows/pr_title_lint.yml` (not a required check, so it won't block merging) and, more importantly, is what [release-please](https://github.com/googleapis/release-please) uses to group merged PRs into CHANGELOG.md entries — see `release-please-config.json` for the type-to-section mapping. A title without a recognized prefix means the change is miscategorized or silently omitted from the changelog.

**This only works reliably under squash merge.** Release-please reads the commit message(s) that actually land on `main`, not the PR title — squash merge is the one method where GitHub sets the resulting commit's message to the PR title, so those line up. Under rebase, your individual commits land as-is; if they aren't themselves Conventional-Commit-formatted, the PR can pass title lint and still be silently missing from the changelog. `pr_title_lint.yml` is advisory only (not a required check) — it nudges toward a good title, but doesn't by itself guarantee correct categorization under rebase. If a PR does go missing from the changelog, you can fix it after the fact: edit the *merged* PR's description to add
```
BEGIN_COMMIT_OVERRIDE
feat: whatever the PR actually did
END_COMMIT_OVERRIDE
```
and release-please will pick it up on its next run — no re-merge needed.

### 3. CI must pass

The Django CI workflow (`.github/workflows/django_ci.yml`) runs the full test suite:

```bash
poetry run python manage.py test
```

The PR cannot be merged until this check passes.

### 4. Merge

Once CI is green, you can merge your own PR. No human approval is required. The allowed merge methods are squash and rebase (merge commits are disabled at the repo level).

---

## Releases

[release-please](https://github.com/googleapis/release-please) keeps a standing PR open with everything merged to `main` since the last release. Merging it isn't just internal bookkeeping — the resulting CHANGELOG.md entry is what users see via the "Latest updates" link in the app footer, so treat merging it as user-facing communication, not busywork to defer.

- **If a `feat:` in the batch improves the user experience**, merge the release PR (and request the corresponding production deploy — see below) as soon as it's ready. Don't wait for a fixed cadence just to sit on something users would benefit from seeing sooner.
- **If the batch is only `fix:`/`chore:`-type changes with no user-visible feature**, there's less urgency — it's fine to let those accumulate and merge on the regular cadence below, or bundle them into the next feature release, whichever comes first.
- **Otherwise, default to a weekly cadence** rather than letting the release PR sit open indefinitely. Merging it only cuts a CHANGELOG.md entry and a git tag — it does not deploy anything by itself (see Deployment below) — so there's no risk in merging promptly.

---

## Deployment

### Development

Merging to `main` does **not** automatically deploy the NOFO Builder to production. However, changes to infrastructure or workflow files may trigger an automatic deploy to the development environment via the `simpler-grants-gov` repository.

### Production

Production deployments are triggered manually. The deploy workflow lives in the [HHS/simpler-grants-gov](https://github.com/HHS/simpler-grants-gov) repository under `.github/workflows/`.

The deployment pipeline:

1. **CI runs** against the specified version
2. **Vulnerability scans** run after CI passes
3. **Deploy** runs only if both above pass, and includes:
   - Publishing the Docker image to the registry
   - Running database migrations
   - Deploying the release to the target environment

### Environments

| Environment | URL | Purpose | Notes |
|-------------|-----|---------|-------|
| `dev` | [nofos.dev.simpler.grants.gov](https://nofos.dev.simpler.grants.gov) | Primary development environment | Auto-deploys on changes to infra/workflow files |
| `staging` | No public URL | Likely unused | Has database and full infrastructure but no domain or HTTPS, and is not available as a manual deploy target. Likely created as a pre-prod validation environment but never adopted into the release workflow. Confirm with the team whether this environment is still needed. |
| `training` | [nofos.training.simpler.grants.gov](https://nofos.training.simpler.grants.gov) | Training and onboarding | Currently running a newer Postgres version (17.5) — may be testing a DB upgrade |
| `grantee1` | [nofos.grantee1.simpler.grants.gov](https://nofos.grantee1.simpler.grants.gov) | External stakeholder pilot | Dedicated environment for a specific grantee group |
| `prod` | [nofos.simpler.grants.gov](https://nofos.simpler.grants.gov) | Production | Clean domain, no environment subdomain |

### Monitoring

Each environment exposes a public health check endpoint that requires no authentication:

```GET /health```

This endpoint returns `{"status": "ok"}` with a `200` status code, and supports both `GET` and `HEAD` requests. It is used by UptimeRobot to monitor uptime across environments.

| Environment | Health check URL |
|-------------|-----------------|
| `prod` | `https://nofos.simpler.grants.gov/health` |
| `dev` | `https://nofos.dev.simpler.grants.gov/health` |
| `training` | `https://nofos.training.simpler.grants.gov/health` |
| `grantee1` | `https://nofos.grantee1.simpler.grants.gov/health` |

Live uptime and incident history are tracked on the [UptimeRobot status page](https://stats.uptimerobot.com/fSUIHr8Hva).

To trigger a deploy, a team member navigates to the **Actions** tab in the `simpler-grants-gov` repo, selects **Deploy NOFOs**, and clicks **Run workflow**, specifying the target environment and git ref (branch, tag, or commit SHA).

**Access requirements:** Triggering a production deploy requires admin access to the `simpler-grants-gov` repository. Admin access requires annual completion of HHS' Rules of Behavior (ROB) and Cybersecurity training modules, with certificates of completion on file.

---

## Before You Push

CI must pass before a PR can be merged, so it's worth running checks locally first to catch issues early.

**Run the test suite:**

```bash
make test
```

**Check linting** (without making changes):

```bash
make lint
```

**Auto-format code:**

```bash
make format
```

**Other useful commands:**

```bash
make migrate          # Run database migrations
make makemigrations   # Create new migrations
make showmigrations   # Check DB connection and show migrations
make build            # Build a Docker image
```

**Install pre-commit hooks** (one-time setup, runs formatting checks automatically on every commit):

```bash
poetry run pre-commit install
```

The following are excluded from formatting: static files, migration files, SVGs, and `.crt` files.

---

## Hotfixes

If a fix needs to bypass the normal PR flow (e.g. a critical production bug), prefix the PR title with `fix: [Hotfix] ...` in lieu of an issue number — keep the `fix:` type prefix so the change still categorizes correctly in CHANGELOG.md, with `[Hotfix]` flagging why it skipped the normal flow. CI must still pass before merging.

---

## Key Files

| File | Purpose |
|------|---------|
| `.github/workflows/django_ci.yml` | Runs the test suite on every PR |
| `.github/workflows/main.yml` | Orchestrates CI on PRs and pushes to main |
| `nofos/bloom_nofos/.env.example` | Template for local environment variables |

---

## Related Resources

- [HHS/simpler-grants-gov](https://github.com/HHS/simpler-grants-gov) — monorepo where deploy workflows live
- [DEVELOPMENT.md (simpler-grants-gov)](https://github.com/HHS/simpler-grants-gov/blob/main/DEVELOPMENT.md) — broader development lifecycle documentation
- [Local development setup](./README.md) — how to run the NOFO Builder locally
