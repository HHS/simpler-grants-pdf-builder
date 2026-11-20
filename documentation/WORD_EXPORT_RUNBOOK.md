# Word export runbook

## Account ownership and settings

Agile Six owns the new GrabzIt account. The account lookup reported the Micro plan with 200 captures remaining at the time of the check. Confirm organizational billing and that at least two current maintainers can access the account. Contact the Agile Six account administrators through the approved internal channel for access or recovery. Keep credentials, cookie values, and private recovery details out of the repository and operational evidence.

The account administrators still need to confirm the configured **Cache Length** for pre-decisional content and whether **Authorized Domains** or **Authorized IPs** is in use. Record the selected settings here once confirmed.

## Environment isolation

The rollout in [#1330](https://github.com/HHS/simpler-grants-pdf-builder/issues/1330) calls for Word export on `nofos.simpler.grants.gov`. Verify the effective host restriction and the task configuration in each deployed environment. Follow the exact-host allowlist in [Deployment](../DEPLOYMENT.md#word-export-environment-isolation). Keep credentials out of environments with Word export disabled. If development export is enabled later, use a separate development account and the exact host `nofos.dev.simpler.grants.gov`.

## Rotate and verify production credentials

1. Coordinate with the Agile Six GrabzIt account administrators to obtain the application key and secret through the approved internal channel. Have the AWS operator update the production secret entries mapped to `GRABZIT_APPLICATION_KEY` and `GRABZIT_APPLICATION_SECRET` in the ECS task definition.
2. Redeploy production with the [deployment workflow](../DEPLOYMENT.md#production). Confirm the rollout completed and that every running web task started after both credential entries were updated. Check that the task definition references the intended entries.
3. Using synthetic content in production, generate a normal NOFO Word export, a Composer or Content Guide export, and a clearance export if enabled. Open each `.docx` and verify that it contains the expected content. Check the corresponding application logs for conversion failures or invalid or empty output.
4. Verify account attribution. A decrease in the new account's remaining capture allowance around a controlled export is supporting evidence if other conversions are idle. If the counter is inconclusive, have an authorized AWS operator verify that the running service loaded the new key and secret and report only whether they match.

## Retire the previous account

After verifying production uses the new account, coordinate with the previous account holder to delete stored custom cookies, revoke or regenerate the old application secret, and cancel the old subscription. Verify that no deployed environment references the old credentials and that disabled environments hold no GrabzIt credentials. Record completion in [#1330](https://github.com/HHS/simpler-grants-pdf-builder/issues/1330).

## Cutover status

Production was redeployed after the credential update. A Word download succeeded, and the new account returned 200 remaining captures before and after the test. Confirmation that production loaded the new credentials, the full export smoke test, non-production cleanup, and retirement of the previous account are pending. Follow the remaining verification in [#1330](https://github.com/HHS/simpler-grants-pdf-builder/issues/1330). Broader Word export operations are tracked in [#880](https://github.com/HHS/simpler-grants-pdf-builder/issues/880).
