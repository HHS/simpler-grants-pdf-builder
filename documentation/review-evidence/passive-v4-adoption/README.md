# Local passive-method adoption candidate

Initially prepared October 14, 2026; refreshed October 16 against Builder main
`35e58d81`, for metrics issue agilesix/hhs-nofo-metrics#10 and merged PR #11
(library main commit `b38496f5`).

Local branch: `codex/readability-passive-v4-adoption`.

The staged changes select HTML profile @0.5.0 for both Builder-native HTML and
standalone authenticated DOCX, tagged PDF @0.6.0, generic PDF @0.5.0, and tagged
adapter @0.1.7. Existing version identity checks retain
historical scores and prevent reuse as current scores when the package/profile
changes. No snapshot migration or policy-target change is needed.

Verification used a separate local Python environment with the built 0.6.0 wheel
and the existing Builder dependency libraries. The environment imports the
candidate's installed wheel, including PDF subprocesses, rather than an editable
metrics checkout. The refreshed branch passed 168 tests across source-native
readability, PDF and DOCX analysis, checkpoints and authenticated/public upload
views. A new synthetic DOCX regression verifies that the corrected classifier
changes the passive numerator from two to three without changing sentence totals
or any other metric, and that the actual DOCX worker returns the corrected value.
Existing structured-DOCX tests verify reuse of the corrected HTML profile.
No shared environment was changed.

This is **not ready for deployment**. Builder's declared dependency and lockfile
remain at the existing release. Before opening the adoption PR, publish the
reviewed library wheel, then update the dependency pin and regenerate the
lockfile against that actual artifact. Update the readability integration and
pilot documentation in the same Builder PR. Record the resulting package/profile
identity during dev verification. No pilot flag, access rule, upload validation,
temporary-storage policy or metrics target is changed by profile adoption.

The v0.4 method fixes unambiguous be contractions and the `need`/`indeed` errors.
Ambiguous pronoun `'s` remains a documented limitation because it can mean `is`
or `has`. This is not a claim of Word parity or of calibration of the 8% target.
