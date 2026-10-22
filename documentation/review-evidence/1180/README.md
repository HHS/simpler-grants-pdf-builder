# Strong1 import and redundant bold verification

Issue: https://github.com/HHS/simpler-grants-pdf-builder/issues/1180

## Source and future manual verification

The reported `Strong1` character style was observed in a Word export from the
**GrantSolutions Announcement Module**. The supplied export defines this exact
style name as bold only. How the module creates or applies the style is not
established, and other exports may use different styles.

For future verification, obtain a fresh GrantSolutions Announcement Module Word
export and confirm that it contains text using `Strong1`. Compare Word with
Builder after both import and reimport: style-only text should be bold, explicit
bold-off overrides should remain off, direct bold should not create duplicate
markers, and separately applied italics should remain. Use the synthetic tests
below for override combinations absent from the fresh export.

## Screenshots

- [Before](before.png): upstream `5b7b5137199c4d5bda3dcf93cb24053754983cfa` behavior.
- [After](after.png): the same five synthetic cases with this change.

These are browser screenshots of a local verification page displaying actual
converter output, not screenshots of production or a proposed UI change.
The first four rows use the shared DOCX import adapter and a synthetic DOCX
built by `strong1_docx()` in `test_strong1_import.py`. The before conversion
bypasses only the new `normalize_strong1_runs()` call. The redundant-bold row
passes `<p><strong><strong>Community-based project and activities</strong></strong></p>`
through the upstream and changed Markdown converters respectively. All results
render through Python Markdown with `extra`, as configured in Builder.

The nested-bold row reproduces the reported stored `****text****` and its visible
asterisks/unintended italics. It does not establish which production step added
the duplicate wrapper. The original uploaded Word document and production
announcement data are not committed. Table widths are outside this change.

## Expected results

| Case | Expected after import and Markdown rendering |
| --- | --- |
| Strong1 only | Bold; no italics or visible formatting markers |
| Explicit bold off | Plain text; honor `0`, `false`, and `off` |
| Strong1 plus direct bold | One bold wrapper and one pair of Markdown delimiters |
| Intentional italics | Retain italics alongside style bold; retain italics alone when bold is explicitly disabled |
| Redundant nested bold | One bold level; no unintended italics or visible delimiters |

## Automated coverage

### Definition safeguards

The compatibility rule now checks the actual style definition, not its name
alone. Only directly defined bold-only Strong1 styles qualify; Word UI metadata
is allowed. Inherited or linked definitions, disabled/missing bold and additional
formatting are not rewritten. Their original package and style references remain
unchanged, and Mammoth's existing unrecognized-style warning/strict-mode behavior
remains in effect. This does not add support for those unfamiliar definitions.

Regression tests cover these negative cases, enabled bold spellings, benign UI
metadata, the existing warning count and retention of directly applied italics.
The before/after screenshots above remain applicable to the supported definition.

`nofos.tests_nofos.test_strong1_import` covers these cases, mixed `<b>`/`<strong>`
nesting in body text and table headers, literal asterisk footnote markers,
style name versus style ID, native-note runs, idempotence, original upload
preservation, HTML upload passthrough, real import/reimport across HRSA, CDC,
NIH and ACF groups (including preservation of the archived prior content),
and Composer import.

Focused checks:

```sh
cd nofos
poetry run python manage.py test nofos.tests_nofos.test_strong1_import nofos.tests_nofos.test_import_transforms nofos.tests_nofos.test_mammoth nofos.tests_nofos.test_nofo_markdown nofos.tests_nofos.test_leading_word_title --noinput
```

All 120 focused tests passed. No rule expands formatting to adjacent characters
or repairs source formatting split inside a word. Existing saved Markdown is
not migrated; reimport applies the handling to incoming content.
