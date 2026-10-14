# Local passive-method adoption candidate

Prepared October 14, 2026 against Builder main `1e92725b`, for metrics issue
agilesix/hhs-nofo-metrics#10 and PR #11 (library commit `955cb8c`).

Local branch: `codex/readability-passive-v4-adoption`.

The staged changes select HTML profile @0.5.0, tagged PDF @0.6.0, generic PDF
@0.5.0, and tagged adapter @0.1.7. Existing version identity checks retain
historical scores and prevent reuse as current scores when the package/profile
changes. No snapshot migration or policy-target change is needed.

Verification used a separate local Python environment with the built 0.6.0 wheel
and the existing Builder dependency libraries. The environment imports the
candidate's installed wheel, including PDF subprocesses, rather than an editable
metrics checkout. All 62 tests in `nofos.tests_nofos.test_readability_metrics` and
`nofos.tests_nofos.test_pdf_readability` passed. No shared environment was changed.

This is **not ready for deployment**. Builder's declared dependency and lockfile
remain at the existing release. Before opening the adoption PR, complete the
library release gates and publish its reviewed wheel, then update the dependency
pin and regenerate the lockfile against that actual artifact. Update the
readability integration and pilot documentation in the same Builder PR. Record
the resulting package/profile identity during dev verification.

The v0.4 method fixes unambiguous be contractions and the `need`/`indeed` errors.
Ambiguous pronoun `'s` remains a documented limitation because it can mean `is`
or `has`. This is not a claim of Word parity or of calibration of the 8% target.
