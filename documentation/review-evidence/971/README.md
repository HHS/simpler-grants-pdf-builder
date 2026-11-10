# Readability Checker deployment verification evidence

Captured in Chrome on November 9, 2026 for [deployment verification issue #971](https://github.com/HHS/simpler-grants-pdf-builder/issues/971). See the [readiness guide](../../readability/READABILITY_CALCULATOR_READINESS.md#what-users-see-and-where-to-look) for current behavior and monitoring.

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
