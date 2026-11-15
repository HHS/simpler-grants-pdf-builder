# Readability Checker deployment verification evidence

This record supports [deployment verification #971](https://github.com/HHS/simpler-grants-pdf-builder/issues/971) and the [public launch decision #968](https://github.com/HHS/simpler-grants-pdf-builder/issues/968). See the [readiness guide](../../readability/READABILITY_CALCULATOR_READINESS.md#what-users-see-and-where-to-look) for current behavior and monitoring. The screenshots below were captured in Chrome on November 9, 2026.

## Dated launch evidence

| Check | Result | Scope |
| --- | --- | --- |
| September 29 signed-out PDF smoke and browser save | A synthetic PDF generated a report, and an unrelated PDF was rejected. The browser displayed copy confirmation and saved a complete report as a PDF. [Upload and rejection](https://github.com/HHS/simpler-grants-pdf-builder/issues/971#issuecomment-5889879072) · [Browser follow-up](https://github.com/HHS/simpler-grants-pdf-builder/issues/971#issuecomment-5890322354) | Historical dev evidence with metrics 0.5.4. Clipboard contents were unverified. |
| October 30 dev WAF rate enforcement | With the rate rule in Block mode at 10 requests per source IP per 300 seconds, empty POSTs to all four checker route forms (`/readability-checker`, `/readability-checker/`, `/readability`, `/readability/`) returned HTTP 429. Alarm and recovery emails arrived. Restoration returned both WAF rules to Count with no 429s. [Rate stage](https://github.com/HHS/simpler-grants-gov/issues/13085#issuecomment-6530139849) · [Restoration](https://github.com/HHS/simpler-grants-gov/issues/13085#issuecomment-6531844716) | Dev only, with public uploads disabled. 429 counts weren't itemized per route. |
| November 2 dev WAF emergency block | With the emergency rule active, GET and empty POST to all four route forms returned HTTP 403 while `/health` and the home page returned 200. Alarm and recovery emails arrived. A final deployed restoration confirmed both rules in Count and baseline responses on every route form. [Emergency stage](https://github.com/HHS/simpler-grants-gov/issues/13085#issuecomment-6581516804) · [Final restoration](https://github.com/HHS/simpler-grants-gov/issues/13085#issuecomment-6585955723) | Dev only, with public uploads disabled. Doesn't cover processing, cleanup, logging or production. |
| November 3 paced upload | One normal and one paced synthetic PDF upload returned HTTP 200 through the signed-in dev route. All five post-test health and page checks returned HTTP 200. [Test results](https://github.com/HHS/simpler-grants-gov/issues/12568#issuecomment-6609694463) | One paced request. The test left the buffering layer, total upload deadline, and concurrent slow requests unverified. |
| November 4 production email delivery | The intended inbox received both alarm and recovery messages from a controlled test alarm. [Delivery receipt](https://github.com/HHS/simpler-grants-gov/issues/12568#issuecomment-6643739707) | Verifies delivery through the production monitoring topic for the test alarm. |
| November 9 search indexing | The disabled production page sent the same crawler directives in its HTTP header and HTML. The site-wide robots file also disallowed crawling. [Production observation](https://github.com/HHS/simpler-grants-pdf-builder/issues/971) | The observation covered the disabled page. The directives depend on crawler compliance. |
| November 10 isolated interruption | In a disposable dev task, the parser exited after the test stopped its own request process and the startup hook removed the abandoned workspace. [Workflow run](https://github.com/HHS/simpler-grants-gov/actions/runs/42856640416) | Covers the isolated scenario. Full service task replacement and production storage remain unverified. |
| November 12 production firewall logging configuration | The read-only check observed the expected CloudWatch destination, 1,827-day retention, zero subscription filters, and no configured log redaction or WAF logging filter. [Inspection](https://github.com/HHS/simpler-grants-gov/actions/runs/43233515647) · [Findings](https://github.com/HHS/simpler-grants-gov/issues/12568#issuecomment-6825800300) | The check covered configured settings. Individual log records, request samples, log access, and downstream retention remain unverified. |

## Builder analyzer busy

Builder rendered its actual public upload template locally with a synthetic PDF and a simulated busy analyzer response.

![Readability Checker form with the inline analyzer-busy message](builder-busy.jpg)

## WAF upload rate limit

A local server returned HTTP 429 with an empty response body, matching the current WAF rate block configuration. This screenshot shows Chrome's generic error page. Other browsers may display a different error page or a blank response.

![Chrome shows HTTP ERROR 429 instead of the Readability Checker form](waf-429.jpg)

The screenshots show a local reproduction. They do not establish live browser behavior or deployment settings.

## November 10 dev temporary storage and cleanup

- **Environment and method.** On November 10, 2026, the
  [runtime verification workflow](https://github.com/HHS/simpler-grants-gov/actions/runs/42829391563)
  ran from 8:58 to 9:00 a.m. Eastern, dispatched by `benbrasso`. It used
  synthetic PDFs in a disposable infra-dev task with the service's deployed
  task definition. The workflow ran from SGG
  `30fe0cd70dc1bb21bfc7c00c759e0b58b76ec415`, which includes
  [SGG #13221](https://github.com/HHS/simpler-grants-gov/pull/13221).
  The latest [successful dev rollout before the probe](https://github.com/HHS/simpler-grants-gov/actions/runs/42716263766)
  deployed Builder `8e660d2580072376b242b1ef1d7bc0fabf8fc68a`, which includes
  the [request workspace and interruption cleanup fix](https://github.com/HHS/simpler-grants-pdf-builder/pull/1316).
  The probe reported `hhs-nofo-metrics` 0.7.0 and `pypdf` 6.21.4.
- **Storage.** The disk-backed upload and analyzer working directory both
  reported `memory_backed` from the filesystem check inside the request workspace.
- **Cleanup and runtime.** The synthetic supported PDF, invalid and encrypted
  rejections, and controlled timeout all passed their cleanup checks. The
  probe observed the files and analyzer directory gone before fallback cleanup
  and verified workspace removal. Linux analyzer limits, the minimal child
  environment, and PostgreSQL admission and release checks passed. The task
  exited successfully, and the public upload switch was off before and after.

This run establishes storage and cleanup in the disposable dev task for the
cases tested. Live-service worker interruption, service task replacement,
production storage, and deployed log handling and retention remain separate
checks. See the [readiness plan](../../readability/READABILITY_CALCULATOR_READINESS.md#3-runtime-checks-without-opening-public-uploads)
for the remaining verification and review.

## November 10 signed-out dev logging check

At 3:20 p.m. Eastern, one approved synthetic PDF was submitted through the
signed-out Readability Checker on infra-dev after the
[dev deployment](https://github.com/HHS/simpler-grants-gov/actions/runs/42852799008)
of Builder `c5aee10ec63b4cde554046f03331517787a7977d`. The request returned
HTTP 200 with a report. The public switch was off before the test, enabled
briefly for the upload, then restored to off. The dev and production public
pages both displayed the unavailable page afterward.

An aggregate New Relic query for 3:19–3:23 p.m. Eastern found one application
POST by time and route and one load balancer POST with the distinct synthetic
request marker. Searches of the message, request, URL, and applicable exception
fields returned zero matches for the test filename and the phrase embedded in
the PDF in both sources. This verifies the fields searched for one successful
dev upload. Failure paths and production uploads remain outside this result.

### Logging coverage reviewed November 10

- New Relic showed Builder application and load balancer access logs for both
  infra-dev and production. A 24-hour query returned no WAF log category under
  the two Builder entity names and no matching span or transaction-error
  events under those entity, service, or application names. Coverage under
  other identifiers or in other systems remains unverified.
- The [production inspection](https://github.com/HHS/simpler-grants-gov/actions/runs/42861864575)
  reported 1,827 days of retention for the application CloudWatch log group and
  one forwarding subscription. The [WAF configuration source](https://github.com/HHS/simpler-grants-gov/blob/main/infra/modules/service/waf.tf)
  declares a separate CloudWatch log destination. The production inspector
  reads the web ACL and application log settings. Verifying the deployed WAF
  logging destination, retained fields, and access requires a separate
  restricted check.
- The New Relic account's retention view required additional access. Have
  authorized observability and infrastructure owners verify effective
  retention and reader access, plus any trace, error-reporting or crash-data
  destinations, under [safeguards #970](https://github.com/HHS/simpler-grants-pdf-builder/issues/970).
