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

### 3. CI must pass

The Django CI workflow (`.github/workflows/django_ci.yml`) runs the full test suite:

```bash
poetry run python manage.py test
```

The PR cannot be merged until this check passes.

### 4. Merge

Once CI is green, you can merge your own PR. No human approval is required. The allowed merge methods are merge commit, squash, and rebase.

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

If a fix needs to bypass the normal PR flow (e.g. a critical production bug), use `[Hotfix]` in the PR title in lieu of an issue number. CI must still pass before merging.

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
