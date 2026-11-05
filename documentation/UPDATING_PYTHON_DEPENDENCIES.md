# Updating Python dependencies

The NOFO Builder uses [Poetry](https://python-poetry.org/) to manage Python dependencies.

This guide covers the recommended process for routine dependency updates as well as major version upgrades.

Python dependencies should be updated **once a week**. The vulnerability scanner used in the deployment pipeline will block deploys if outdated or vulnerable packages are detected, so keeping dependencies current is necessary to keep the app deployable.

---

## Prerequisites

- Poetry installed and configured
- The application running locally
- Access to the `./nofos` directory within the project
---

## Routine updates (minor and patch versions)

### 1. Check for outdated dependencies

```bash
poetry show --outdated
```

This lists all outdated packages, including direct dependencies defined in pyproject.toml and nested (transitive) dependencies. Typically only about one-quarter to one-third of the listed packages are direct dependencies — the rest are managed transitively.

### 2. Update pyproject.toml

For minor and patch version bumps, update the relevant version constraints in pyproject.toml. These updates are generally safe to apply without detailed review, but always verify against any known breaking changes in the package's changelog if uncertain.

### 3. Update the lock file

```bash
poetry update
```

This resolves and updates all locked dependency versions in poetry.lock, including transitive dependencies.

### 4. Run the test suite

From the `./nofos` directory, run the full Django test suite:

```bash
poetry run python manage.py test
```

All tests must pass before proceeding.

---

## Manual smoke test

After automated tests pass, verify the application behaves correctly end-to-end by running it locally and completing the following steps:

1. Start the application.
2. Log in.
3. Import a NOFO document. A sample NOFO document ([Kansas.docx](https://docs.google.com/document/d/1I6qyltZ1gqtYqkV74iPlqgD7WdoWswf9/edit?usp=drive_link)) is available for Agile Six team members to use.
4. Open the imported NOFO.
5. Review the HTML rendering and confirm the content appears complete and correct.

This step helps catch issues that automated tests may not surface — such as large sections of content failing to import or render. For a more precise comparison, capture the HTML output of an imported document before and after the update and compare the two using a diff tool.

---

## When a container vulnerability scan blocks a deployment

A passing application test suite does not establish that the container runtime
is free of known vulnerabilities. A new advisory or scanner database update can
block a build of an otherwise unchanged commit. Updating `poetry.lock` alone does
not update the Python interpreter installed by the Docker base image.

Use the following assessment before proposing a temporary scanner exception.
These are review recommendations, not an approved exception or a substitute for
the project's security risk-acceptance process. For reporting a newly suspected
application vulnerability, follow [SECURITY.md](SECURITY.md), rather than posting
sensitive findings or exploit details in a public issue or PR.

### Establish the blocker and available fix

1. Record the failed workflow, commit, image tag/digest, installed package and
   runtime versions, CVE, severity cutoff, and scanner version/database details
   where available. Distinguish the finding that fails the cutoff from lower
   severity findings also listed in the report.
2. Read the vendor advisory and check maintained runtime branches, backport
   status, released versions, and official base-image availability. A scanner's
   “fixed in” field alone does not establish a usable, supported upgrade path.
3. Prefer a supported patched runtime or dependency and rebuild/re-scan the
   resulting image. Do not switch Python minor versions or adopt a prerelease
   solely to clear a finding without compatibility testing.

### Assess application exposure

Trace whether attacker-controlled values can reach the affected API in the
actual deployed dependency stack. Identify existing validation, authentication,
network restrictions, and relevant third-party library behavior. Separate
verified protections from assumptions; document what remains untested.

For hostname/port handling advisories, inspect outbound request paths such as
Builder's external-link checker (`_update_link_statuses` in
[nofos/nofo.py](../nofos/nofos/nofo.py)). It uses Requests and follows redirects.
A review should establish how malformed host/port values and redirects are
handled through Requests, urllib3, and the runtime, rather than assuming that
a URL library either exposes or blocks the vulnerable socket behavior.

Use isolated local tests, synthetic inputs, and controlled destinations; do not
probe production or internal services. Verify that malformed destinations cannot
cause an unintended connection. Absence of a reproduced exploit is not proof of
non-exposure. Keep sensitive findings in the approved reporting channel.

### If proposing a temporary exception

An exception permits deployment with a known finding still present; it does not
patch the vulnerability. Low exploit-prediction scores and passing functional
tests are supporting context, not sufficient evidence of acceptable exposure.

The proposal should record:

- The exact CVE and affected package/runtime, and the narrowest supported match
  scope. Avoid a broad severity-threshold change or disabling the scanner.
- The reason a supported fix cannot yet be deployed, the application exposure
  assessment, compensating controls, unverified assumptions, and residual risk.
- The risk-acceptance decision and responsible approver under the project's
  security process, plus a named owner and a concrete review/expiry date.
- A removal condition: a supported patched runtime/base image is available,
  compatibility checks pass, and the rebuilt image passes a scan without the
  exception. Reassess sooner if exploitation or exposure information changes.

Do not add an exception based only on this guide. Obtain the required
risk-acceptance decision first. A documented review date does not automatically
expire a scanner configuration entry; the owner must track and remove it.

Builder's [.grype.yml](../.grype.yml) says its exceptions mirror the deployment
repository's [.grype.yml](https://github.com/HHS/simpler-grants-gov/blob/main/.grype.yml).
Coordinate additions and removals in both repositories so PR and deployment scans
apply the intended policy. Verify the configuration used by each workflow,
including whether its bypass-ignore mode drops per-CVE entries. Retain the
existing severity cutoff and other scan checks.

After an approved change, rebuild and scan the intended deployment image, record
the results and remaining findings, and follow the normal
[deployment workflow](../DEPLOYMENT.md#production). Do not assume an exception
change will affect a workflow checking out an older immutable commit; confirm
which revision supplies both the image and scanner configuration.

---

## Major version updates

Major version updates require additional care and should be handled separately from routine patch and minor updates.

Update one dependency at a time. After each individual major version update:

```bash
poetry update <package-name>
poetry run python manage.py test
```

Then start the application locally and repeat the manual smoke test.

Avoid batching multiple major version updates in a single change. Updating one package at a time makes it easier to isolate the cause if a test failure or regression occurs.

---

## Pre-merge checklist

Before opening or merging a pull request, confirm all of the following:

- [ ] poetry.lock reflects the intended updates
- [ ] The full test suite passes
- [ ] The application starts successfully
- [ ] A NOFO can be imported without errors
- [ ] The imported NOFO renders correctly after a quick visual review

If any of these checks fail, either resolve the issue before merging or revert the dependency that introduced the problem.

---

## Contributing

Once your dependency updates are ready and the checklist above is complete, open a pull request targeting main. For details on the contribution workflow, CI requirements, and how changes get deployed to production, see [DEPLOYMENT.md](../DEPLOYMENT.md).
