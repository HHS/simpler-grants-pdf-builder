# Readability Checker 429 screenshots

Captured in Chrome on November 9, 2026 for [deployment verification issue #971](https://github.com/HHS/simpler-grants-pdf-builder/issues/971). See the [readiness guide](../../readability/READABILITY_CALCULATOR_READINESS.md#what-users-see-and-where-to-look) for current behavior and monitoring.

## Builder analyzer busy

Builder rendered its actual public upload template locally with a synthetic PDF and a simulated busy analyzer response.

![Readability Checker form with the inline analyzer-busy message](builder-busy.jpg)

## WAF upload rate limit

A local server returned HTTP 429 with an empty response body, matching the current WAF rate block configuration. This screenshot shows Chrome's generic error page. Other browsers may display a different error page or a blank response.

![Chrome shows HTTP ERROR 429 instead of the Readability Checker form](waf-429.jpg)

The screenshots show a local reproduction. They do not establish live browser behavior or deployment settings.
