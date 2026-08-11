# Source-native readability metrics

NOFO Builder has a contained integration boundary for the standalone
`hhs-nofo-metrics` package. The package is pinned to the durable `v0.5.0`
release. The feature remains disabled by default so environments can opt into
the provisional metrics UI independently.

## Source contract

Builder renders `nofos/includes/nofo_export_document.html` for both:

- the `#download_target` region used to generate Word documents; and
- the UTF-8 HTML passed to `hhs-nofo-metrics`.

This keeps the metrics source aligned with the generated document without an
authenticated HTTP request back into Builder. It also excludes navigation,
forms, CSRF tokens, and other application shell content from the source hash.

The caller selects:

- profile `hhs-nofo-fy27-html@0.4.0`;
- adapter root `download_target`;
- production path `nofo_builder_export_html`;
- the NOFO UUID as `document_id`; and
- `Nofo.updated` as the Builder revision.

## Endpoint

An authorized user with access to the NOFO can request:

```text
GET /nofos/<uuid>/readability-metrics
```

When enabled and installed, the endpoint returns the package's complete
status-aware `AnalysisResult` JSON and sets `Cache-Control: no-store`. It does
not flatten unavailable metrics to zero or turn provisional measurements into
pass/fail determinations.

Expected failures are machine-readable:

- `503 readability_metrics_disabled` when the feature flag is off;
- `503 readability_metrics_unavailable` when the package is absent; and
- `422` with the package's stable error code when analysis rejects the source.

Normal Builder group permissions apply.

## Edit-screen panel

When the feature flag is enabled, the normal NOFO edit screen shows an
on-demand **Calculate metrics** panel. It displays the six configured metric
values, each metric's package status, the active profile and profile status,
and any package warnings. The browser reads only the endpoint response; metric
calculation and source rendering remain server-side.

The panel does not assign pass/fail bands. It labels the result as a draft
structured estimate and makes clear that the calculation is not persisted.

## Local validation

Enable the feature in a local environment and start Builder normally:

```bash
HHS_NOFO_METRICS_ENABLED=true poetry run python nofos/manage.py runserver
```

## Release activation

Before enabling the feature outside local development:

1. Run the real-package integration test and the Builder test suite.
2. Confirm that the pinned package tag and profile reference are still the
   intended versions.
3. Set `HHS_NOFO_METRICS_ENABLED=true` only in the intended environment.

The edit-screen panel calculates on demand and does not add a database table,
background job, or cache. It displays the current response only; reloading or
editing the NOFO requires another calculation.
