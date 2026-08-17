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

When the feature flag is enabled, the normal NOFO edit screen shows a compact,
collapsed readability accordion after the primary NOFO status. A **Beta** tag
identifies the feature as experimental. Expanding the accordion reveals the
on-demand **Calculate metrics** action. The result displays the six configured
metric values, any metric-specific unavailable status, a scope explanation for
metrics that use different denominators, and collapsed package notes. The
browser reads only the endpoint response; metric calculation and source
rendering remain server-side. The package profile and version remain available
in the API response for diagnostics but are not shown to editors.

The panel does not assign pass/fail bands. It makes clear that calculations run
on demand and are not persisted.

## Target comparisons

Builder adds presentation-only comparisons without changing the metrics package
or its result contract. The default targets are:

- word count: 13,500 or fewer;
- words per sentence: 15 or fewer;
- sentences per paragraph: 3 or fewer;
- passive sentences: 8% or fewer; and
- Flesch-Kincaid grade level: 11.5 or lower for general NOFOs and 12.5 or
  lower for scientific/research NOFOs.

Flesch Reading Ease and characters per word remain informational; Builder does
not assign targets to them. Builder displays both grade-level comparisons and
does not infer a NOFO category.

Set `HHS_NOFO_METRIC_GOALS` to a JSON object keyed by metric ID to override the
defaults for an environment. Set it to `{}` to hide all target and assessment
language.

This synthetic example demonstrates the override shape:

```bash
HHS_NOFO_METRIC_GOALS='{"word_count":{"label":"Example goal","operator":"at_most","value":100}}'
```

Each configured goal requires a display `label`, an `operator` of `at_most` or
`at_least`, and a finite numeric `value`. A metric may instead use a non-empty
array of goal objects when multiple categories apply. Builder displays every
configured comparison without inferring which category applies. It compares
the unrounded metric value and uses neutral **Within target** or **Review
target** language rather than pass or fail.

When the package publishes `paragraph_count` and `sentences_per_paragraph` as
components of its sentence-scope results, Builder displays the latter as a
separate card. Older package versions leave that optional card hidden. The
denominator remains the package's source-native, sentence-bearing semantic
blocks.

When more than one category may apply, configure and display each labeled goal;
the application must not infer a category from the NOFO title or prose.

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
