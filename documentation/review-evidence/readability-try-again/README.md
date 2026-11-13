# Readability panel: remove Recalculate, show Try again only on failure

Local Chromium verification, November 13, 2026, at a 1100px viewport. All
screenshots show the real Django NOFO edit page with readability metrics
enabled, rendering a synthetic test NOFO with an automatic import snapshot, as
every imported NOFO has in production. That snapshot is why the slim
information alert ("A snapshot was saved automatically when this NOFO was
imported...") appears at the top of the panel. The failure screenshots force
the metrics endpoint to return a 503 response in the browser; no production
data or services were used.

The screenshots also show the "current NOFO" wording that replaces "version"
in the alert and the panel introduction ("Each action saves once for the
current NOFO."); see the [decision log](../../DECISIONS.md#2026-11-13--say-current-nofo-rather-than-version-in-readability-copy).

- [Before, success](before-success.png): after the panel calculates on open,
  an outlined **Recalculate** button sits beside the status line.
- [After, success](after-success.png): the same state with no button. The
  status line and **Save these results** are unchanged.
- [Before, failure](before-failure.png): a failed first calculation leaves a
  **Calculate metrics** button beside the error.
- [After, failure](after-failure.png): the same failure shows **Try again**.
  Selecting it calculated again and hid the button once the calculation
  succeeded.

Browser checks on the same page:

| State | Status line | Button shown |
| --- | --- | --- |
| Panel opened, calculation succeeds | Calculated for the current NOFO. Save these results to keep a snapshot. | None |
| Panel opened, calculation fails | Metrics could not be calculated. Readability metrics are unavailable. | Try again |
| Try again selected, calculation succeeds | Calculated for the current NOFO. Save these results to keep a snapshot. | None |

The decision is recorded in the [decision log](../../DECISIONS.md#2026-11-13--remove-the-readability-panels-recalculate-button).
