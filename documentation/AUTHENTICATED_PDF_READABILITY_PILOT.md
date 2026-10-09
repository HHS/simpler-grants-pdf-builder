# Authenticated PDF readability pilot

Issue #1033 adds a restricted validation route. It reuses the existing PDF
analyzer, temporary files, recognition rules, report, copy action and browser
print/save action. It does not create a NOFO, save metric scores, add report
history or enable public `/readability/` uploads.

## Accounts, permissions and switches

Share `/nofos/readability/` directly. It has no navigation link. Both GET and POST
require an active Builder account and `nofos.use_pdf_readability_pilot`.
Administrators grant this permission through the **PDF readability pilot
participants** group created by migration 0150. Provision accounts through the
existing approved Builder process, then add only approved Agile Six or Gartner
participants. Email domain, OpDiv and sign-in alone do not grant access. Remove
membership and any direct pilot permission to revoke access; deactivate accounts
when required. Existing superuser permission behavior is retained.

To grant access in Django administration, open **Users**, select the participant
(or add their account), check **Can use PDF readability pilot** under
**Permissions**, and save. To revoke access, uncheck that box and save. This only
removes membership in the participant group; any direct permission or other
permission-granting group must also be removed. The form warns when separate
permission grants exist. Superusers retain automatic access. Keep **Can view
metrics** unchecked unless dashboard access is also intended. The participant
checkbox does not enable the pilot feature switch or outcome recording.

This group grants no dashboard permission. Viewing usage still requires
`nofos.view_builder_metrics`, normally through **Metrics viewers**. Dashboard
permission does not grant upload access.

`HHS_NOFO_AUTHENTICATED_PDF_METRICS_PILOT_ENABLED` is a default-off Constance
setting independent of the public flag. Authorized users see an unavailable page
when disabled. Authorized POSTs require CSRF even while disabled. Authentication
and permission checks precede multipart parsing and analysis. The existing size
handler is installed before the nested CSRF check reads the body.

## Supported PDFs and processing

Use text-based HHS NOFO PDFs. Existing configurable recognition checks the first
five pages for NOFO signals such as HHS agency name, opportunity number,
Assistance Listing number and Grants.gov reference. Agency text can replace
agency metadata lost in a print export; two different signal types are still
required. See
[PDF_READABILITY_PILOT.md](PDF_READABILITY_PILOT.md) and
[PDF_READABILITY_SAFEGUARDS.md](PDF_READABILITY_SAFEGUARDS.md).

Limits remain one PDF, 15 MiB, 150 pages, a 15-second bounded analyzer worker and
the existing shared analysis slot. Both routes use the same slot. Unsupported,
uncertain, scanned/no-text, encrypted, malformed, oversized, busy, timeout and
unavailable cases retain their useful messages. Unexpected analyzer failures
return a fixed message and `internal_error`, without exception text or traceback.
Reports retain scope and reliability explanations; PDF and source-native Builder
measurements can differ. Authentication does not establish parser containment.

The upload page shows the existing Word export progress-modal design after browser
validation succeeds, with “Analyzing your PDF…” and the loading animation. It
shows no estimated percentage. The loading modal has no dismissal button.
The report response shows “Your report is ready” with an OK button and closes
automatically after three seconds, matching Word export. Errors replace the
upload page with the existing error message. Submission is
disabled while pending and restored when returning through browser Back.

Missing-file submissions use the shared inline file-upload error state, matching
NOFO Compare: red form-group styling, an error message associated with the file
input, and focus on the inline error. No browser-required tooltip or duplicate
error alert is shown. Empty submissions do not open the analysis progress modal;
server validation still rejects missing and multiple files before analysis.

## Usage, failures and privacy

The existing `/nofos/metrics/readability-pilot` page offers All, Authenticated,
Public and Unknown filters in HTML and JSON. Selected source survives pagination
and is visible in printed output. Its labeled source breakdown covers all
retained rows. Other counts, rates, outcomes, daily/weekly totals, percentiles and
recent attempts use the selected source.

The dashboard leads with attempts, reports returned and unsuccessful uploads.
Daily and weekly charts cover the last 30 days and 12 weeks, including the current
period. Missing retained observations display as No data, not zero usage. The
underlying tables use the existing metrics-page disclosures; printing opens them
and restores their previous state afterward. Full daily/weekly JSON totals remain
available. About these metrics appears above the source filter, while processing
and recording settings remain visible.

Source means the upload route, not the session: a signed-in public-route visitor
still creates a public outcome. Migration 0150 marks existing rows public because
the pre-migration application recorded only that route. New unattributed inserts
default to unknown. Unknown rows appear only in All or Unknown filters.

Authorized POSTs reaching the workflow record one outcome after processing:
success, handled validation/analysis/capacity failure, disabled response, or a
sanitized unexpected workflow failure. GETs, authentication/permission denials,
CSRF failures, malformed requests outside the workflow and upstream/WAF
rejections are not counted. Operational monitoring must cover those. Duration is
workflow processing time, including form parsing and rendering, not pure parser
execution. Recording failure does not prevent a report from being returned.

Stored facts are timestamp, source, fixed outcome code, HTTP status and duration.
There is no filename, document text, metric value, IP, account/session ID or raw
exception. Internal/staging participant activity is included without changing
the main Builder dashboard's OpDiv eligibility or denominators. Both upload
routes have privacy headers and sanitized request/framework logging;
authenticated upload logs omit user IDs. Infrastructure logs remain separate.

