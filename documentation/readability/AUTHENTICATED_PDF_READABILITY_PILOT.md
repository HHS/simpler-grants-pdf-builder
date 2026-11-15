# Signed-in Readability Checker access

Signed-in Builder users use the same Readability Checker as everyone else, at the
unlinked `/readability-checker/` URL. There is no separate signed-in route and no
per-user pilot permission. Two Constance switches decide who can upload, and the
usage label records whether the person was signed in.

This page keeps its original file name so existing links still work. Issue #1033
added a restricted `/nofos/readability-checker/` route for approved pilot
participants. Issue #1367 retired that route and its permission. The original
pilot record is in the
[authenticated readability evidence](../review-evidence/authenticated-readability-1033/README.md).

The [Readability Checker guide](PDF_READABILITY_PILOT.md) covers supported
documents, limits, the report and public operations. This page covers what is
specific to signed-in users.

## Who can use the checker

| `HHS_NOFO_PDF_METRICS_PILOT_ENABLED` (public) | `HHS_NOFO_AUTHENTICATED_PDF_METRICS_PILOT_ENABLED` (signed in) | Who can upload |
|---|---|---|
| On | Either | Everyone |
| Off | On | Any active, signed-in Builder user |
| Off | Off | No one |

Both are default-off Constance settings, so changes take effect without a
restart. The signed-in switch has no effect while the public switch is on.

When someone can't upload, GET serves the unavailable page with 200 and POST
returns it with 403. The decision uses only the session and the two switches, so
it happens before CSRF processing, multipart parsing or analysis. Disabled POSTs
record outcome `disabled` with the uploader's label.

Signed-in access needs no group or permission. Migration 0164 deleted
`nofos.use_pdf_readability_pilot`, the **PDF readability pilot participants**
group and the **Can use PDF readability pilot** checkbox. Deleting the permission
also removed it from every user and group that held it. Reversing the migration
recreates an empty group; former memberships are not restored.

## Header

The checker header matches the Builder header's account item:

- Signed out: a **Login** link to `/users/login/?next=/readability-checker/`.
  After password sign-in, the user returns to the checker.
- Signed in: the user's email, linking to their account page.

The header nav is hidden when printing, so the email doesn't appear on printed or
saved reports. It doesn't show **All NOFOs** or admin links.

## Word comparison save

[Word comparison save](WORD_COMPARISONS.md) appears after a Word analysis for
signed-in users with `nofos.manage_word_comparisons` while
`HHS_NOFO_WORD_COMPARISONS_ENABLED` is on. Signed-out users and signed-in users
without the permission never see it.

## Old URLs

`/nofos/readability-checker/` and `/nofos/readability/` permanently redirect (301)
to `/readability-checker/` in one hop, for signed-in and signed-out visitors. The
redirect never forwards an upload: a POST from a page left open across the change
is answered without reading its body, and the browser loads an empty form. These
paths keep the sanitized readability request logging, because a stale form can
still send an upload to them.

`/nofos/readability-checker/comparisons/save` and the usage pages under
`/nofos/metrics/` are unchanged.

## Usage labels and recording

The usage label records whether the person was signed in when they uploaded:

- `authenticated`: signed in
- `public`: not signed in
- `unknown`: historical rows with no established source; new records don't use it

Before #1367, `authenticated` meant uploads through the restricted pilot route,
and `public` included signed-in people who used the public page. The
[usage page](PDF_READABILITY_PILOT.md#content-free-outcome-monitoring-985) notes
this change.

Each label has its own environment settings, read at startup:

| Label | Recording | Retention |
|---|---|---|
| `public` | `PDF_READABILITY_ATTEMPT_RECORDING_ENABLED` (default off) | `PDF_READABILITY_ATTEMPT_RETENTION_DAYS` (unset) |
| `authenticated` | `AUTHENTICATED_PDF_READABILITY_ATTEMPT_RECORDING_ENABLED` (default off) | `AUTHENTICATED_PDF_READABILITY_ATTEMPT_RETENTION_DAYS` (unset) |

Set both recording switches as intended in each environment. If only one is on,
the other group's uploads aren't recorded. The page's privacy notice uses the
same label as the recorded attempt, so it shows the retention that applies to
that person.

Content-free usage records have no automatic expiration; leave both retention
settings unset. See the
[retention decision](PDF_READABILITY_PILOT.md#content-free-outcome-monitoring-985).
If a future decision adds expiration, configure a positive window and schedule
the source-specific cleanup command:

```text
python manage.py cleanup_pdf_readability_attempts --source authenticated --dry-run
python manage.py cleanup_pdf_readability_attempts --source authenticated
```

Default cleanup targets public and legacy/unknown rows using public retention.
Explicit `--source unknown` targets unknown only. Authenticated cleanup uses its
own window and can't delete public or unknown rows.

Stored facts are timestamp, label, attempted file category (PDF, DOCX or
unknown), fixed outcome code, HTTP status and duration. There is no filename,
document text, metric value, IP, account or session ID, or raw exception. Upload
request logs omit user IDs for signed-in users.

## Infrastructure

Builder deployment infrastructure lives in
[HHS/simpler-grants-gov](https://github.com/HHS/simpler-grants-gov).

- `infra/nofos/app-config/prod.tf` sets
  `AUTHENTICATED_PDF_READABILITY_ATTEMPT_RECORDING_ENABLED = "true"`. Check
  whether `PDF_READABILITY_ATTEMPT_RECORDING_ENABLED` should also be on in prod.
- The WAF upload rate limit and emergency block in
  `infra/modules/service/waf.tf` match `/readability-checker/` and
  `/readability/`, so they now apply to signed-in uploads too. The prod limit
  stays at 30 upload POSTs per IP per 5 minutes. The emergency block now also
  blocks signed-in users; to keep signed-in access while the public checker is
  off, use the Constance switches instead.

## Rollout and rollback

1. Deploy the revision with migration 0164. Confirm the pilot group and the
   **Can use PDF readability pilot** checkbox are gone.
2. Confirm both recording settings are set as intended.
3. Check the switches. With public off and signed-in on, a signed-in user can
   upload, a signed-out visitor sees the unavailable page with the Login link,
   and `/nofos/readability-checker/` redirects to `/readability-checker/`.
4. Check that a signed-in upload appears under the Authenticated filter at
   `/nofos/metrics/readability-checker-usage`.

Local screenshots and checks for this change are in the
[#1367 evidence](../review-evidence/1367/README.md).

Switch changes take effect immediately, without a deployment:

- To pause all uploads, turn off both `HHS_NOFO_PDF_METRICS_PILOT_ENABLED` and
  `HHS_NOFO_AUTHENTICATED_PDF_METRICS_PILOT_ENABLED`. While the public switch is
  on, everyone can upload whatever the signed-in switch is set to; while the
  signed-in switch is on, signed-in users can still upload.
- To pause only signed-out uploads, turn off the public switch and leave the
  signed-in switch on.

Rolling back the application restores the old route and an empty pilot group;
reassign participants manually.
