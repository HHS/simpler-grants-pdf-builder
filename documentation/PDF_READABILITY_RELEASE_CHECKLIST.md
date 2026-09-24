# PDF readability deployment verification checklist

Use this worksheet for [#971](https://github.com/HHS/simpler-grants-pdf-builder/issues/971) only after the supported-document rules in #969 and applicable [deployment safeguards](PDF_READABILITY_SAFEGUARDS.md) in #970 are ready. The [pilot runbook](PDF_READABILITY_PILOT.md) remains the policy and stop procedure. A merged commit or passing local test is **not** permission to enable the public route. Use only approved synthetic or representative documents under the agreed handling controls; do not attach real or pre-decisional PDFs, filenames, extracted text, or sensitive logs to public issues.

For each target environment, record the **date/time, environment, release owner, deployed Builder commit, deployed `hhs-nofo-metrics` version and tagged-adapter version**, and links to restricted evidence. Read the **stored Constance value** of `HHS_NOFO_PDF_METRICS_PILOT_ENABLED` from that environment's database, not just its environment default. Record the value before and after testing. Coordinate any temporary shared-dev enablement with its owner and restore the agreed state; do not change production for smoke testing.

In the target application's `nofos` directory, these read-only checks help capture dependency and flag evidence (an absent database row is different from a stored `False`):

```sh
python -c 'from importlib.metadata import version; from hhs_nofo_metrics.adapters.tagged_pdf import ADAPTER_VERSION; print(version("hhs-nofo-metrics"), ADAPTER_VERSION)'
python manage.py shell -c 'from constance.models import Constance; key="HHS_NOFO_PDF_METRICS_PILOT_ENABLED"; print(list(Constance.objects.filter(key=key).values_list("key", "value")))'
```

| Check in the target runtime | Passing evidence to record |
| --- | --- |
| Disabled route | With the stored flag off, signed-out GET and POST `/readability/` return the purpose-built 503 with no upload form. Both responses retain `Cache-Control: no-store` and `X-Robots-Tag: noindex, nofollow, noarchive, nosnippet`. Confirm the URL is absent from navigation and sitemaps. |
| Recognition and supported report | Verify #969's approved recognition rules are configured in the target environment; with rules absent, an upload must fail closed rather than yield a report. With an approved supported fixture, signed-out upload produces one immediate report. Record page and scope counts; all five displayed measures (word count, words per sentence, sentences per paragraph, Flesch-Kincaid Grade Level, passive sentences); measurement version; extraction-reliability caveat; and complete Calculation notes. Flesch Reading Ease should not display. Test Copy metrics and its feedback. |
| Rejection and bounds | Exercise an unrelated/unsupported PDF under #969's recognition rule, invalid bytes, >15 MiB upload, >150 pages, and the agreed timeout/failure fixture. Record safe response/status and absence of content-bearing logs. Check that handled failure/timeout removes request and nested parser temporary files in the target runtime. |
| Admission and limits | Hold one analysis on one PostgreSQL connection/worker while a second independent connection/worker attempts the route: the second gets busy/429, then a later attempt succeeds after release. Verify the Linux analyzer child applies the configured CPU, address-space, file-size, and open-file limits in the deployed container. SQLite/macOS evidence does not satisfy this row. |
| Browser-saved report | Save the report through the browser's **Print / save as PDF** action and inspect every page for complete values/notes, HHS/NOFO Builder identity, estimate disclaimer, readable page breaks, and no printed government banner/footer. Keep the saved synthetic output in the approved evidence location. |
| Operations | Link #970's verified ingress, analyzer-isolation, logging, retention, and tested infrastructure route-block evidence. Name support, monitoring, incident, and disable owners; confirm who can change the stored flag and how to invoke the route block if the application cannot respond. Record unresolved limitations and the named release owner's go/no-go decision, target environment/version, data classification, audience, and required approvals in the parent #968 gate. |

## Reuse before deployment

The existing generic synthetic fixture generator is `synthetic_text_pdf()` in `nofos/nofos/tests_nofos/test_pdf_readability.py`; it is not evidence of a recognized FY27 template. Use #969's approved positive/negative fixtures for recognition and report smoke checks. Existing Python tests cover safe errors, size/page bounds, local contention, worker environment, handled cleanup, route headers/content, and the adapter pin. The JavaScript tests cover print disclosure and copy behavior. From the repository root, the local regression commands are:

```sh
cd nofos
DATABASE_URL=sqlite:///:memory: python manage.py test bloom_nofos.tests_bloom_nofos.test_pdf_readability nofos.tests_nofos.test_pdf_readability nofos.tests_nofos.test_readability_metrics nofos.tests_nofos.test_readability_input_contract_migration
cd ..
node --test tests/js/pdf_readability.test.cjs
```

These tests do **not** establish deployed version/flag state, #969 recognition, real ingress controls, PostgreSQL cross-worker locking, Linux limits, deployment logging/retention, infrastructure blocking, or the appearance of a browser-saved PDF. Record each of those separately; mark unavailable checks as open rather than inferred pass.