Authenticated recording uses independent environment settings:

- `AUTHENTICATED_PDF_READABILITY_ATTEMPT_RECORDING_ENABLED=False` by default.
- `AUTHENTICATED_PDF_READABILITY_ATTEMPT_RETENTION_DAYS` has no default.

Authenticated recording requires only the recording switch. Leave the optional
`AUTHENTICATED_PDF_READABILITY_ATTEMPT_RETENTION_DAYS` unset for this production
pilot: content-free usage records have no automatic expiration. Uploaded PDFs
and document contents are not retained. No authenticated cleanup schedule is
required. This is the pilot's chosen behavior, not a claim about HHS policy.

If a future decision introduces expiration, configure a positive retention
period and explicitly schedule the existing source-specific cleanup command:

```text
python manage.py cleanup_pdf_readability_attempts --source authenticated --dry-run
python manage.py cleanup_pdf_readability_attempts --source authenticated
```

Default cleanup targets public and legacy/unknown rows using public retention,
preserving its existing operational contract. Explicit `--source unknown` targets
unknown only. Authenticated cleanup uses its separate window and cannot delete
public/unknown rows; public cleanup cannot delete authenticated rows.

## Activation and validation

Implementation and synthetic local checks do not enable a shared pilot. Before
enabling, record the pilot operator, target environment, approved participants
and documents, support contact, notice/retention decision and restricted evidence
location. Verify the deployed revision, applicable parser isolation, limits,
temporary-file cleanup and safe application/edge logging under #970/#971.
Public-pilot-only requirements under #968 are not automatically prerequisites,
but sign-in does not replace applicable safeguards.

Enable authenticated recording and verify successful and unsuccessful outcomes
appear in the dashboard. Keep authenticated retention unset and do not install
an authenticated cleanup schedule for this pilot. Confirm public recording and
retention remain unchanged.

Enable only the authenticated Constance setting for the agreed validation round.
Check approved-user upload, report, copy and print/save; signed-out and
unapproved-user denial; CSRF rejection; supported and negative fixtures; source
filtering and dashboard authorization. Record content-free findings and follow-up
issues, never real PDFs or report contents in public evidence. Disable the
authenticated flag to end the round and recheck authorized unavailability and
unauthorized denial. Keep the public flag off throughout.

### Production rollout checklist

These are preparation steps, not a record of deployed verification or enablement.
The intended pilot runs in production for approved authenticated participants.
A development rehearsal is useful but does not replace production verification.
Keep public uploads disabled.

1. After review and merge, verify production's deployed revision and migration 0150.
   Check that the participant group exists without automatically added users.
2. Check applicable deployed parser isolation, upload/concurrency bounds,
   temporary-file cleanup and safe request/edge logging using #970/#971.
   Record results against the actual production revision, not local screenshots.
3. Record the operating contact, approved accounts and supported test documents.
   Grant only pilot upload permission unless dashboard access is separately needed.
4. Set authenticated outcome recording on and leave authenticated retention
   unset. Verify recording before launching participant uploads. No authenticated
   record-cleanup job is required; do not change public recording or cleanup.
5. Confirm the public flag remains off. Enable only the authenticated flag and
   run the documented access, CSRF, report/copy/print and source-filter checks.
   Keep real document contents out of public evidence.
6. Share the direct URL only with approved participants. End or pause the round
   by disabling the authenticated flag; revoke access when no longer needed.


### Where production configuration is applied

Builder deployment infrastructure lives in
[HHS/simpler-grants-gov](https://github.com/HHS/simpler-grants-gov), separately
from this application PR. The following locations were inspected on October 6,
2026; source inspection does not confirm deployed AWS state.

1. In [`infra/nofos/app-config/prod.tf`](https://github.com/HHS/simpler-grants-gov/blob/main/infra/nofos/app-config/prod.tf),
   add `AUTHENTICATED_PDF_READABILITY_ATTEMPT_RECORDING_ENABLED = "true"` to
   `service_override_extra_environment_variables`. Leave
   `AUTHENTICATED_PDF_READABILITY_ATTEMPT_RETENTION_DAYS` unset. No authenticated
   scheduled cleanup job is needed for this pilot.
2. Review and apply the companion infrastructure change through the approved
   workflow, then deploy the Builder revision using **Deploy NOFOs** with the
   production target. Verify the running service has recording enabled.
3. In production Django administration, grant approved accounts **Can use PDF
   readability pilot** and dashboard reviewers **Can view metrics**. Enable
   `HHS_NOFO_AUTHENTICATED_PDF_METRICS_PILOT_ENABLED` in Constance after verifying
   applicable safeguards. Leave `HHS_NOFO_PDF_METRICS_PILOT_ENABLED` off.
4. Verify successful and handled unsuccessful authenticated test uploads appear
   under the Authenticated filter at `/nofos/metrics/readability-pilot` without
   document content. Operational monitoring must also cover requests rejected
   before the application workflow.

This Builder PR supplies the application, participant checkbox and rollout
instructions. Production environment configuration belongs in the companion
infrastructure repository; this PR does not apply Terraform or enable live
switches. Disabling the authenticated upload switch pauses the pilot immediately.
Disabling recording requires updating its environment setting and redeploying.
Existing authenticated usage records remain available without automatic expiration.
