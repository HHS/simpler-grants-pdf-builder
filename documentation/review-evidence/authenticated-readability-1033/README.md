# Authenticated PDF readability verification

Local verification on October 6, 2026 for #1033. All accounts and PDF fixtures
were synthetic. No real NOFO, participant account, or shared environment was
used or changed. This is implementation evidence, not deployed-pilot sign-off.

## Browser checks

Chrome against an isolated SQLite-backed local Builder at port 8895:

- Signed-out access redirects to the existing login page.
- An explicit pilot participant can upload the supported synthetic PDF, receive
  the existing report, copy its metrics, and use Analyze another PDF without
  leaving the authenticated route.
- The unsupported fixture produces a focused, useful error summary.
- A participant without metrics permission cannot view the dashboard. A
  metrics-only account cannot open the upload workflow.
- All and Authenticated show the two successful uploads and one unsupported
  upload. Public has no attempts. These internal test users are included.
- The public route remains unavailable while the authenticated flag is on.
  Turning the authenticated flag off makes its approved-user route unavailable.
  Both upload flags were left off in the local runtime after testing.
- Print-media emulation preserves all report metrics and calculation notes,
  removes report actions, and preserves the dashboard's selected-source label
  while hiding its filter controls. Screen-media emulation was restored.

The print button triggered the browser print flow, but the native dialog
interrupted browser automation. No newly saved PDF or paginated native print
preview was verified in this run. Print/save code is reused without changes.
The tiny supported fixture checks workflow behavior, not metric accuracy for a
representative real NOFO.

## Screenshots

- [Upload and recording notice](upload.jpg)
- [Existing report and successful copy action](report.jpg)
- [Unsupported document](unsupported.jpg)
- [Authenticated source dashboard after disabling the local upload flag](metrics-authenticated.jpg)
- [Report print styles](report-print-styles.jpg)
- [Dashboard print styles](metrics-print-styles.jpg)
- [Authenticated disabled state](authenticated-disabled.jpg)

## Automated checks

The focused suite covers authorization before analysis, group grant/revoke,
independent switches, CSRF (including disabled POST), expected and unexpected
failures, exactly-once recording, failed database writes, independent retention,
source attribution and historical backfill, dashboard HTML/JSON/pagination,
separate cleanup, and sanitized request/framework logs.

Tests use the existing local `codex-word-882:sep30` runtime image, Python 3.14,
SQLite, and its installed dependencies. CI must also verify the current locked
dependency installation; these local runs are not a new production-image build.

- 79 focused Django tests passed.
- 53 existing JavaScript tests passed.
- Full Django suite: 2,364 tests passed, with two skips.
- Black and isort checks passed for all changed Python files.
- Migration drift check passed; all migrations applied on a fresh local DB.
- `git diff --check` passed.

## Shared-environment handoff

The implementation does not approve a retention window, configure scheduled
cleanup, provision real participants, enable either shared pilot, or verify
deployed isolation/edge logging. Follow
[the operating instructions](../../AUTHENTICATED_PDF_READABILITY_PILOT.md) for
environment-specific checks. These are distinct from implementation acceptance
and the later participant validation round.
