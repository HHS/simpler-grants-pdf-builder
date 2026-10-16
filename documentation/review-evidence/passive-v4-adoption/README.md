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

The dependency step advances Builder from 0.5.4, not 0.5.5. It therefore also
includes the released tagged table-cell continuation correction and adapter
0.1.7. PDF extraction and resulting nonpassive estimates may change. Claims that
only the passive score changes apply to a controlled identical extracted input,
not to every PDF analyzed across the package upgrade.

The library release is published at
https://github.com/agilesix/hhs-nofo-metrics/releases/tag/v0.6.0 from reviewed
main commit `b38496f5b90e88b0491d658a3151b04b299add53`, with all main CI checks
passing. Builder's dependency and lockfile now select its published wheel with
SHA-256 `7fc342f8bc0b7f78cf876ef41de847cf09404cdfe1045db10bd908df338ca81c`.
Poetry 2.5.1 regenerated only the metric package entry and project content hash;
no unrelated dependency versions changed. The actual published wheel is
installed in the isolated Python 3.14 consumer test and local browser runtime.
No pilot flag, access rule, upload validation, temporary-storage policy or metrics
target is changed by profile adoption. No Builder deployment is implied.

The v0.4 method fixes unambiguous be contractions and the `need`/`indeed` errors.
Ambiguous pronoun `'s` remains a documented limitation because it can mean `is`
or `has`. This is not a claim of Word parity or of calibration of the 8% target.
