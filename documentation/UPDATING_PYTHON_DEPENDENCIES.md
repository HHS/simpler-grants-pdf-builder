# Updating Python dependencies

The NOFO Builder uses [Poetry](https://python-poetry.org/) to manage Python dependencies.

This guide covers the recommended process for routine dependency updates as well as major version upgrades.

Python dependencies should be updated **once a week**. The vulnerability scanner used in the deployment pipeline will block deploys if outdated or vulnerable packages are detected, so keeping dependencies current is necessary to keep the app deployable.

---

## Prerequisites

- Poetry installed and configured
- The application running locally
- Access to the /nofos directory within the project

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

From the /nofos directory, run the full Django test suite:

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

Once your dependency updates are ready and the checklist above is complete, open a pull request targeting main. For details on the contribution workflow, CI requirements, and how changes get deployed to production, see [DEPLOYMENT.md](./DEPLOYMENT.md).
