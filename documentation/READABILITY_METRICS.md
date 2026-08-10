# Source-native readability metrics

NOFO Builder has a contained integration boundary for the standalone
`hhs-nofo-metrics` package. The feature is disabled by default until the
package has a durable tagged release and is pinned in `pyproject.toml` and
`poetry.lock`.

## Source contract

Builder renders `nofos/includes/nofo_export_document.html` for both:

- the `#download_target` region used to generate Word documents; and
- the UTF-8 HTML passed to `hhs-nofo-metrics`.

This keeps the metrics source aligned with the generated document without an
authenticated HTTP request back into Builder. It also excludes navigation,
forms, CSRF tokens, and other application shell content from the source hash.

The caller selects:

- profile `hhs-nofo-fy27-html@0.1.0`;
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

## Local validation

Until a package release is available, a developer can validate the integration
without changing Builder's dependency files:

```bash
poetry run pip install -e /path/to/hhs-nofo-metrics
HHS_NOFO_METRICS_ENABLED=true poetry run python nofos/manage.py runserver
```

This editable install is for local development only. Do not commit a local
filesystem dependency.

## Release activation

After `hhs-nofo-metrics` has a durable release:

1. Pin the exact package version or immutable Git tag in `pyproject.toml`.
2. Regenerate and commit `poetry.lock`.
3. Run the real-package integration test and the Builder test suite.
4. Set `HHS_NOFO_METRICS_ENABLED=true` only in the intended environment.

This first slice deliberately does not add a UI, database table, background
job, or cache. Those product choices can consume the same endpoint and result
contract without changing how Builder renders or measures the source.
