# Subsection save conflicts: before and after

Review evidence for issue #1075 and PR #1076. Captured October 8, 2026,
using fictional NOFO content and a local demo account.

## Normal subsection editing

Opening the subsection editor retains the existing editing layout and Save
subsection action. The version token is hidden; there is no new confirmation
step during ordinary editing.

| Before | After |
| --- | --- |
| ![Original subsection editor](before-edit.jpg) | ![Updated subsection editor](after-edit.jpg) |

## Saving a stale tab

The demo opens two forms for the same subsection. Tab A corrects the application
link and removes the bullet from the table caption, then saves. Tab B adds a
20-page narrative limit to its older text, then tries to save.

**Before:** the save succeeds and returns to the main NOFO edit page. The old
link and bulleted caption replace Tab A's corrections, without a warning.
The screenshot is the resulting NOFO page; its layout is not changed by this PR.

![Before: stale save silently replaces newer content](before-stale-save.jpg)

**After:** the save is blocked. The subsection page displays the unsaved fields
alongside the latest saved fields, with Review and combine changes as the primary
action and Discard my changes and return as the secondary action. The read-only
content fields can be scrolled and selected to copy longer drafts.

![After: stale save blocked with both versions preserved](after-stale-save.jpg)

## Reviewing and combining changes

This is a new state; the previous editor had no conflict-recovery screen.
Review opens an editable copy of the latest saved version while keeping the
unsaved version alongside it. No write occurs until Save combined version is
submitted. Discard returns without writing.

![After: recovery editor with the preserved draft](after-review.jpg)

## A form opened before deployment

This is also a new state. A submission without the new hidden token displays
“The editor was updated while this page was open” and the same recovery actions.
Its unsaved fields remain available; refreshing is not required to recover them.

![After: missing-token recovery for a predeployment form](after-deployment.jpg)

## Narrow screens

The comparison and recovery columns stack at 390px. The recovery toolbar wraps
within the editor. These are the new states, so no corresponding old mobile
conflict screen exists.

| Conflict | Review |
| --- | --- |
| ![Conflict on a narrow screen](after-stale-save-mobile.jpg) | ![Recovery editor on a narrow screen](after-review-mobile.jpg) |

## Capture and verification

- Desktop viewport: 1280 × 720; mobile viewport: 390 × 844. Images are full-page
  browser captures with the original application styles and initialized editor.
- Before renders use the parent revision's exact subsection template and
  `NofoSubsectionEditView.form_valid` handler, with the same common application
  shell and fixture as the after renders. After renders use commit `fc14e6d2`.
- Captures use rendered Django responses from an authenticated test client,
  served locally with the application's static assets. No production NOFOs,
  user data, credentials, or session-cookie values appear in these images.
- The reproduction asserts that the baseline stale POST redirects and overwrites
  the subsection; the protected stale POST returns HTTP 409 and retains Tab A's
  saved content. Review returns HTTP 200 without saving. A missing-token POST
  returns HTTP 409 with the submitted draft preserved.
