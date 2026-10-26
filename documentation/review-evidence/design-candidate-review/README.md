# Synthetic candidate review evidence

October 20, 2026. Invented local documents only, stacked on the candidate-only
interface. This is a partial #1148 slice, not an acceptance or operating approval.

## Checks

- Independent code review found no blocking issues and independently passed all
  52 combined review, transport/concurrency, host and kernel tests.
- Parent focused rerun passed all 52 tests. These cover attribution, immutable
  retries, stale design/render/finding evidence, blockers that cannot be
  acknowledged, diagnostic failures, ownership/group/CSRF, escaped text and
  disabled capabilities. No PDF/network call is required.
- Independent guide/task review found no blocker. Two minor instruction fixes
  were applied: counts belong to the summary alert; copy unsaved reasons before
  submitting rather than after the recovery page has replaced the form.
- Migration 0156 applied to the isolated SQLite database. Full-suite results and
  final migration/format checks are recorded in the PR.

## Chrome walkthrough

1. Loaded an existing synthetic table-heavy candidate. The report identified
   an existing heading diagnostic and retained the source/import and asset/link
   verification blockers. Optional HTML was available; PDF remained disabled.
2. Followed **Review affected section**. Chrome expanded the relevant read-only
   section and showed all ten table rows and the ordered submission list.
3. Added a clearly labeled invented warning for this exercise in the scratch
   database. Submitted a human acknowledgment through the actual browser form.
   The page showed the local synthetic user's identity, timestamp and reason;
   the warning count became zero while all three blockers remained.
4. Changed the theme using the ordinary pilot form. The revision and design
   change count changed, and the warning required acknowledgment again. The old
   acknowledgment was not applied to the new revision.
5. At 390 pixels, the warning form and button remained usable and the document
   width was 390 pixels, without horizontal overflow. Reset the viewport after
   capture. New section headings match existing Theme/Cover headings:
   Merriweather Web, 21.44 pixels, weight 700. The alert heading uses Source Sans
   Pro Web at 23.36 pixels, weight 700, following the shared alert pattern.

Screenshots contain invented content and no credentials. The warning was seeded
for the exercise; it is not evidence that the source generated that warning.

![Review summary after acknowledgment](review-summary.jpg)

![Attributed acknowledgment](warning-acknowledged.jpg)

![Warning requires review after a new revision, narrow screen](warning-new-revision-narrow.jpg)

## Limits

No acceptance/rejection/deletion, production transfer, substantive content edits,
real documents, model runtime, provider calls or DocRaptor/PDF were exercised.
Source-to-import and complete asset/link fidelity remain explicitly not assessed.
Passing diagnostics do not prove accessibility or design completion. Historical
render archives and attribution for earlier presentation edits are not implemented.
The full #1148 walkthrough and acceptance criteria remain open.

## October 26 review follow-up

Resolved the branch's conflicts with current main, preserving the candidate-access
status UI, outside-edit recovery and HRSA cover policy. Migration 0158 joins the
review-decision branch with main's tool-access/history migration branch. An
isolated scratch SQLite upgrade from main's migration 0157 through the new review
table and merge migration succeeded; the drift check reports no changes.

The import-to-review regression test constructs a real synthetic DOCX with an
unmapped paragraph style. The installed converter emits a formatting warning;
the normal upload/import path retains its source and content, exposes a
nonblocking review finding, and allows an owner acknowledgment with actor, time
and reason. No warning or converter output is injected or mocked. Acknowledging
that warning leaves the blocking findings unchanged. Strict import rejection is
disabled only for this test so it exercises the nonblocking import path.

Rejected acknowledgment forms now retain the explanation. A current form is
prefilled only when the exact warning ID and evidence are unchanged and still
unacknowledged. Changed/removed/already-acknowledged warnings retain the old text
separately for copying. Render/database errors retain it on the recovery page.
No decision is recorded until an explicit valid submission. Drafts exist only
in the returned response and are escaped; they are not saved in a session or
decision record. The guide and Editor Task describe recovery and refresh limits.

- Final full Django suite after syncing main: 2,901 tests passed, three existing
  skips. Focused review/transport/host/kernel suite: 65 tests passed.
- JavaScript suite: 61 tests passed.
- Changed Python files pass Black/isort; diff and commit hooks pass.
- Recovery tests cover stale design revisions with fresh form fields, explicit
  resubmission, changed warning evidence, escaped text and render/database errors.
- Chrome checked actual Django-rendered recovery responses with synthetic warning
  text at 1440 and 390 pixels: no horizontal overflow. These captures use local
  static assets and remove CSRF input values; no keys or cookies are captured.
  They verify rendered responses, not a live-agent run or a real-document review.
- Findings/Theme/Cover headings match at 21.44 pixels and weight 700. The new
  alert uses the existing 23.36-pixel, weight-700 style. Chrome confirms the actual
  rendered Merriweather and Source Sans Pro web fonts.

Stale-form explanation and current warning form:

![Explanation retained after a stale submission](stale-review-explanation.jpg)

![Unchanged warning retains the explanation for explicit resubmission](retained-warning-form.jpg)

Changed warning retains the old explanation separately at 390 pixels:

![Changed warning with a separate unsaved draft](changed-warning-draft-narrow.jpg)
