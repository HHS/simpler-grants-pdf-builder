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

## Follow-up verification of current PR revision

October 6, 2026, PR head `cf1ef36915dca1388101b0455673185298c17bf8`:

- An independent code-review agent found no actionable blocking findings and
  reran all 79 focused Django tests successfully. This was not deployed-environment
  or production PostgreSQL verification. CI on that revision passed the test,
  image-build, title and security scan jobs.
- Chrome's native print preview showed a two-page report including all five
  metrics. The macOS save sheet stayed disabled, even in a writable test folder;
  that native file-dialog save is still unverified, not an established app defect.
- Exported the actual report through Chrome's `Page.printToPDF` interface. The
  resulting two-page, 50,819-byte PDF contains all five metric labels/values,
  reliability/scope explanations and expanded calculation notes. Both pages
  were rendered and visually checked: no blank pages or clipped content.
- All data is synthetic. Local authenticated uploads were disabled again after
  verification. No shared environment was changed.

Evidence: [native preview](native-print-preview.png),
[exported PDF](report-exported.pdf), [page 1](report-pdf-page-1.png),
[page 2](report-pdf-page-2.png). Older screenshots above predate the branding fix;
this follow-up records the latest reviewed application revision.

## Revised upload page

The upload page now leads with a short introduction and the existing shared
“Drag file here or choose from folder” component. Essential sharing/temporary
processing information stays visible before submission. Supporting content uses
USWDS accordions titled “How we handle your PDF” and “PDF requirements.” OCR is
spelled out on first use; the original help wording is below the form. Privacy
and feedback links retain external-link decoration and new-tab announcements.
The shared template applies this presentation to both upload routes.

Screenshots show the actual Django template and repository CSS/JavaScript,
rendered locally with synthetic context and recording enabled to include that
notice. This screenshot pass did not use a live account or upload a document.
Desktop (1440px) and mobile (390px) layouts were visually reviewed; both accordion
buttons opened/closed their content, the existing USWDS file-picker initialized,
and the mobile page had no horizontal overflow. All 35 public/authenticated page
tests passed. No shared switches or operational settings were changed.

- [Revised upload page](upload-revised.png)
- [Expanded supporting information](upload-revised-details.png)
- [Mobile upload page](upload-revised-mobile.png)

### Lightweight contextual help correction

Replaced the two boxed USWDS accordions with native `details`/`summary`
disclosures, matching the approved mockup's Additional Info appearance. This is
local contextual-help styling, not an imported VA web component. Essential upload
requirements and sharing notice remain visible. Regenerated all three revised
screenshots; desktop/mobile disclosure interaction and containment checks passed,
as did the 35 public/authenticated page tests.


### Revised pilot usage dashboard

Simplified the summary and outcome labels, moved contextual guidance above the
source filter, and replaced long time-series tables with bounded daily/weekly
charts. Data disclosures match the existing metrics dashboard and expand for
printing, then restore their prior state. Missing observations remain unknown.

- [Revised dashboard](metrics-revised.png)
- [Mobile dashboard](metrics-revised-mobile.png)

These screenshots render the actual Django template with repository assets and
synthetic context, without a live account or uploaded document. All 34 focused
metrics/authenticated-pilot tests passed. Browser checks verified chart rendering,
disclosures, print-state restoration, and mobile containment without JavaScript
errors. Deployed data and operational settings were not exercised.
